# Thesis Reproducibility Archive

Scripts, model weights, cohort definitions, logs and results that back the experiments of the doctoral thesis:

**"Pattern-Informed Fuzzy Deep Learning for Interpretable Genotype–Phenotype Inference in Lung Adenocarcinoma under Data Scarcity"**
(Servio Fernando Lima Reina, Ph.D. Thesis, Department of Informatics, University of Fribourg).

One script per archived result: every log / CSV / JSON in `logs/` was produced by the script
that sits next to it in `training/`, `evaluation/` or `figures/`. All files were copied from the
DGX H100 server where the experiments ran (`notebooks/slima/`). Audit notes are in `provenance/`.

## Directory Structure

```
Thesis/
├── training/
│   ├── artefact1_pattern_classifier/    # FuzzyArcLoss V2 on Zenodo-ANORAK (6 patterns, 637 tiles)
│   │   ├── SLIMA_ablation_study_loss_functions_ver_23_feb_2026_gpu_rev_13 (1).py  # 18-loss ablation -> output_ablation_best_rev13.txt (Table 6.1)
│   │   ├── SLIMA_optuna_fuzzyarcloss_v2_best model search_ 22 feb_2026 rev 2.py   # Optuna s,m,tau -> output_optuna_fuzzyarcv2_best.txt, best_fuzzyarcloss_v2.pth
│   │   └── SLIMA_kfold_statistical_validation_23 feb_2026 rev 13.py             # 5-fold x 3 seeds -> output_kfold_fuzzyv2_sphereface.txt (Table 6.3, 92.31%)
│   ├── artefact2_mutation_abmil/        # PI-ABMIL + all six benchmark conditions, 5-fold CV
│   │   └── pattern_informed_abmil_benchmark_v2_patched.py   # <-- produced logs/mutation_5fold_results (14 Mar 2026)
│   ├── artefact3_mutation_choquet/      # FC-MIL is implemented inside *_v2_patched.py (classes FuzzyMeasure,
│   │   └── README.md                    #   FuzzyChoquetAggregation, FuzzyChoquetMIL); README points to them
│   ├── xgboost_baseline/                # stand-alone XGBoost + TreeSHAP on slide-level pattern profiles (B1 development)
│   └── data_preparation/                # GDC download, MAF -> labels, cohort cross-reference, ANORAK overlay index,
│       ├── build_anorak_overlay_index.py        #   builds overlay_index.xlsx (637 tiles) from the Zenodo ANORAK release
│       ├── overlay_index.xlsx                   #   tile -> pattern index used to train Artefact 1
│       ├── pipeline_6gpu_parallel.py            #   tiling -> FuzzyArcLoss V2 -> CTransPath embeddings -> per-slide .npy (687 slides)
│       ├── SLIMA_PARALLEL_inferencing_hist_patterns_ver_24_feb_2026_gpu_optimized.py
│       ├── SLIMA_PARALELL_inferencing_hist_patterns_roi_parallel_ver_14_dec_2025.py  # produced logs/tcga_tile_inference_dec2025
│       ├── SLIMA Mapping MAF to CSV per tile wsi classification TGCA ver 17 dec 2025.ipynb  # -> *_dec2025.csv summaries
│       ├── crossref_slides_vs_luad_maf.py       #   defines the 505-slide cohort
│       ├── prepare_benchmark_inputs (1).py, extract_embeddings (2).py
│       └── download_*.py, mutation_report.py
│
├── models/
│   ├── best_fuzzyarcloss_v2.pth.xz      # Artefact 1 weights (xz, 96.8 MiB -> 111.8 MB .pth); see models/README.md
│   └── SHA256SUMS
│
├── data/
│   └── cohort/
│       ├── labels.csv                   # 687-slide inventory x 6 genes (binary labels from the GDC MAF)
│       ├── luad_slide_ids_available.txt # 505 LUAD slides actually evaluated (benchmark --slide_list)
│       ├── luad_slide_ids_full.txt      # all 687 slide ids of the inventory (same set as labels.csv)
│       └── luad_cases_missing_slides.txt # 51 LUAD cases whose SVS could not be downloaded
│
├── inference/
│   └── SLIMA_histology_mutation_xgboost_rev3_autodelim_threshold ver 1 feb 2026 (2).ipynb
│                                        # XGBoost B1 development notebook (reads logs/tcga_tile_inference_dec2025/*_dec2025.csv)
│
├── logs/
│   ├── mutation_5fold_results/          # = results_luad_full_v2 on the DGX
│   │   ├── summary_table.csv            # 36 (condition, gene) rows: AUROC / AUPRC / F1 mean+std over 5 folds
│   │   ├── per_fold_json/               # 180 JSON files (6 cond x 6 genes x 5 folds)
│   │   │   └── metrics_<cond>_<gene>_fold<k>.json
│   │   ├── orchestrator_output_benchmark_v2_patched.txt
│   │   └── worker_logs/worker_<gene>.txt    # per-gene training logs (one H100 per gene)
│   ├── pattern_classifier_results/      # Artefact 1 logs and evaluations
│   │   ├── output_ablation_best_rev13.txt       # 18-loss ablation benchmark (Table 6.1)
│   │   ├── output_optuna_fuzzyarcv2_best.txt    # Optuna search for FuzzyArcLoss V2
│   │   ├── output_kfold_fuzzyv2_sphereface.txt  # K-fold statistical validation (Table 6.3)
│   │   ├── ablation_results_v16_optuna.json
│   │   ├── eval_results.json                    # Full-dataset evaluation (N=637 tiles)
│   │   ├── eval_results_val_set.json            # Held-out evaluation (N=128 tiles, 80/20 split)
│   │   └── confusion_matrix_val_set.png         # Figure 6.5 as rendered
│   ├── data_pipeline/                   # SVS download and 6-GPU embedding pipeline logs
│   └── tcga_tile_inference_dec2025/     # ROI-model tile inference on 322 TCGA slides (14 Dec 2025, B1 development)
│       ├── tcga_tiles_384_predictions_322_slides.zip   # x,y,pred_class,pattern
│       ├── tcga_*_patterns*_dec2025.csv                # per-case (305) / per-slide (322) pattern %
│       └── pred_class_to_pattern.json                  # index -> pattern sidecar
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
│   └── add_pattern_names_to_tile_predictions.py  # adds a `pattern` column (name of pred_class) to tile CSVs
├── docs/zenodo_deposit/                 # manifest, README and metadata of the Zenodo deposit (large artefacts)
├── provenance/                          # audit notes: class-name correction, what produced Chapter 6, pruned scripts
└── README.md                            # This file
```

