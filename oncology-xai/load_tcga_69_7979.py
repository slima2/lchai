"""
Comprehensive data loader for TCGA-69-7979.
- Uploads tiled image and overlay to MinIO
- Generates SHAP bar, beeswarm, force plots
- Creates all DB records (image, ml_job, result_bundle, patterns, genetics, XAI artifacts, morphologic profile)
- Creates EHR document from mutation data
"""

import hashlib
import io
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
import shap
import xgboost as xgb
from minio import Minio
from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────────────

DB_CONFIG = dict(
    host='localhost', port=5432,
    dbname='oncology_xai', user='oncology', password='oncology_secret'
)
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS = 'minioadmin'
MINIO_SECRET = 'minioadmin'
MINIO_BUCKET = 'oncology-xai'

CASE_PREFIX = 'TCGA-69-7979'
DATA_DIR = r'D:\Dropbox\PHD\THESIS\TCGA-69-7979'
COHORT_FILE = r'D:\Dropbox\PHD\THESIS\cohortMAF.2025-12-05_with_histologic_patterns_dec2025 rev 2.xlsx'

TILED_IMG = os.path.join(DATA_DIR, 'SLIMA TCGA-69-7979 tiled image ver 8 feb 2026.jpeg')
CSV_FILE = os.path.join(DATA_DIR, 'TCGA-69-7979-01Z-00-DX1.c9bc265d-4889-4333-9852-b8b535887f1e_tiles_384_predictions.csv')
EHR_XLSX = os.path.join(DATA_DIR, 'SLIMA TCGA-69-7979 histo to mutations mapping cohort ver 8 feb 2027.xlsx')

ID2LABEL = {0: "micropapillary", 1: "cribriform", 2: "papillary", 3: "lepidic", 4: "solid", 5: "acinar"}
PATTERN_COLORS = {
    "acinar":         (0.0, 1.0, 0.0),    # green
    "lepidic":        (1.0, 1.0, 0.0),    # yellow
    "micropapillary": (1.0, 0.0, 1.0),    # magenta
    "mucinous":       (1.0, 0.65, 0.0),   # orange
    "papillary":      (0.0, 0.0, 1.0),    # blue
    "solid":          (1.0, 0.0, 0.0),     # red
}
PATTERN_HEX = {
    "acinar": "#00FF00", "lepidic": "#FFFF00", "micropapillary": "#FF00FF",
    "mucinous": "#FFA500", "papillary": "#0000FF", "solid": "#FF0000",
}
KEY_GENES = ['EGFR', 'KRAS', 'TP53']
FEATURES = ['pct_acinar', 'pct_lepidic', 'pct_micropapillary', 'pct_mucinous', 'pct_papillary', 'pct_solid']


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def get_minio():
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS, secret_key=MINIO_SECRET, secure=False)
    if not client.bucket_exists(MINIO_BUCKET):
        client.make_bucket(MINIO_BUCKET)
    return client


def upload_to_minio(client, key, data, content_type='application/octet-stream'):
    """Upload bytes to MinIO, return s3:// URI."""
    client.put_object(MINIO_BUCKET, key, io.BytesIO(data), len(data), content_type=content_type)
    return f"s3://{MINIO_BUCKET}/{key}"


# ─── Step 1: Find patient & case in DB ─────────────────────────────────────

