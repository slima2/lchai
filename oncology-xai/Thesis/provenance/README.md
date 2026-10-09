# Provenance notes

Audit trail for the files in this archive. Nothing here is needed to run or
reproduce the thesis; it exists so that a reviewer comparing the archived
logs with the original DGX outputs understands the differences.

## 1. Class names in the archived results were renamed after the runs

The ANORAK overlay index used to train the pattern classifier carried a
permuted set of class names. A histopathologist re-verified the six classes
against the official Zenodo ANORAK documentation on 4 April 2026; the
corrected index is `training/data_preparation/overlay_index.xlsx` and the
builder is `training/data_preparation/build_anorak_overlay_index.py`.

The trained models, their six output indices and every numeric result are
unaffected; only the *name* attached to each index was wrong. The fixed index
order of all checkpoints (`best_fuzzyarcloss_v2.pth`, the 150 ABMIL/Choquet
checkpoints, every `pattern_probs.npy`, every `prob_*` column) is therefore the
alphabetical order of the old names, not of the correct ones:

| model index | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| **class** | micropapillary | cribriform | papillary | lepidic | solid | acinar |
| name used in files written before the correction | acinar | lepidic | micropapillary | mucinous | papillary | solid |

Consequences visible in the archive:

* Every log, JSON, CSV, script and notebook under `Thesis/` was rewritten with
  the single simultaneous permutation above (`remap_pattern_names_4apr2026.py`
  for results, `remap_pattern_names_in_scripts.py` for code; mapping table in
  `PATTERN_REMAP_4_apr_2026.py`). Numeric values were not touched.
  `remap_manifest_dgx.json` lists every DGX file rewritten, with checksums.
* The Artefact 1 scripts sort labels with the `CLASS_ORDER` constant instead of
  `sorted()`, so that `label2id` stays identical to the original runs and the
  positional per-class parameters of FuzzyArcLoss keep their meaning.
* `models/best_fuzzyarcloss_v2.pth` is the DGX checkpoint
  `outputs/ablation_study_v16_optuna/best_fuzzyarcloss_v2.pth` (24 Feb 2026,
  sha256 `e2b2c99b…`) with only `id2label`/`label2id` rewritten; the tensors
  are byte-identical (193 tensors checked with `torch.equal`). The checkpoint
  keeps the old map under `id2label_legacy_pre_4apr2026` and a `provenance` key.
* The gene→pattern literature priors in `figures/generate_attention_maps.py`
  and `figures/visualize_attention_patterns.py` are biology, not labels, so
  they were restored by hand after the mechanical remap.
* Pre-correction copies of everything are kept on the DGX under
  `notebooks/slima/backups/` (`thesis_scripts_pre_pattern_remap_9oct2026.tar.gz`,
  `inference_results_parallel_pre_remap_9oct2026.tar.gz`,
  `inference_pipeline_6gpu_pre_remap_9oct2026.tar.gz`,
  `backups_pre_pattern_fix_4apr2026/`). Git history before commit `c42ab8f`
  also contains the dated file names and the per-file markers.

Consistency check: with the corrected names,
`per_fold_json/metrics_proposed_fuzzy_choquet_KRAS_fold3.json` gives
`lepidic×solid = +0.0321` and `solid×acinar = +0.0254`, i.e. the first two rows
of Table 6.12; RBM10 rows correspond to fold 4.

## 2. What produced the Chapter 6 numbers

* Script `training/artefact2_mutation_abmil/pattern_informed_abmil_benchmark_v2_patched.py`
  (14 Mar 2026; orchestrator log
  `logs/mutation_5fold_results/orchestrator_output_benchmark_v2_patched.txt`).
  Earlier Feb-2026 versions produced different, superseded result sets and were
  removed from the repository (git history up to `d7543a2` still has them).
* Cohort: `--slide_list data/cohort/luad_slide_ids_available.txt` →
  505 slides from 505 patients (train 404 / test 101 per fold).
  `data/cohort/labels.csv` is the full 687-slide / 668-patient label matrix; of
  the 182 unused slides, 170 carry all-zero labels (patient absent from the MAF).
  Observed prevalence in the 505: TP53 50.3 %, KRAS 27.3 %, KEAP1 18.2 %,
  EGFR 14.7 %, STK11 13.3 %, RBM10 6.9 %.
* Model selection: `_abmil_loop()` evaluates AUROC after every epoch on the CV
  **test** fold, keeps the best epoch (patience 15) and reports that value.
  There is no inner validation split, so the fold AUROCs are
  best-epoch-on-test-fold values and optimistically biased; thesis §5.8.2
  ("10 % of the training fold") should be read accordingly.
* Per-slide predictions: `_save_fold()` strips `probs`/`labels` before writing
  the JSON, so no per-fold prediction CSV exists; they can be regenerated from
  the 150 checkpoints (Zenodo deposit). The XGBoost models were not persisted.
* Artefact 1: `output_kfold_fuzzyv2_sphereface.txt` line
  "FuzzyArcLoss V2 (Optuna) 92.31 % ± 2.05" is the source of the 92.31 % figure
  (thesis prints ± 2.04).

## 3. Scripts kept vs. removed (9 Oct 2026)

Rule: for every result in the thesis, the one script version that produced the
archived log / CSV / JSON, plus the data-preparation scripts on its path.

