#!/usr/bin/env python3
"""
Download TCGA-LUAD Masked Somatic Mutation MAF files from GDC API.
Downloads in small batches to avoid GDC server errors.
Based on the TCGA-LUSC MAF download script
"""
import os, json, sys, gzip, tarfile

try:
    import requests
except ImportError:
    os.system("pip install requests --break-system-packages")
    import requests

OUT_PATH = "/home/rapids/notebooks/slima/TGCA MAF/cohortMAF_LUAD2.maf"

# Step 1: Query GDC for file IDs
print("=" * 60)
print("Querying GDC API for TCGA-LUAD MAF files...")
print("=" * 60)

filters = {
    "op": "and",
    "content": [
        {"op": "=", "content": {"field": "cases.project.project_id", "value": "TCGA-LUAD"}},
        {"op": "=", "content": {"field": "data_category", "value": "Simple Nucleotide Variation"}},
        {"op": "=", "content": {"field": "data_type", "value": "Masked Somatic Mutation"}},
        {"op": "=", "content": {"field": "data_format", "value": "MAF"}},
    ]
}

params = {
    "filters": json.dumps(filters),
    "fields": "file_id,file_name,file_size,cases.submitter_id,cases.case_id",
    "size": 1000,
}

r = requests.get("https://api.gdc.cancer.gov/files", params=params, timeout=60)
data = r.json()
hits = data['data']['hits']
print(f"Found {len(hits)} MAF files for TCGA-LUAD")

file_ids = [h['file_id'] for h in hits]

# Step 2: Download in small batches and merge
BATCH_SIZE = 10
header_written = False
total_variants = 0
total_files = 0
errors = 0

os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

with open(OUT_PATH, 'w') as out_f:
    for batch_start in range(0, len(file_ids), BATCH_SIZE):
        batch = file_ids[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(file_ids) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"  Batch {batch_num}/{total_batches} ({total_files} files, {total_variants} variants so far)...", flush=True)

        try:
            r = requests.post(
                "https://api.gdc.cancer.gov/data",
                json={"ids": batch},
                headers={"Content-Type": "application/json"},
                timeout=120,
            )

            if r.status_code != 200:
                errors += 1
                print(f"    [WARN] HTTP {r.status_code}")
                continue

            content = r.content
            tmp = "/tmp/gdc_batch_luad.tar.gz"
            with open(tmp, 'wb') as f:
                f.write(content)

            try:
                with tarfile.open(tmp, 'r:gz') as tar:
                    for member in tar.getmembers():
                        if not (member.name.endswith('.maf.gz') or member.name.endswith('.maf')):
                            continue
                        f = tar.extractfile(member)
                        if f is None:
                            continue
                        raw = f.read()
                        if member.name.endswith('.maf.gz'):
                            text = gzip.decompress(raw).decode('utf-8', errors='replace')
                        else:
                            text = raw.decode('utf-8', errors='replace')

                        lines = text.strip().split('\n')
                        header_line = None
                        for line in lines:
                            if line.startswith('#'):
                                continue
                            if header_line is None:
                                header_line = line
                                if not header_written:
                                    out_f.write(header_line + '\n')
                                    header_written = True
                                continue
                            out_f.write(line + '\n')
                            total_variants += 1
                        total_files += 1

            except tarfile.TarError:
                try:
                    text = gzip.decompress(content).decode('utf-8', errors='replace')
                except Exception:
                    text = content.decode('utf-8', errors='replace')

                lines = text.strip().split('\n')
                header_line = None
                for line in lines:
                    if line.startswith('#'):
                        continue
                    if header_line is None:
                        header_line = line
                        if not header_written:
                            out_f.write(header_line + '\n')
                            header_written = True
                        continue
                    out_f.write(line + '\n')
                    total_variants += 1
                total_files += 1

            if os.path.exists(tmp):
                os.remove(tmp)

        except Exception as e:
            errors += 1
            print(f"    [WARN] Batch {batch_num} failed: {e}")

print(f"\n{'=' * 60}")
print(f"DONE — TCGA-LUAD MAF")
print(f"  Files merged : {total_files}")
print(f"  Total variants: {total_variants:,}")
print(f"  Errors        : {errors}")
print(f"  Output        : {OUT_PATH}")
if os.path.exists(OUT_PATH):
    print(f"  File size     : {os.path.getsize(OUT_PATH) / 1024 / 1024:.1f} MB")
print(f"{'=' * 60}")

# ── Quick sanity check: count unique cases ────────────────────────────────
print("\nRunning quick sanity check on output MAF...")
try:
    import pandas as pd
    df = pd.read_csv(OUT_PATH, sep='\t', comment='#', low_memory=False,
                     usecols=['Tumor_Sample_Barcode', 'Hugo_Symbol', 'Variant_Classification'])
    cases = df['Tumor_Sample_Barcode'].str[:12].nunique()
    genes  = df['Hugo_Symbol'].nunique()
    print(f"  Unique TCGA cases (12-char barcode) : {cases}")
    print(f"  Unique genes mutated                : {genes}")
    print(f"  Total variant rows                  : {len(df):,}")
    print()
    # Count per gene of interest
    for gene in ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10']:
        n = df[df['Hugo_Symbol'] == gene]['Tumor_Sample_Barcode'].str[:12].nunique()
        pct = n / cases * 100
        print(f"  {gene:<8} mutated in {n:>4} / {cases} cases  ({pct:.1f}%)")
except Exception as e:
    print(f"  [sanity check skipped: {e}]")