def find_patient_case(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM patients WHERE external_id = %s", (CASE_PREFIX,))
    row = cur.fetchone()
    if not row:
        sys.exit(f"Patient {CASE_PREFIX} not found in database. Run seed_from_excel.py first.")
    patient_id = row[0]

    cur.execute("SELECT id FROM cases WHERE patient_id = %s", (patient_id,))
    row = cur.fetchone()
    if not row:
        sys.exit(f"Case for patient {CASE_PREFIX} not found.")
    case_id = row[0]
    print(f"  Patient: {patient_id}  Case: {case_id}")
    return patient_id, case_id


# ─── Step 2: Upload tiled image to MinIO + register in DB ──────────────────

def upload_image(conn, minio_client, case_id):
    """Upload the tiled JPEG to MinIO and create an image record."""
    cur = conn.cursor()
    # Check if image already exists
    cur.execute("SELECT id FROM images WHERE case_id = %s", (case_id,))
    existing = cur.fetchone()
    if existing:
        print(f"  Image already exists: {existing[0]}")
        return existing[0]

    print("  Reading tiled image...")
    with open(TILED_IMG, 'rb') as f:
        data = f.read()

    image_id = str(uuid.uuid4())
    key = f"images/{case_id}/{image_id}.jpeg"
    checksum = sha256(data)

    print(f"  Uploading tiled image to MinIO ({len(data)/1024:.0f} KB)...")
    uri = upload_to_minio(minio_client, key, data, 'image/jpeg')

    cur.execute("""
        INSERT INTO images (id, case_id, format, storage_uri, checksum, size_bytes, stain, magnification, notes, uploaded_at)
        VALUES (%s, %s, 'jpeg', %s, %s, %s, 'H&E', '20x', 'TCGA-69-7979 WSI tiled 384px', NOW())
    """, (image_id, case_id, uri, checksum, len(data)))
    conn.commit()
    print(f"  Image created: {image_id}")
    return image_id


# ─── Step 3: Generate tile overlay from CSV predictions ────────────────────

def generate_overlay(minio_client, case_id, rb_id):
    """Create a colored tile map image from CSV predictions."""
    print("  Reading CSV predictions...")
    df = pd.read_csv(CSV_FILE)
    df['label'] = df['pred_class'].map(ID2LABEL)

    tile_size = 384  # from filename
    max_x = df['x'].max() + tile_size
    max_y = df['y'].max() + tile_size

    # Downsample for a manageable image
    scale = 8  # Each tile becomes 384/8 = 48 pixels
    img_w = max_x // scale
    img_h = max_y // scale
    print(f"  Generating overlay image {img_w}x{img_h}...")

    overlay = np.ones((img_h, img_w, 3), dtype=np.uint8) * 240  # light gray background

    for _, row in df.iterrows():
        x0 = int(row['x']) // scale
        y0 = int(row['y']) // scale
        x1 = x0 + tile_size // scale
        y1 = y0 + tile_size // scale
        color = PATTERN_COLORS.get(row['label'], (0.5, 0.5, 0.5))
        color_uint8 = tuple(int(c * 255) for c in color)
        overlay[y0:y1, x0:x1] = color_uint8

    # Save as PNG
    pil_img = Image.fromarray(overlay)
    buf = io.BytesIO()
    pil_img.save(buf, format='PNG')
    overlay_bytes = buf.getvalue()

    # Also create a nice figure with legend
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.imshow(overlay)
    ax.set_title(f'TCGA-69-7979 — Tile-Level Pattern Predictions ({len(df)} tiles)', fontsize=14)
    ax.axis('off')

    patches = [mpatches.Patch(color=PATTERN_COLORS[p], label=f"{p} ({(df['label']==p).sum()} tiles, {(df['label']==p).sum()/len(df)*100:.1f}%)")
               for p in ['acinar', 'lepidic', 'micropapillary', 'mucinous', 'papillary', 'solid']]
    ax.legend(handles=patches, loc='lower right', fontsize=9, framealpha=0.9)

    fig_buf = io.BytesIO()
    fig.savefig(fig_buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    overlay_with_legend = fig_buf.getvalue()

    # Upload both to MinIO
    key_overlay = f"results/{case_id}/{rb_id}/roi_overlay_combined.png"
    uri_overlay = upload_to_minio(minio_client, key_overlay, overlay_with_legend, 'image/png')

    print(f"  Overlay uploaded: {key_overlay} ({len(overlay_with_legend)/1024:.0f} KB)")
    return uri_overlay, overlay_with_legend


# ─── Step 4: Generate SHAP plots ──────────────────────────────────────────

def generate_shap_plots(minio_client, case_id, rb_id):
    """Train XGBoost on cohort, generate SHAP bar/beeswarm/force for TCGA-69-7979."""
    print("  Loading cohort data for SHAP...")
    cohort = pd.read_excel(COHORT_FILE)

    # Get unique patients with pattern data
    patients = cohort.dropna(subset=['n_tiles_total']).groupby('case_barcode').first().reset_index()
    print(f"  Cohort: {len(patients)} patients with pattern data")

    # Target patient features
    target_patient = patients[patients['case_barcode'] == CASE_PREFIX]
    if target_patient.empty:
        print("  WARNING: TCGA-69-7979 not found in cohort. Using CSV stats.")
        target_features = pd.DataFrame([{
            'pct_acinar': 0.05664, 'pct_lepidic': 0.000898,
            'pct_micropapillary': 0.000561, 'pct_mucinous': 0.367153,
            'pct_papillary': 0.007632, 'pct_solid': 0.567116,
        }])
    else:
        target_features = target_patient[FEATURES]

    X = patients[FEATURES].fillna(0)

    artifacts = {}
    gene_results = {}

    for gene in KEY_GENES:
        print(f"  Training XGBoost for {gene}...")
        # Binary: does this patient have a mutation in this gene?
        gene_mutations = cohort[cohort['Hugo_Symbol'] == gene]['case_barcode'].unique()
        y = patients['case_barcode'].isin(gene_mutations).astype(int)

        n_pos = y.sum()
        n_neg = len(y) - n_pos
        print(f"    {gene}: {n_pos} positive, {n_neg} negative")

        if n_pos == 0:
            print(f"    No positive samples for {gene}, creating dummy results")
            gene_results[gene] = {'score': 0.1, 'status': 'NEG'}
            # Still generate placeholder plots
            for ptype in ['bar', 'beeswarm', 'force']:
                fig, ax = plt.subplots(figsize=(8, 5))
                ax.text(0.5, 0.5, f'No data for {gene} mutation prediction',
                        ha='center', va='center', fontsize=14, color='gray')
                ax.axis('off')
                buf = io.BytesIO()
                fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
                plt.close(fig)
                key = f"results/{case_id}/{rb_id}/xai/shap_{gene}_{ptype}.png"
                uri = upload_to_minio(minio_client, key, buf.getvalue(), 'image/png')
                artifacts[f"{gene}_{ptype}"] = {'uri': uri, 'hash': sha256(buf.getvalue()), 'data': buf.getvalue()}
            continue

        # Scale_pos_weight for imbalanced data
        spw = max(n_neg / max(n_pos, 1), 1)
        model = xgb.XGBClassifier(
            n_estimators=100, max_depth=3, learning_rate=0.1,
            scale_pos_weight=spw, use_label_encoder=False,
            eval_metric='logloss', random_state=42
        )
        model.fit(X, y)

        # Predict for target
        target_X = target_features[FEATURES].fillna(0)
        pred_proba = model.predict_proba(target_X)[0][1]
        pred_status = 'POS' if pred_proba >= 0.5 else 'NEG'
        gene_results[gene] = {'score': float(pred_proba), 'status': pred_status}
        print(f"    {gene} prediction: {pred_status} (score={pred_proba:.4f})")

        # SHAP values
        explainer = shap.TreeExplainer(model)
        shap_values_all = explainer(X)
        shap_values_case = explainer(target_X)

        # ─── Bar plot ───
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.plots.bar(shap_values_all, show=False, ax=ax)
        ax.set_title(f'SHAP Bar — {gene} Mutation (Global Feature Importance)', fontsize=12)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        key = f"results/{case_id}/{rb_id}/xai/shap_{gene}_bar.png"
        uri = upload_to_minio(minio_client, key, buf.getvalue(), 'image/png')
        artifacts[f"{gene}_bar"] = {'uri': uri, 'hash': sha256(buf.getvalue()), 'data': buf.getvalue()}
        print(f"    Uploaded SHAP bar for {gene}")

        # ─── Beeswarm plot ───
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.plots.beeswarm(shap_values_all, show=False)
        plt.title(f'SHAP Beeswarm — {gene} Mutation (Feature Impact Distribution)', fontsize=12)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close('all')
        key = f"results/{case_id}/{rb_id}/xai/shap_{gene}_beeswarm.png"
        uri = upload_to_minio(minio_client, key, buf.getvalue(), 'image/png')
        artifacts[f"{gene}_beeswarm"] = {'uri': uri, 'hash': sha256(buf.getvalue()), 'data': buf.getvalue()}
        print(f"    Uploaded SHAP beeswarm for {gene}")

        # ─── Force plot ───
        fig, ax = plt.subplots(figsize=(12, 3))
        # Use waterfall for single instance (force plot alternative)
        shap.plots.waterfall(shap_values_case[0], show=False)
        plt.title(f'SHAP Force — {gene} for {CASE_PREFIX} (Case-Level Explanation)', fontsize=11)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close('all')
        key = f"results/{case_id}/{rb_id}/xai/shap_force_{gene}_case.png"
        uri = upload_to_minio(minio_client, key, buf.getvalue(), 'image/png')
        artifacts[f"{gene}_force"] = {'uri': uri, 'hash': sha256(buf.getvalue()), 'data': buf.getvalue()}
        print(f"    Uploaded SHAP force for {gene}")

    return artifacts, gene_results


# ─── Step 5: Create all DB records ─────────────────────────────────────────

def create_db_records(conn, case_id, image_id, overlay_uri, overlay_data, shap_artifacts, gene_results):
    """Create ml_job, result_bundle, pattern_results, genetic_results, xai_artifacts, morphologic_profile."""
    cur = conn.cursor()

    # Check existing
    cur.execute("SELECT id FROM result_bundles WHERE case_id = %s", (case_id,))
    existing = cur.fetchone()
    if existing:
        print(f"  Result bundle already exists: {existing[0]}. Cleaning up...")
        rb_id = existing[0]
        cur.execute("DELETE FROM morphologic_profiles WHERE result_bundle_id = %s", (rb_id,))
        cur.execute("DELETE FROM xai_artifacts WHERE result_bundle_id = %s", (rb_id,))
        cur.execute("DELETE FROM genetic_results WHERE result_bundle_id = %s", (rb_id,))
        cur.execute("DELETE FROM pattern_results WHERE result_bundle_id = %s", (rb_id,))
        cur.execute("DELETE FROM result_bundles WHERE id = %s", (rb_id,))
        cur.execute("DELETE FROM ml_jobs WHERE case_id = %s", (case_id,))
        conn.commit()

    # Read CSV for pattern stats
    df = pd.read_csv(CSV_FILE)
    total = len(df)
    dist = df['pred_class'].value_counts()

    pattern_pcts = {}
    for pid, label in ID2LABEL.items():
        count = dist.get(pid, 0)
        pattern_pcts[label] = count / total * 100

    predominant = max(pattern_pcts, key=pattern_pcts.get)

    # ML Job
    job_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO ml_jobs (id, case_id, image_id, job_type, status, progress, started_at, ended_at, created_at)
        VALUES (%s, %s, %s, 'IMAGE_INFERENCE', 'COMPLETED', 1.0, NOW(), NOW(), NOW())
    """, (job_id, case_id, image_id))

    # Result Bundle
    rb_id = str(uuid.uuid4())
    pattern_composition = json.dumps({label: round(pct, 4) for label, pct in pattern_pcts.items()})
    cur.execute("""
        INSERT INTO result_bundles (id, case_id, image_id, job_id, model_profile, model_version,
            pattern_composition, predominant_pattern, evidence_source, intended_use, created_at)
        VALUES (%s, %s, %s, %s, 'CTransPath+FuzzyArcLoss_v3', '1.0.0',
            %s, %s, 'THESIS_INTERNAL', 'Research only — NOT for clinical diagnosis', NOW())
    """, (rb_id, case_id, image_id, job_id, pattern_composition, predominant))

    # Update job with result_bundle_id
    cur.execute("UPDATE ml_jobs SET result_bundle_id = %s WHERE id = %s", (rb_id, job_id))

    # Pattern Results
    for label, pct in pattern_pcts.items():
        pr_id = str(uuid.uuid4())
        score = pct / 100.0
        is_conclusive = bool(pct > 5.0)
        cur.execute("""
            INSERT INTO pattern_results (id, result_bundle_id, pattern, score, percentage, is_conclusive, overlay_uri)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (pr_id, rb_id, label, float(round(score, 4)), float(round(pct, 2)), is_conclusive, overlay_uri if is_conclusive else None))

    # Genetic Results
    for gene in KEY_GENES:
        gr_id = str(uuid.uuid4())
        gr = gene_results.get(gene, {'score': 0.0, 'status': 'INCONCLUSIVE'})
        cur.execute("""
            INSERT INTO genetic_results (id, result_bundle_id, mutation, score, status, evidence_source, intended_use)
            VALUES (%s, %s, %s, %s, %s, 'THESIS_INTERNAL_XGBOOST', 'Research only')
        """, (gr_id, rb_id, gene, float(round(gr['score'], 4)), str(gr['status'])))

    # XAI Artifacts
    for art_key, art_data in shap_artifacts.items():
        xa_id = str(uuid.uuid4())
        gene = art_key.split('_')[0]
        if 'bar' in art_key:
            art_type = 'shap_bar'
        elif 'beeswarm' in art_key:
            art_type = 'shap_beeswarm'
        elif 'force' in art_key:
            art_type = 'shap_force'
        else:
            art_type = 'shap'
        cur.execute("""
            INSERT INTO xai_artifacts (id, result_bundle_id, artifact_type, gene, uri, hash, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (xa_id, rb_id, art_type, gene, art_data['uri'], art_data['hash']))

    # Also add overlay as an artifact
    xa_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO xai_artifacts (id, result_bundle_id, artifact_type, gene, uri, hash, created_at)
        VALUES (%s, %s, 'roi_overlay', NULL, %s, %s, NOW())
    """, (xa_id, rb_id, overlay_uri, sha256(overlay_data)))

    # Morphologic Profile
    mp_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO morphologic_profiles (id, result_bundle_id, n_tiles_total,
            pct_lepidic, pct_acinar, pct_papillary, pct_micropapillary, pct_solid, pct_mucinous)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (mp_id, rb_id, int(total),
          float(round(pattern_pcts.get('lepidic', 0), 4)),
          float(round(pattern_pcts.get('acinar', 0), 4)),
          float(round(pattern_pcts.get('papillary', 0), 4)),
          float(round(pattern_pcts.get('micropapillary', 0), 4)),
          float(round(pattern_pcts.get('solid', 0), 4)),
          float(round(pattern_pcts.get('mucinous', 0), 4))))

    conn.commit()
    print(f"  Result bundle created: {rb_id}")
    print(f"  ML Job: {job_id}")
    print(f"  Predominant pattern: {predominant}")
    return rb_id, job_id


