"""
Seed LCHAI v1.2 database from cohortMAF Excel file.
Loads patients with histologic patterns and their genetic mutations.
"""

import sys
import uuid
import math
from datetime import datetime, timezone

import pandas as pd
import psycopg2
import psycopg2.extras
import requests

# ── Configuration ──────────────────────────────────────────────────────
EXCEL_PATH = r"D:\Dropbox\PHD\THESIS\cohortMAF.2025-12-05_with_histologic_patterns_dec2025 rev 2.xlsx"
CASE_SERVICE_URL = "http://localhost:8001"
DB_DSN = "postgresql://oncology:oncology_secret@localhost:5432/oncology_xai"

# Key mutations of interest for lung cancer
KEY_MUTATIONS = {
    "TP53", "KRAS", "EGFR", "ALK", "STK11", "KEAP1", "NF1", "BRAF",
    "PIK3CA", "MET", "ROS1", "RET", "ERBB2", "NRAS", "MAP2K1",
    "SMARCA4", "RB1", "CDKN2A", "ARID1A", "NOTCH1",
}

PATTERN_THRESHOLD = 0.55  # from .env


def safe_float(val, default=0.0):
    """Convert value to float, returning default if NaN/None."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return float(val)


def safe_int(val, default=0):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return int(val)


def main():
    print("=" * 60)
    print("LCHAI v1.2 — Database Seed from cohortMAF Excel")
    print("=" * 60)

    # ── 1. Read Excel ──────────────────────────────────────────────
    print("\n[1/5] Reading Excel file...")
    cols_needed = [
        "Hugo_Symbol", "Variant_Classification", "Tumor_Sample_Barcode",
        "case_barcode", "Chromosome", "Start_Position",
        "n_tiles_total", "n_acinar", "pct_acinar",
        "n_lepidic", "pct_lepidic", "n_micropapillary", "pct_micropapillary",
        "n_mucinous", "pct_mucinous", "n_papillary", "pct_papillary",
        "n_solid", "pct_solid",
    ]
    df = pd.read_excel(EXCEL_PATH, usecols=cols_needed)
    print(f"  Loaded {len(df)} rows, {df['case_barcode'].nunique()} unique patients")

    # ── 2. Filter patients with histologic patterns ────────────────
    df_with_patterns = df[df["n_tiles_total"].notna()].copy()
    patients_with_patterns = df_with_patterns["case_barcode"].unique()
    print(f"  {len(patients_with_patterns)} patients have histologic pattern data")

    # Also include patients without patterns (but fewer details)
    all_patients = df["case_barcode"].unique()
    patients_without_patterns = set(all_patients) - set(patients_with_patterns)
    print(f"  {len(patients_without_patterns)} patients without patterns (will create basic records)")

    # ── 3. Create patients and cases via REST API ──────────────────
    print("\n[2/5] Creating patients and cases via case-service API...")
    patient_map = {}  # case_barcode -> {patient_id, case_id}

    for i, barcode in enumerate(all_patients):
        if (i + 1) % 50 == 0:
            print(f"  ... {i + 1}/{len(all_patients)}")

        # Get first tumor sample barcode for this patient
        patient_rows = df[df["case_barcode"] == barcode]
        tumor_barcode = patient_rows["Tumor_Sample_Barcode"].iloc[0]

        # Get mutations for this patient
        patient_mutations = patient_rows["Hugo_Symbol"].unique().tolist()
        key_muts = [g for g in patient_mutations if g in KEY_MUTATIONS]

        # Create patient
        resp = requests.post(f"{CASE_SERVICE_URL}/api/v1/patients", json={
            "external_id": barcode,
            "demographics": {
                "tcga_barcode": barcode,
                "tumor_sample_barcode": tumor_barcode,
                "source": "TCGA-LUAD",
                "total_mutations": len(patient_mutations),
                "key_mutations": key_muts,
            },
        })
        if resp.status_code == 201:
            patient_id = resp.json()["patient_id"]
        elif resp.status_code == 500 and "unique" in resp.text.lower():
            # Patient already exists, find it
            search = requests.get(f"{CASE_SERVICE_URL}/api/v1/patients", params={"query": barcode})
            existing = [p for p in search.json() if p["external_id"] == barcode]
            if existing:
                patient_id = existing[0]["patient_id"]
            else:
                print(f"  WARNING: Could not create or find patient {barcode}")
                continue
        else:
            print(f"  WARNING: Failed to create patient {barcode}: {resp.status_code} {resp.text[:200]}")
            continue

        # Create case
        resp = requests.post(f"{CASE_SERVICE_URL}/api/v1/cases", json={
            "patient_id": patient_id,
            "tags": ["TCGA-LUAD", "seed"],
            "metadata": {
                "source": "cohortMAF_dec2025",
                "tumor_sample_barcode": tumor_barcode,
            },
        })
        if resp.status_code == 201:
            case_id = resp.json()["case_id"]
        else:
            print(f"  WARNING: Failed to create case for {barcode}: {resp.status_code}")
            continue

        patient_map[barcode] = {
            "patient_id": patient_id,
            "case_id": case_id,
            "mutations": patient_mutations,
            "key_mutations": key_muts,
        }

    print(f"  Created {len(patient_map)} patients with cases")

    # ── 4. Seed inference data directly into PostgreSQL ─────────────
    print("\n[3/5] Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    print("\n[4/5] Seeding inference results for patients WITH histologic patterns...")
    seeded_count = 0

    for barcode in patients_with_patterns:
        if barcode not in patient_map:
            continue

        info = patient_map[barcode]
        case_id = info["case_id"]
        mutations = info["mutations"]
        key_muts = info["key_mutations"]

        # Get pattern data (same for all rows of this patient)
        pat_row = df_with_patterns[df_with_patterns["case_barcode"] == barcode].iloc[0]

        n_tiles = safe_int(pat_row["n_tiles_total"])
        pct_acinar = safe_float(pat_row["pct_acinar"])
        pct_lepidic = safe_float(pat_row["pct_lepidic"])
        pct_micropapillary = safe_float(pat_row["pct_micropapillary"])
        pct_mucinous = safe_float(pat_row["pct_mucinous"])
        pct_papillary = safe_float(pat_row["pct_papillary"])
        pct_solid = safe_float(pat_row["pct_solid"])

        # Determine predominant pattern
        patterns = {
            "acinar": pct_acinar,
            "lepidic": pct_lepidic,
            "micropapillary": pct_micropapillary,
            "mucinous": pct_mucinous,
            "papillary": pct_papillary,
            "solid": pct_solid,
        }
        predominant = max(patterns, key=patterns.get)

        # Create IDs
        image_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        bundle_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Insert dummy image record
        cur.execute("""
            INSERT INTO images (id, case_id, format, storage_uri, checksum, size_bytes,
                                stain, magnification, notes, uploaded_by, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            image_id, case_id, "svs",
            f"s3://oncology-xai/images/{barcode}/slide.svs",
            "seed_" + uuid.uuid4().hex[:56],
            0,
            "H&E", "20x",
            f"TCGA-LUAD slide for {barcode} (seeded from cohortMAF)",
            "seed_script", now,
        ))

        # Insert ML job (completed)
        cur.execute("""
            INSERT INTO ml_jobs (id, case_id, image_id, job_type, status, progress,
                                 result_bundle_id, started_at, ended_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            job_id, case_id, image_id, "IMAGE_INFERENCE", "COMPLETED", 1.0,
            bundle_id, now, now, now,
        ))

        # Insert result bundle
        pattern_composition = {k: round(v * 100, 2) for k, v in patterns.items()}
        cur.execute("""
            INSERT INTO result_bundles (id, case_id, image_id, job_id, model_profile,
                                        model_version, thresholds, pattern_composition,
                                        predominant_pattern, summary_json,
                                        evidence_source, intended_use, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            bundle_id, case_id, image_id, job_id,
            "CTransPath+FuzzyArcLoss_v3", "1.0.0-seed",
            psycopg2.extras.Json({"pattern": PATTERN_THRESHOLD, "mutation": 0.60}),
            psycopg2.extras.Json(pattern_composition),
            predominant,
            psycopg2.extras.Json({
                "source": "TCGA-LUAD cohortMAF",
                "tcga_barcode": barcode,
                "n_tiles_total": n_tiles,
                "total_mutations_detected": len(mutations),
                "key_mutations_detected": key_muts,
            }),
            "THESIS_INTERNAL",
            "research / decision support (non-diagnostic)",
            now,
        ))

        # Insert pattern results
        for pattern_name, pct_val in patterns.items():
            n_val = safe_int(pat_row.get(f"n_{pattern_name}", 0))
            cur.execute("""
                INSERT INTO pattern_results (id, result_bundle_id, pattern, score,
                                             percentage, is_conclusive, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()), bundle_id, pattern_name,
                pct_val, round(pct_val * 100, 4),
                pct_val >= PATTERN_THRESHOLD,
                now,
            ))

        # Insert genetic results (key mutations found in this patient)
        for gene in key_muts:
            cur.execute("""
                INSERT INTO genetic_results (id, result_bundle_id, mutation, score,
                                             status, evidence_source, intended_use, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()), bundle_id, gene,
                0.95,  # high confidence since these are confirmed TCGA mutations
                "POSITIVE",
                "TCGA_MAF",
                "research / decision support (non-diagnostic)",
                now,
            ))

        # Also add negative results for key mutations NOT found
        for gene in (KEY_MUTATIONS - set(key_muts)):
            cur.execute("""
                INSERT INTO genetic_results (id, result_bundle_id, mutation, score,
                                             status, evidence_source, intended_use, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()), bundle_id, gene,
                0.05,
                "NEGATIVE",
                "TCGA_MAF",
                "research / decision support (non-diagnostic)",
                now,
            ))

        # Insert morphologic profile
        cur.execute("""
            INSERT INTO morphologic_profiles (id, result_bundle_id, n_tiles_total,
                                              pct_lepidic, pct_acinar, pct_papillary,
                                              pct_micropapillary, pct_solid, pct_mucinous, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()), bundle_id, n_tiles,
            pct_lepidic, pct_acinar, pct_papillary,
            pct_micropapillary, pct_solid, pct_mucinous, now,
        ))

        seeded_count += 1
        if seeded_count % 10 == 0:
            conn.commit()
            print(f"  ... seeded {seeded_count}/{len(patients_with_patterns)} patients with full results")

    conn.commit()
    print(f"  Seeded {seeded_count} patients with full inference results")

    # ── 5. Summary ────────────────────────────────────────────────
    print("\n[5/5] Verifying seed data...")
    cur.execute("SELECT COUNT(*) FROM patients")
    print(f"  Patients: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM cases")
    print(f"  Cases: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM images")
    print(f"  Images: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM ml_jobs")
    print(f"  ML Jobs: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM result_bundles")
    print(f"  Result Bundles: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM pattern_results")
    print(f"  Pattern Results: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM genetic_results")
    print(f"  Genetic Results: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM morphologic_profiles")
    print(f"  Morphologic Profiles: {cur.fetchone()[0]}")

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("Seed complete! Open http://localhost:3000 to see the data.")
    print("=" * 60)


if __name__ == "__main__":
    main()
