#!/usr/bin/env python3
"""
Cross-reference existing slides vs TCGA-LUAD MAF.
Identifies: which slides are LUAD vs LUSC, which LUAD cases are missing slides.

Run on your server:
  python3 crossref_slides_vs_luad_maf.py

Paths (edit if needed):
"""
import os
import pandas as pd
from pathlib import Path

SLIDES_DIR  = Path("/home/rapids/notebooks/slima/data/slides")
LUAD_MAF    = Path("/home/rapids/notebooks/slima/TGCA MAF/cohortMAF_LUAD2.maf")
LUSC_MAF    = Path("/home/rapids/notebooks/slima/TGCA MAF/cohortMAF_LUSC.maf")   # may not exist
OUT_DIR     = Path("/home/rapids/notebooks/slima/TGCA MAF")
GENES       = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

# ── 1. Read slide folder names ────────────────────────────────────────────────
slide_dirs = sorted([d.name for d in SLIDES_DIR.iterdir() if d.is_dir()])
print(f"Total slide folders found: {len(slide_dirs)}")

# Extract 12-char TCGA barcode: TCGA-XX-XXXX (first 3 fields)
def barcode12(slide_name):
    parts = slide_name.split("-")
    return "-".join(parts[:3]) if len(parts) >= 3 else None

slide_barcodes = {}  # barcode12 → full slide folder name
for s in slide_dirs:
    bc = barcode12(s)
    if bc:
        slide_barcodes[bc] = s

print(f"Unique 12-char barcodes from slides: {len(slide_barcodes)}")

# ── 2. Load LUAD MAF ──────────────────────────────────────────────────────────
print(f"\nLoading LUAD MAF: {LUAD_MAF} ...")
luad_df = pd.read_csv(LUAD_MAF, sep='\t', comment='#', low_memory=False,
                      usecols=['Tumor_Sample_Barcode', 'Hugo_Symbol'])
luad_df['barcode12'] = luad_df['Tumor_Sample_Barcode'].str[:12]
luad_cases = set(luad_df['barcode12'].unique())
print(f"Unique cases in LUAD MAF: {len(luad_cases)}")

# ── 3. Load LUSC MAF if available ────────────────────────────────────────────
lusc_cases = set()
if LUSC_MAF.exists():
    print(f"Loading LUSC MAF: {LUSC_MAF} ...")
    lusc_df = pd.read_csv(LUSC_MAF, sep='\t', comment='#', low_memory=False,
                          usecols=['Tumor_Sample_Barcode', 'Hugo_Symbol'])
    lusc_df['barcode12'] = lusc_df['Tumor_Sample_Barcode'].str[:12]
    lusc_cases = set(lusc_df['barcode12'].unique())
    print(f"Unique cases in LUSC MAF: {len(lusc_cases)}")

# ── 4. Classify each slide ────────────────────────────────────────────────────
luad_slides     = []   # slide in LUAD MAF
lusc_slides     = []   # slide in LUSC MAF
unknown_slides  = []   # slide not in either MAF

for bc, slide in slide_barcodes.items():
    if bc in luad_cases:
        luad_slides.append((bc, slide))
    elif bc in lusc_cases:
        lusc_slides.append((bc, slide))
    else:
        unknown_slides.append((bc, slide))

print(f"\n{'=' * 60}")
print(f"  SLIDE CLASSIFICATION")
print(f"{'=' * 60}")
print(f"  LUAD slides (in LUAD MAF) : {len(luad_slides)}")
print(f"  LUSC slides (in LUSC MAF) : {len(lusc_slides)}")
print(f"  Unknown (not in MAF)      : {len(unknown_slides)}")
print(f"  Total                     : {len(slide_barcodes)}")

# ── 5. Find LUAD cases with NO slide yet ─────────────────────────────────────
luad_slides_bcs = {bc for bc, _ in luad_slides}
missing_luad    = luad_cases - luad_slides_bcs

print(f"\n{'=' * 60}")
print(f"  LUAD COVERAGE")
print(f"{'=' * 60}")
print(f"  LUAD cases in MAF         : {len(luad_cases)}")
print(f"  LUAD cases WITH slide     : {len(luad_slides_bcs)}")
print(f"  LUAD cases MISSING slide  : {len(missing_luad)}")
print(f"  Coverage                  : {len(luad_slides_bcs)/len(luad_cases)*100:.1f}%")