# ─── Step 6: Create EHR document ──────────────────────────────────────────

def create_ehr_document(conn, case_id):
    """Create EHR document from the mutation XLSX data."""
    cur = conn.cursor()

    # Check if EHR already exists
    cur.execute("SELECT id FROM ehr_documents WHERE case_id = %s", (case_id,))
    existing = cur.fetchone()
    if existing:
        print(f"  EHR document already exists: {existing[0]}")
        return existing[0]

    print("  Reading mutation data for EHR...")
    df = pd.read_excel(EHR_XLSX)

    # Extract unique mutations
    mutations = df[['Hugo_Symbol', 'Variant_Classification', 'Variant_Type', 'Chromosome',
                     'Start_Position', 'HGVSp_Short']].drop_duplicates()

    # Key mutations
    key_mutations = mutations[mutations['Hugo_Symbol'].isin(KEY_GENES)]

    # All unique genes
    all_genes = sorted(df['Hugo_Symbol'].unique())

    # Pattern data from CSV
    csv_df = pd.read_csv(CSV_FILE)
    total_tiles = len(csv_df)
    dist = csv_df['pred_class'].value_counts()

    # Build clinical text
    lines = [
        f"CLINICAL SUMMARY — {CASE_PREFIX}",
        f"Date: {datetime.now().strftime('%Y-%m-%d')}",
        "",
        "DIAGNOSIS: Lung Adenocarcinoma (LUAD)",
        "Sample: TCGA-69-7979-01Z-00-DX1",
        "Stain: H&E",
        "",
        "HISTOLOGIC PATTERN ANALYSIS:",
        f"Total tiles analyzed: {total_tiles}",
    ]
    for pid, label in sorted(ID2LABEL.items()):
        count = dist.get(pid, 0)
        pct = count / total_tiles * 100
        lines.append(f"  - {label.capitalize()}: {count} tiles ({pct:.1f}%)")

    predominant = max(ID2LABEL.values(), key=lambda l: dist.get({v:k for k,v in ID2LABEL.items()}[l], 0))
    lines.append(f"Predominant pattern: {predominant.upper()}")

    lines.append("")
    lines.append("SOMATIC MUTATIONS DETECTED:")
    lines.append(f"Total unique genes with mutations: {len(all_genes)}")
    lines.append(f"Total mutation events: {len(df)}")
    lines.append("")

    for _, m in key_mutations.iterrows():
        hgvsp = m['HGVSp_Short'] if pd.notna(m['HGVSp_Short']) else 'N/A'
        lines.append(f"  * {m['Hugo_Symbol']} — {m['Variant_Classification']} ({m['Variant_Type']}) "
                      f"chr{m['Chromosome']}:{m['Start_Position']} {hgvsp}")

    lines.append("")
    lines.append("OTHER NOTABLE MUTATIONS:")
    notable = mutations[~mutations['Hugo_Symbol'].isin(KEY_GENES)].head(20)
    for _, m in notable.iterrows():
        hgvsp = m['HGVSp_Short'] if pd.notna(m['HGVSp_Short']) else ''
        lines.append(f"  - {m['Hugo_Symbol']}: {m['Variant_Classification']} {hgvsp}")

    lines.append("")
    lines.append("NOTE: This is a research summary generated from TCGA/GDC genomic data.")
    lines.append("All findings should be confirmed with standard molecular diagnostics.")

    content = "\n".join(lines)

    ehr_id = str(uuid.uuid4())
    checksum = sha256(content.encode())
    cur.execute("""
        INSERT INTO ehr_documents (id, case_id, version, source, content_text, checksum, created_at)
        VALUES (%s, %s, 1, 'tcga_maf_import', %s, %s, NOW())
    """, (ehr_id, case_id, content, checksum))
    conn.commit()
    print(f"  EHR document created: {ehr_id}")
    return ehr_id


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("TCGA-69-7979 Full Data Loader")
    print("=" * 60)

    conn = psycopg2.connect(**DB_CONFIG)
    minio_client = get_minio()

    print("\n[1/6] Finding patient and case...")
    patient_id, case_id = find_patient_case(conn)

    print("\n[2/6] Uploading tiled image...")
    image_id = upload_image(conn, minio_client, case_id)

    # Generate a temp rb_id for MinIO paths
    rb_id = str(uuid.uuid4())

    print("\n[3/6] Generating tile overlay...")
    overlay_uri, overlay_data = generate_overlay(minio_client, case_id, rb_id)

    print("\n[4/6] Generating SHAP plots (training XGBoost on cohort)...")
    shap_artifacts, gene_results = generate_shap_plots(minio_client, case_id, rb_id)

    print("\n[5/6] Creating DB records...")
    final_rb_id, job_id = create_db_records(conn, case_id, image_id, overlay_uri, overlay_data, shap_artifacts, gene_results)

    print("\n[6/6] Creating EHR document...")
    ehr_id = create_ehr_document(conn, case_id)

    conn.close()

    print("\n" + "=" * 60)
    print("DONE! Summary:")
    print(f"  Patient:        {CASE_PREFIX} ({patient_id})")
    print(f"  Case:           {case_id}")
    print(f"  Image:          {image_id}")
    print(f"  Result Bundle:  {rb_id}")
    print(f"  ML Job:         {job_id}")
    print(f"  EHR Document:   {ehr_id}")
    print(f"  SHAP artifacts: {len(shap_artifacts)}")
    for gene in KEY_GENES:
        gr = gene_results.get(gene, {})
        print(f"  {gene}: {gr.get('status', 'N/A')} (score={gr.get('score', 0):.4f})")
    print("=" * 60)


if __name__ == '__main__':
    main()