## Class index order (applies to every model and result file)

The six pattern classes are indexed in a **fixed, non-alphabetical** order in all
checkpoints, `pattern_probs.npy` arrays, `prob_*` columns and `pred_class` values:

| index | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| class | micropapillary | cribriform | papillary | lepidic | solid | acinar |

The Artefact 1 training scripts therefore sort labels with the `CLASS_ORDER` constant
rather than `sorted()`; the inference scripts take the names from the checkpoint's
`id2label`. Do not re-derive the order alphabetically. Background in `provenance/README.md`.

## Model weights and large artefacts

| Artefact | Where |
|---|---|
| `best_fuzzyarcloss_v2.pth` — Artefact 1 (CTransPath Swin-T + FuzzyArcLoss V2; 5-fold 92.31 % ± 2.04, held-out acc 0.9375) | in git: `models/best_fuzzyarcloss_v2.pth.xz` (`xz -d`, verify with `models/SHA256SUMS`) and in the Zenodo deposit |
| 150 ABMIL / FC-MIL checkpoints of the Chapter 6 benchmark (`checkpoints_luad_v2.zip`, 104 MB) | Zenodo deposit |
| `pattern_probs.npy` for 687 TCGA-LUAD slides (`[n_tiles, 6]`, 138 MB zip) — the pattern channel of Artefacts 2/3 | Zenodo deposit |
| tile-level CSVs of the 336 slides processed by `pipeline_6gpu_parallel.py` (40 MB zip) | Zenodo deposit |
| `embeddings.npy` for 687 slides (`[n_tiles, 512]` float32, 38.6 GB) | regenerable from public TCGA-LUAD + CTransPath with `pipeline_6gpu_parallel.py`; sha256 of every file in `docs/zenodo_deposit/embeddings_sha256_manifest_REGENERABLE_not_deposited.txt`; six case-study slides deposited as a sample (341 MB) |
| `ctranspath.pth` (third-party backbone, Wang et al. MedIA 2022) | <https://github.com/Xiyue-Wang/TransPath>; sha256 in `docs/zenodo_deposit/ctranspath_sha256_NOT_REDISTRIBUTED.txt`. Only needed to retrain from scratch — the fine-tuned backbone is inside `best_fuzzyarcloss_v2.pth` |

**Zenodo DOI: _pending upload_** (package prepared on the DGX as `zenodo_deposit_thesis/`,
≈700 MB; `docs/zenodo_deposit/MANIFEST_sha256.txt` lists its contents).

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
see `provenance/README.md` §2. The FC-MIL JSONs also carry the Choquet Shapley values and
interaction indices used in Table 6.12.

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

## Reproducing the pipeline end to end

1. **Artefact 1** — `training/artefact1_pattern_classifier/` on the ANORAK tiles indexed by
   `training/data_preparation/overlay_index.xlsx` (ablation → Optuna → K-fold). The resulting
   checkpoint is `models/best_fuzzyarcloss_v2.pth`.
2. **Per-slide inputs** — `training/data_preparation/pipeline_6gpu_parallel.py` with
   `MODEL_PATH = models/best_fuzzyarcloss_v2.pth` and the public CTransPath weights writes, for each
   TCGA-LUAD slide, `embeddings.npy` (`[n_tiles, 512]`) and `pattern_probs.npy` (`[n_tiles, 6]`).
   Labels come from the GDC MAF via `download_tcga_luad_maf.py` → `crossref_slides_vs_luad_maf.py`
   (`data/cohort/labels.csv`).
3. **Artefacts 2/3 benchmark**:

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
