# Thesis Reproducibility Archive

Scripts, logs, cohort definitions and results that back the experiments of the doctoral thesis:

**"Pattern-Informed Fuzzy Deep Learning for Interpretable Genotype–Phenotype Inference in Lung Adenocarcinoma under Data Scarcity"**
(Ph.D. Thesis, Department of Informatics, University of Fribourg).

All files in this directory were copied from the DGX H100 server where the experiments ran
(`notebooks/slima/`). Every result file that still used the pre-4-April-2026 histologic pattern
names has been remapped to the pathologist-verified ANORAK classes (see
`README_ADDENDUM_pattern_correction_and_provenance.md` and `tools/`). Original, unmodified
copies are kept on the DGX under `notebooks/slima/backups/`.

## Directory Structure

```
Thesis/
├── training/
│   ├── artefact1_pattern_classifier/    # FuzzyArcLoss V2 on Zenodo-ANORAK (6 patterns)
│   │   └── *.py                         # Backbone, ablation (18 losses), Optuna, K-fold scripts
│   ├── artefact2_mutation_abmil/        # PI-ABMIL: 5-fold CV mutation prediction
│   │   ├── pattern_informed_abmil_benchmark_v2_patched.py   # <-- script that produced results_luad_full_v2 (14 Mar 2026)
│   │   └── *.py                         # earlier versions kept for provenance
│   ├── artefact3_mutation_choquet/      # FC-MIL: Fuzzy Choquet MIL condition
│   │   └── pattern_informed_abmil_benchmark_FuzzyChoquetAggregation.py
│   ├── xgboost_baseline/                # B1: XGBoost on slide-level pattern features
│   └── data_preparation/                # GDC download, tiling, CTransPath embeddings, MAF -> labels,
│                                        # ANORAK overlay correction (4 Apr 2026)
│
├── data/
│   └── cohort/
│       ├── labels.csv                   # 687-slide inventory x 6 genes (binary labels from the GDC MAF)
│       ├── luad_slide_ids_available.txt # 505 LUAD slides actually evaluated (benchmark --slide_list)
│       ├── luad_slide_ids_full.txt      # all 687 slide ids of the inventory (same set as labels.csv)
│       └── luad_cases_missing_slides.txt # 51 LUAD cases whose SVS could not be downloaded
│
├── inference/
│   └── *.ipynb                          # XGBoost inference notebooks (legacy, B1 development)
│
├── logs/
│   ├── mutation_5fold_results/          # = results_luad_full_v2 on the DGX
│   │   ├── summary_table.csv            # 36 (condition, gene) rows: AUROC / AUPRC / F1 mean+std over 5 folds
│   │   ├── per_fold_json/               # 180 JSON files (6 cond x 6 genes x 5 folds)
│   │   │   └── metrics_<cond>_<gene>_fold<k>.json
│   │   └── worker_logs/                 # Per-gene training logs (one H100 per gene)
│   │       └── worker_<gene>.txt
│   ├── pattern_classifier_results/      # Artefact 1 logs and evaluations
│   │   ├── output_ablation_best_rev13.txt       # 18-loss ablation benchmark (Table 6.3)
│   │   ├── output_optuna_fuzzyarcv2_best.txt    # Optuna search for FuzzyArcLoss V2
│   │   ├── output_kfold_fuzzyv2_sphereface.txt  # K-fold statistical validation
│   │   ├── ablation_results_v16_optuna.json
│   │   ├── eval_results.json                    # Full-dataset evaluation (N=637 tiles)
│   │   └── eval_results_val_set.json            # Held-out evaluation (N=128 tiles, 80/20 split)
│   ├── data_pipeline/                   # SVS download and 6-GPU embedding pipeline logs
│   └── tcga_tile_inference_dec2025/     # FuzzyArcLoss V2 tile inference on 322 TCGA slides (Nov-Dec 2025,
│       ├── tcga_tiles_384_predictions_322_slides.zip   # x,y,pred_class,pattern  (corrected names)
│       ├── tcga_*_histologic_patterns*.csv             # per-case / per-slide pattern % (B1 development input)
│       └── pred_class_to_pattern_4apr2026.json         # index -> true class sidecar
│
├── evaluation/
│   ├── eval_pattern_confusion.py        # Confusion matrix of FuzzyArcLoss V2 (Figure 6.5)
│   ├── verify_fold_aurocs.py            # Verify best-fold AUROCs (Table 6.9) from per_fold_json
│   ├── extract_fold_aurocs.py           # Extract per-fold AUROCs from checkpoints
│   └── find_high_prob_slides.py         # High-P(mut) slides for the case studies
│
├── figures/
│   ├── summary_data.py                  # shared loader: reads logs/mutation_5fold_results/summary_table.csv
│   ├── gen_auroc_bar_chart.py           # Figure 6.6:  AUROC per gene (6 conditions)
│   ├── gen_auroc_heatmap.py             # Figure 6.7:  AUROC heatmap (condition x gene)
│   ├── gen_auroc_difference.py          # Figure 6.8:  delta AUROC vs B2
│   ├── gen_auroc_radar.py               # Figure 6.9:  radar plot (4 conditions)
│   ├── gen_auprc_bar_chart.py           # Figure 6.10: AUPRC per gene
│   ├── gen_choquet_plots.py             # Choquet Shapley / interaction bar charts (Table 6.12)
│   ├── generate_attention_maps.py       # Attention heatmaps on WSIs
│   ├── visualize_attention_patterns.py
│   └── gen_*.py                         # Diagrams (ablation flowchart, fuzzy MFs, SHAP quadrant, ...)
│
├── tools/
│   ├── remap_pattern_names_4apr2026.py  # idempotent legacy -> true pattern-name remapper (JSON/TXT/CSV)
│   ├── remap_pattern_names_in_scripts.py # same remap for .py/.ipynb (+ stable class order for Artefact 1)
│   ├── add_pattern_names_to_tile_predictions.py  # adds `pattern` (true name of pred_class) to tile CSVs
│   ├── PATTERN_REMAP_4_apr_2026.py      # mapping table used by the remappers
│   └── remap_manifest_dgx.json          # which DGX files were remapped, with checksums
│
├── README_ADDENDUM_pattern_correction_and_provenance.md
└── README.md                            # This file
```

