#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  MASTER RUNNER: Download all external LUAD cohorts for thesis
# ══════════════════════════════════════════════════════════════════════════════
#
#  Datasets:
#    1. CPTAC-3 LUAD   (~111 patients, ~140 slides, multi-hospital USA)
#    2. APOLLO-LUAD     (~87 patients, ~87+ slides, DoD/VA hospitals)
#    3. CDDP_EAGLE-1    (~31 patients, ~49 slides, Lombardy Italy)
#
#  Total additional: ~229 patients → combined with TCGA-LUAD (~557) = ~786
#
#  Run:
#    nohup bash run_all_downloads.sh > output_all_downloads.txt 2>&1 &
#    tail -f output_all_downloads.txt
#
# ══════════════════════════════════════════════════════════════════════════════

set -e  # Exit on error

SCRIPT_DIR="/home/rapids/notebooks/slima/scripts"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  MULTI-COHORT LUAD DOWNLOAD PIPELINE                          ║"
echo "║  Target: ~229 additional LUAD patients for thesis              ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "  Start time: $(date)"
echo ""

# ── 1. CPTAC-3 LUAD MAF ──────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [1/5] Downloading CPTAC-3 LUAD mutation data (MAF)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "${SCRIPT_DIR}/download_cptac3_luad_maf.py"
echo "  [1/5] ✓ CPTAC-3 MAF complete"
echo ""

# ── 2. CPTAC-3 LUAD SVS ──────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [2/5] Downloading CPTAC-3 LUAD slides (SVS)..."
echo "        WARNING: This may download ~100+ GB of slide images"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "${SCRIPT_DIR}/download_cptac3_luad_svs.py"
echo "  [2/5] ✓ CPTAC-3 SVS complete"
echo ""

# ── 3. APOLLO-LUAD MAF + SVS ─────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [3/5] Downloading APOLLO-LUAD mutations + slides..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "${SCRIPT_DIR}/download_apollo_luad.py"
echo "  [3/5] ✓ APOLLO-LUAD complete"
echo ""

# ── 4. EAGLE LUAD MAF + SVS ──────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [4/5] Downloading EAGLE LUAD mutations + slides..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "${SCRIPT_DIR}/download_eagle_luad.py"
echo "  [4/5] ✓ EAGLE complete"
echo ""

# ── 5. Merge all cohorts ─────────────────────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  [5/5] Merging all cohorts into unified dataset..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "${SCRIPT_DIR}/merge_luad_cohorts.py"
echo "  [5/5] ✓ Merge complete"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ALL DOWNLOADS COMPLETE                                        ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "  End time: $(date)"
echo ""
echo "  Output files:"
echo "    MAFs:"
echo "      - cohortMAF_CPTAC3_LUAD.maf"
echo "      - cohortMAF_APOLLO_LUAD.maf"
echo "      - cohortMAF_EAGLE_LUAD.maf"
echo "    Unified:"
echo "      - unified_luad_mutation_labels.csv"
echo "      - unified_luad_slide_inventory.csv"
echo "    Slides:"
echo "      - data/slides_cptac3_luad/"
echo "      - data/slides_apollo_luad/"
echo "      - data/slides_eagle_luad/"
echo ""
echo "  NEXT: Run tile extraction + embeddings on new slides,"
echo "        then re-run ABMIL benchmark with expanded cohort."
echo ""
