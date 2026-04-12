# Thesis Reproducibility Archive

All scripts, logs, and results required to reproduce the experiments in the doctoral thesis:

**"Fuzzy Logic-Enhanced Computational Pathology for Lung Adenocarcinoma Mutation Prediction: Pattern-Informed Attention and Choquet Aggregation"**

## Directory Structure

```
Thesis/
├── training/
│   ├── artefact1_pattern_classifier/    # FuzzyArcLoss V2 on Zenodo-ANORAK (6 patterns)
│   │   ├── logs/                        # Training logs (18 loss functions benchmark)
│   │   └── *.py                         # Training scripts (Optuna, ablation, K-fold)
│   ├── artefact2_mutation_abmil/        # PI-ABMIL: 5-fold CV mutation prediction
│   │   └── *.py                         # Benchmark runner (6 conditions × 6 genes × 5 folds)
│   ├── artefact3_mutation_choquet/       # FC-MIL: Fuzzy Choquet MIL training
│   │   └── *.py                         # Choquet-specific benchmark script
│   ├── xgboost_baseline/                # B1: XGBoost on slide-level pattern features
│   │   └── *.py                         # XGBoost mutation prediction scripts
│   └── data_preparation/                # Embedding extraction, tiling, label correction
│       ├── download_gdc_svs.py          # TCGA-LUAD SVS download from GDC
│       ├── extract_embeddings.py        # CTransPath 512-d embedding extraction
│       ├── prepare_benchmark_inputs.py  # Tile embeddings + pattern probs → benchmark input
│       ├── mutation_report.py           # MAF → per-slide binary mutation labels
│       └── SLIMA Zenodo overlay CORRECTED 4 apr 2026.py  # Fix ANORAK class mapping
│
├── inference/
│   └── *.ipynb                          # XGBoost inference notebooks (legacy)
│
├── logs/
│   ├── mutation_5fold_results/
│   │   ├── summary_table.csv            # All 36 (condition,gene) AUROC/AUPRC/F1 means
│   │   ├── per_fold_json/               # 180 JSON files (6 cond × 6 genes × 5 folds)
│   │   │   └── metrics_<cond>_<gene>_fold<k>.json
│   │   └── worker_logs/                 # Per-gene training logs from H100 GPUs
│   │       └── worker_<gene>.txt
│   └── pattern_classifier_results/
│       ├── eval_results.json            # Full-dataset evaluation (N=637)
│       └── eval_results_val_set.json    # Validation-set evaluation (N=128, 80/20 split)
│
├── evaluation/
│   ├── eval_pattern_confusion.py        # Generate confusion matrix from FuzzyArcLoss V2
│   ├── verify_fold_aurocs.py            # Verify Table 6.12 best-fold values from JSONs
│   ├── extract_fold_aurocs.py           # Extract per-fold AUROCs from checkpoints
│   └── find_high_prob_slides.py         # Identify high-P(mut) slides for case studies
│
├── figures/
│   ├── gen_auroc_bar_chart.py           # Figure 6.2: AUROC per gene (6 conditions)
│   ├── gen_auroc_heatmap.py             # Figure 6.3: AUROC heatmap (condition × gene)
│   ├── gen_auroc_difference.py          # Figure 6.4: Delta AUROC vs B2
│   ├── gen_auroc_radar.py               # Figure 6.5: Radar plot (4 conditions)
│   ├── gen_auprc_bar_chart.py           # Figure 6.6: AUPRC per gene
│   ├── gen_ablation_flowchart.py        # Ablation causal chain diagram
│   ├── gen_choquet_plots.py             # Choquet Shapley/interaction bar charts
│   ├── gen_fuzzy_mf_plots.py            # Fuzzy membership function plots (5 scales)
│   ├── gen_shap_ablation_quadrant.py    # SHAP attribution vs ablation utility quadrant
│   ├── gen_tile_filtering_pipeline.py   # Tile filtering pipeline flowchart
│   ├── gen_visual_summary.py            # Thesis visual summary (RQ → chapter mapping)
│   ├── gen_active_learning_diagrams.py  # Active learning workflow diagrams
│   └── gen_questionnaire_docx.py        # Expert questionnaire DOCX generator
│
└── README.md                            # This file
```

## Key Results Files

### `logs/mutation_5fold_results/summary_table.csv`
Master table with all 36 (condition, gene) results. Columns: `condition, gene, n_folds, auroc_mean, auroc_std, auprc_mean, auprc_std, f1_mean, f1_std`. This file backs Tables 6.5, 6.6, 6.7, and 6.8 in the thesis.

### `logs/mutation_5fold_results/per_fold_json/`
180 individual JSON files, one per (condition, gene, fold). Each contains the test-fold AUROC. These back Table 6.12 (best fold AUROC) and the statistical tests in Finding 1.

### `logs/pattern_classifier_results/`
Evaluation of FuzzyArcLoss V2 on ANORAK tiles. `eval_results_val_set.json` backs the confusion matrix (Figure 6.1, N=128 val set).

## Computational Environment

- **Pattern classifier training**: 6× NVIDIA H100 80GB HBM3, CUDA 12.x, PyTorch 2.x
- **Mutation prediction 5-fold CV**: 6× NVIDIA H100 (one gene per GPU), ~15-16 hours total
- **Inference service**: Docker container with CTransPath + FuzzyArcLoss V2 checkpoint

## Reproducing the Figures

All figure generators in `figures/` are standalone Python scripts using matplotlib. Run:
```bash
python Thesis/figures/gen_auroc_bar_chart.py
```
Output paths are hardcoded to the thesis figures directory.

## Condition Naming Convention

| Code | Name | Description |
|------|------|-------------|
| B1 | XGBoost | Slide-level pattern features → XGBoost |
| B2 | ABMIL-emb | CTransPath 512-d embeddings → ABMIL |
| B3 | ABMIL-pat | Pattern probabilities 6-d → ABMIL |
| PI-ABMIL | PI-ABMIL (ours) | Embeddings + patterns 518-d → ABMIL |
| A | Ablation one-hot | Embeddings + one-hot 518-d → ABMIL |
| FC-MIL | FC-MIL (ours) | Dual-pathway: ABMIL + Choquet integral |