| Removed (still in git history ≤ `9d1284c`) | Why |
|---|---|
| ablation `ver_11_jan_2026`, `ver_12_feb_2026_rev5` | pre-audit versions (150 epochs); superseded by `…_rev_13`, whose log is the archived Table 6.1 run |
| `ablation_v2_5`, `ablation_v3 improved`, `complete_ablation_multigpu`, `fuzzy_arc_loss_v2` (Jan 2026) | exploratory variants contained in the rev-13 ablation; the loss module was never imported |
| `advanced_benchmark_v3 FSL` | few-shot / meta-learning benchmark, not in the thesis |
| `improved_pathology_backbone_90_target` (27 Dec 2025) | its model is not used by anything archived (the Dec-2025 TCGA inference used the ROI model `anorak_roi_acc6_v5`) |
| ABMIL benchmark `.py`, `_paralell.py`, `ver 27 feb 2026`, `_v2.py`, stand-alone `FuzzyChoquetAggregation.py` | Feb-28 LUAD+LUSC / 768-d versions; `_v2.py` differs from `_v2_patched.py` only by not saving checkpoints |
| XGBoost `v2_feb_2026 ver 24 feb 2026` | earlier revision of `rev 4` |
| `run_all_downloads.sh` | CPTAC-3 / APOLLO / EAGLE downloads through scripts never written; cohorts explicitly not used (thesis Table 3.10) |
| notebook `xgboost ver 25 nov 2025`, Nov-2025 summary CSVs | superseded by the 1 Feb 2026 notebook and the Dec-2025 322-slide summaries |
| `oncology-xai/scripts/*` thesis copies (22 files) | identical to files in `Thesis/` or the same superseded versions |

Known gap: the "71–76 % before the twenty fixes" figure of thesis §3.7 / §6.1.1
has no archived script + log pair; the only pre-audit log on the DGX
(`output_ablation_allfuzzy_allothers.txt`) used a 775-tile split and is
truncated after 3 of 18 losses.

## 4. Known discrepancies between the thesis text (PDF of 3 May 2026) and the archive

The archive is the record of what was actually run. Where the printed text
differs, the archived value is the one that can be reproduced.

| Thesis | Says | Archive |
|---|---|---|
| Figure 6.5 caption | validation set N = 138 tiles | `logs/pattern_classifier_results/eval_results_val_set.json`: N = 128 tiles (80/20 split of 637, seed 42). No 138-tile evaluation exists on the DGX. |
| §5.8 cohort of the mutation benchmark | 687 slides / 668 patients, ≈549 train / 138 test per fold | `results_luad_full_v2` was run with `--slide_list luad_slide_ids_available.txt`: 505 slides / 505 patients, 404 / 101 per fold. `labels.csv` still lists the full 687-slide inventory. |
| §5.8.2 model selection | "10 % of the training fold" used for early stopping | `_abmil_loop()` selects the best epoch on the CV **test** fold (patience 15) and reports that value; there is no inner split. Fold AUROCs are therefore best-epoch-on-test values (optimistic). |
| §5.8.3 per-slide predictions | per-fold prediction files | `_save_fold()` drops `probs`/`labels` before writing the JSON; no per-slide prediction CSV exists. Regenerable from the 150 checkpoints (Zenodo). XGBoost models were not persisted. |
| Figure 6.10 (AUPRC per gene) | values typed by hand, 2 decimals | 32 of 36 cells differ from `summary_table.csv` (largest: FC-MIL/TP53 printed .63 vs .706; B2/TP53 .64 vs .695; B1/EGFR .31 vs .235). Figures 6.6–6.9 (AUROC) match the CSV exactly. |
| §6.1 FuzzyArcLoss V2 K-fold result | 92.31 % ± 2.04 | `output_kfold_fuzzyv2_sphereface.txt`: 92.31 % ± 2.05 |
| §3.7 / §6.1.1 pre-audit baseline | 71–76 % macro-F1 before the twenty fixes | no archived script + log pair (see §3 above) |
| §5.3.6 embedding storage | embeddings stored as float16 (~20 GB) | `embeddings.npy` are float32 (38.6 GB); `pattern_probs.npy` float32 as stated |
| Reproducibility statement | — | Zenodo DOI pending; `docs/zenodo_deposit/MANIFEST_sha256.txt` lists the deposit |

## 5. Material in the archive that the thesis does not use

`logs/tcga_tile_inference_dec2025/` (322 TCGA slides), the notebook
`inference/SLIMA_histology_mutation_xgboost_rev3_… 1 feb 2026.ipynb`, the
notebook `SLIMA Mapping MAF to CSV … 17 dec 2025.ipynb` and the script
`SLIMA_PARALELL_inferencing_hist_patterns_roi_parallel_ver_14_dec_2025.py` are
the Nov–Dec 2025 development line of the XGBoost baseline: an earlier ROI
pattern model (`anorak_roi_acc6_v5`, not FuzzyArcLoss V2) was run on the 322
TCGA slides available at the time, slide-level pattern percentages were joined
to the MAF, and XGBoost + TreeSHAP were explored per gene. None of its numbers
appear in the thesis: condition B1 of Chapter 6 is computed inside
`pattern_informed_abmil_benchmark_v2_patched.py` on the 505-slide cohort, and
the SHAP attributions of Figure 4.12 / Table 6.10 come from the LCHAI
inference service, not from these notebooks.