## Cohort actually evaluated

* `data/cohort/labels.csv` lists **687 slides** (505 single-slide LUAD + 19 extra slides of
  multi-slide LUAD patients + 150 TCGA-LUSC + 13 slides without a MAF match). Slides absent from
  `cohortMAF_LUAD2.maf` received all-zero (wild-type) labels in this file.
* The Chapter 6 benchmark (`results_luad_full_v2`) was run with
  `--slide_list luad_slide_ids_available.txt`, i.e. on the **505 LUAD slides from 505 distinct
  patients**. Each 5-fold split therefore has ≈404 training and ≈101 test slides.
  (The methodology text in §5.8 describes the larger 668-patient / 687-slide inventory with
  ≈549/138 slides per fold; the archived results correspond to the 505-slide run.)

## Key Results Files

### `logs/mutation_5fold_results/summary_table.csv`
Master table with all 36 (condition, gene) results. Columns:
`condition, gene, n_folds, auroc_mean, auroc_std, auprc_mean, auprc_std, f1_mean, f1_std`.
Backs Tables 6.5–6.8 and Figures 6.6–6.10.

### `logs/mutation_5fold_results/per_fold_json/`
180 JSON files, one per (condition, gene, fold), with the per-fold AUROC/AUPRC/F1 on the held-out
fold. They back Table 6.9 (best-fold AUROC) and the statistical tests of Finding 1.
Fold-level metrics are the maximum over epochs on the held-out fold (early stopping on that fold);
see the addendum for details. The FC-MIL JSONs also carry the Choquet Shapley values and
interaction indices used in Table 6.12 (pattern names already corrected).