# ── 6. Mutation counts for current LUAD slides only ──────────────────────────
print(f"\n{'=' * 60}")
print(f"  MUTATION COUNTS — LUAD slides you already have")
print(f"{'=' * 60}")
luad_maf_subset = luad_df[luad_df['barcode12'].isin(luad_slides_bcs)]
for gene in GENES:
    n = luad_maf_subset[luad_maf_subset['Hugo_Symbol'] == gene]['barcode12'].nunique()
    pct = n / len(luad_slides_bcs) * 100 if luad_slides_bcs else 0
    viable = "✓" if n >= 25 else "✗ low"
    print(f"  {gene:<8} {n:>4} / {len(luad_slides_bcs)} ({pct:.1f}%)  {viable}")

# ── 7. Mutation counts if ALL 557 LUAD cases were available ──────────────────
print(f"\n{'=' * 60}")
print(f"  MUTATION COUNTS — Full LUAD MAF (557 cases, if all slides downloaded)")
print(f"{'=' * 60}")
for gene in GENES:
    n = luad_df[luad_df['Hugo_Symbol'] == gene]['barcode12'].nunique()
    pct = n / len(luad_cases) * 100
    viable = "✓" if n >= 25 else "✗ low"
    print(f"  {gene:<8} {n:>4} / {len(luad_cases)} ({pct:.1f}%)  {viable}")

# ── 8. Save lists to files ────────────────────────────────────────────────────
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Save LUAD slide IDs (for benchmark — use these, drop LUSC)
luad_slide_list = [slide for _, slide in luad_slides]
with open(OUT_DIR / "luad_slide_ids_available.txt", "w") as f:
    f.write("\n".join(luad_slide_list))

# Save missing LUAD case barcodes (need to download SVS for these)
with open(OUT_DIR / "luad_cases_missing_slides.txt", "w") as f:
    f.write("\n".join(sorted(missing_luad)))

# Save LUSC slide IDs (separate, for reference)
lusc_slide_list = [slide for _, slide in lusc_slides]
with open(OUT_DIR / "lusc_slide_ids.txt", "w") as f:
    f.write("\n".join(lusc_slide_list))

# Save unknown
unk_list = [slide for _, slide in unknown_slides]
with open(OUT_DIR / "slides_not_in_maf.txt", "w") as f:
    f.write("\n".join(unk_list))

print(f"\n{'=' * 60}")
print(f"  OUTPUT FILES SAVED to {OUT_DIR}/")
print(f"{'=' * 60}")
print(f"  luad_slide_ids_available.txt   → {len(luad_slide_list)} slides (use for benchmark)")
print(f"  luad_cases_missing_slides.txt  → {len(missing_luad)} cases (download these SVS)")
print(f"  lusc_slide_ids.txt             → {len(lusc_slide_list)} LUSC slides (exclude from LUAD benchmark)")
print(f"  slides_not_in_maf.txt          → {len(unk_list)} unclassified slides")

# ── 9. Quick check of what data each LUAD slide has ──────────────────────────
print(f"\n{'=' * 60}")
print(f"  DATA COMPLETENESS CHECK — LUAD slides")
print(f"{'=' * 60}")
has_probs = 0
has_emb   = 0
has_both  = 0
for _, slide in luad_slides:
    slide_path = SLIDES_DIR / slide
    p = (slide_path / "pattern_probs.npy").exists()
    e = (slide_path / "embeddings.npy").exists()
    if p: has_probs += 1
    if e: has_emb += 1
    if p and e: has_both += 1

n = len(luad_slides)
print(f"  has pattern_probs.npy : {has_probs} / {n} ({has_probs/n*100:.0f}%)")
print(f"  has embeddings.npy    : {has_emb}   / {n} ({has_emb/n*100:.0f}%)")
print(f"  has BOTH (ready)      : {has_both}  / {n} ({has_both/n*100:.0f}%)")
print(f"\n  → {has_both} LUAD slides are immediately usable for benchmark re-run")
print(f"  → {n - has_both} LUAD slides need processing before benchmark")