### `logs/pattern_classifier_results/`
Artefact 1 evaluations. `eval_results_val_set.json` is the 80/20 held-out evaluation (N=128
tiles, macro-F1 0.886, per-class confusion counts) and `eval_results.json` the full-dataset
evaluation (N=637 tiles).
Note: the printed caption of Figure 6.5 states N=138 tiles; no evaluation with 138 tiles exists
on the DGX, the archived held-out evaluation has 128 tiles.

## Condition Naming Convention

| Code in CSV/JSON | Thesis label | Description |
|------|------|-------------|
| `baseline1_xgboost` | B1: XGB | Slide-level pattern features → XGBoost |
| `baseline2_abmil_embeddings` | B2: ABMIL-emb | CTransPath 512-d embeddings → ABMIL |
| `baseline3_abmil_patterns` | B3: ABMIL-pat | Pattern probabilities 6-d → ABMIL |
| `proposed_abmil_concat` | PI-ABMIL (ours) | Embeddings + patterns 518-d → ABMIL |
| `ablation_abmil_onehot` | Abl: one-hot | Embeddings + one-hot 518-d → ABMIL |
| `proposed_fuzzy_choquet` | FC-MIL (ours) | Dual pathway: ABMIL + Choquet integral |

## Reproducing the Figures

The five AUROC/AUPRC generators read `logs/mutation_5fold_results/summary_table.csv` through
`figures/summary_data.py`; nothing is hard-coded. Output goes to `figures/output/` by default:

```bash
cd Thesis/figures
python gen_auroc_bar_chart.py            # -> output/auroc_by_gene.png
python gen_auroc_heatmap.py              # -> output/auroc_heatmap.png
python gen_auroc_difference.py           # -> output/auroc_difference_vs_b2.png
python gen_auroc_radar.py                # -> output/auroc_radar_profile.png
python gen_auprc_bar_chart.py            # -> output/auprc_by_gene.png
# optional: --summary <path/to/summary_table.csv> --out-dir <dir> --out-name <file.png>
```

Requirements: `numpy`, `matplotlib` (no pandas needed).

**AUPRC caveat.** The version of `gen_auprc_bar_chart.py` used for the printed Figure 6.10 carried
AUPRC values typed by hand and rounded to two decimals; 32 of the 36 cells differ from
`summary_table.csv` (largest: FC-MIL/TP53 printed .63 vs archived .706; B2/TP53 .64 vs .695;
B1/EGFR .31 vs .235). The AUROC figures (6.6–6.9) match the CSV exactly. Regenerating
Figure 6.10 from the CSV with this script gives the archived values.

## Reproducing the 5-fold benchmark

```bash
# <benchmark_inputs> must contain labels.csv plus the per-slide embeddings / pattern probabilities
python training/artefact2_mutation_abmil/pattern_informed_abmil_benchmark_v2_patched.py \
    --data_dir <benchmark_inputs> \
    --slide_list data/cohort/luad_slide_ids_available.txt \
    --results_dir results_luad_full_v2 --genes TP53 EGFR KRAS STK11 KEAP1 RBM10 \
    --gene_parallel 6
```
Defaults: 5 folds, seed 42, 50 ABMIL epochs, lr 1e-4, hidden 256, attention 128, dropout 0.25,
XGBoost 300 estimators. Per-gene logs of the original run are in
`logs/mutation_5fold_results/worker_logs/`.

## Computational Environment

- **Pattern classifier training**: NVIDIA DGX, 6× H100 80GB HBM3, CUDA 12.x, PyTorch 2.x
- **Mutation prediction 5-fold CV**: 6× H100 (one gene per GPU), ~15–16 h total
- **Inference service**: Docker container with CTransPath + FuzzyArcLoss V2 checkpoint
