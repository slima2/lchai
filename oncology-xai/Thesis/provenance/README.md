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
  the single simultaneous permutation above (`remap_pattern_names_in_results.py`
  for results, `remap_pattern_names_in_scripts.py` for code; mapping table in
  `pattern_index_mapping.py`). Numeric values were not touched.
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

* Script `training/artefact2_mutation_abmil/pattern_informed_mil_benchmark.py`
  (14 Mar 2026; orchestrator log
  `logs/mutation_5fold_results/orchestrator_output_benchmark.txt`).
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
* Artefact 1: `output_kfold_statistical_validation.txt` line
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

## 4. Discrepancies between the thesis text (PDF of 3 May 2026) and the archive

### Why they exist

Chapters 5 and 6 were drafted between February and March 2026 from the
experimental *design* and from intermediate runs. Two things happened after
much of that text was written: the final benchmark run of 14 March 2026
(`results_luad_full_v2`, the one archived here) and the class-name audit of
4 April 2026 (§1). The AUROC tables and figures (Table 6.5, Figures 6.6–6.9,
Table 6.9) were regenerated from the final run and match the archive exactly;
some prose, captions and one hand-typed figure were not re-synchronised.

Policy of this archive: it is the record of what was executed. No archived
number was edited to agree with the text. Where the two differ, the archived
value is the reproducible one and the text should be read as described below.

### Itemised

**D1 — Figure 6.5 caption: N = 138 tiles.** The confusion matrix shown is
`logs/pattern_classifier_results/confusion_matrix_val_set.png`, computed from
`eval_results_val_set.json` on 128 tiles (20 % of 637 with `seed 42`). No
138-tile evaluation exists. The number 138 is the test-fold size of the
687-slide design cohort (687 × 0.2 ≈ 138, see D2), which was most likely
carried into the caption by mistake. Only the caption is affected; the matrix
and the per-class figures are those of the 128-tile evaluation.

**D2 — §5.8 cohort: 687 slides / 668 patients, ≈ 549 / 138 per fold; gene
prevalences in Figure 6.10 (RBM10 5.4 %, STK11 9.9 %).** These describe the
designed cohort — the complete inventory in `data/cohort/labels.csv` (687
rows). The benchmark was executed with `--slide_list luad_slide_ids_available.txt`,
i.e. the 505 LUAD slides (one per patient) that had both a downloadable SVS
and a patient present in the GDC MAF; 51 LUAD cases had no downloadable slide
(`luad_cases_missing_slides.txt`) and 170 of the excluded 182 slides carry
all-zero labels because the patient is absent from the MAF. Fold sizes are
404 / 101 and the observed prevalences are TP53 50.3 %, KRAS 27.3 %,
KEAP1 18.2 %, EGFR 14.7 %, STK11 13.3 %, RBM10 6.9 %. The 687-based
prevalences in the text are therefore *diluted* by slides that could never be
positive. Impact: every Chapter 6 metric is a 505-slide result; the ranking
of conditions is unaffected because all six conditions share the same folds.
Readers should substitute 505 / 404 / 101 and the prevalences above.

**D3 — §5.8.2 early stopping on "10 % of the training fold".** This is the
intended protocol; the executed code (`_abmil_loop()` in
`pattern_informed_mil_benchmark.py`) evaluates on the CV test fold after
every epoch, keeps the best epoch (patience 15) and reports that epoch's
metrics. There is no inner validation split. The fold AUROCs of the five MIL
conditions are therefore best-epoch-on-test values and optimistically biased;
Table 6.9 ("best fold") is additionally a maximum over folds. The bias is the
same for the five MIL conditions, so comparisons *among* them remain
internally consistent, but the comparison against B1 (XGBoost, which is fit
once on the training fold and evaluated once on the test fold) is tilted in
favour of the MIL conditions. This is the most consequential discrepancy of
the list and the one a reader should weigh when interpreting the absolute
AUROC values. Re-running the benchmark with an inner validation split would
be the first step of any follow-up work.

**D4 — §5.8.3 per-slide prediction files.** `_save_fold()` removes `probs`
and `labels` before writing each `metrics_*.json`, so the archive has fold-level
metrics but no per-slide predictions. They can be regenerated from the 150
checkpoints in the Zenodo deposit; the XGBoost models (B1) were not persisted
and would need to be retrained (deterministic, `random_state` fixed).

**D5 — Figure 6.10 (AUPRC per gene).** The printed figure was produced by an
earlier version of `figures/gen_auprc_bar_chart.py` whose values were typed by
hand, rounded to two decimals, from an intermediate run. 32 of the 36 cells
differ from `summary_table.csv` (mean |Δ| = 0.031; nine cells differ by more
than 0.05, the largest being FC-MIL/TP53 0.63 vs 0.706 and B1/EGFR 0.31 vs
0.235). For TP53, KRAS and STK11 the condition with the highest AUPRC also
changes (printed: B2, B2, PI-ABMIL; archive: FC-MIL, FC-MIL, one-hot
ablation). The AUPRC-based remarks in §6 (the "AUROC–AUPRC gap" paragraph and
Figure 6.11) inherit these values. AUPRC is a secondary metric in the thesis;
the primary conclusions rest on AUROC (Table 6.5, Figures 6.6–6.9), which
match the archive. The current `gen_auprc_bar_chart.py` reads the CSV and
produces the corrected figure.

**D6 — §6.1 K-fold result 92.31 % ± 2.04.** The archived log
(`output_kfold_statistical_validation.txt`) prints 92.31 % ± 2.05 for
FuzzyArcLoss V2 (15 runs: 5 folds × 3 seeds). The 0.01 difference is a
rounding of the same standard deviation; the mean, the 95 % CI [91.2, 93.4]
and the paired t-test against SphereFace (p = 0.0011) are as printed.

**D7 — §3.7 / §6.1.1 "71–76 % macro-F1 before the twenty fixes".** The
twenty fixes were applied incrementally between January and February 2026 on
development versions of the ablation script whose logs were overwritten. The
only surviving pre-audit log on the DGX (`output_ablation_allfuzzy_allothers.txt`)
used a 775-tile split and stops after 3 of 18 losses. The figure is from the
author's working notes and cannot be reproduced from the archive; it should
be read as historical context, not as a result.

**D8 — §5.3.6 embeddings "stored as float16 (~20 GB)".** The pipeline
(`pipeline_6gpu_parallel.py`) writes `embeddings.npy` in float32 (38.6 GB
for 687 slides); `pattern_probs.npy` is float32 as stated. The text reflects
the planned storage format. No result depends on it; the float32 files are
the ones hashed in `docs/zenodo_deposit/embeddings_sha256_manifest_REGENERABLE_not_deposited.txt`.

**D9 — Reproducibility statement.** The DOI of the Zenodo deposit was not
available at printing time. The deposit content is fixed by
`docs/zenodo_deposit/MANIFEST_sha256.txt`.

**D10 — §4.4.2 / §4.4.4 / §5.5: FC-MIL fuzzy measure and Choquet integral as
executed.** The text describes a normalised, monotone 2-additive capacity over
the six patterns (softmax Shapley weights, Eq. 4.25; L1 on the interactions,
Eq. 4.26; monotonicity penalty, Eq. 5.2) whose Choquet integral sorts the six
values of a slide-level membership vector. The executed module
(`FuzzyMeasure`, `FuzzyChoquetAggregation` in `pattern_informed_mil_benchmark.py`)
is, exactly:

* a 2-additive set function in Möbius form, `g(S) = σ( Σ_k m_k s_k + Σ_{j<k} m_jk s_j s_k )`
  with singleton masses `m_k = sigmoid(v_k)` and 15 pair masses `m_jk = triu(v2, 1)`,
  evaluated on *soft* subsets `s` (multilinear extension) and squashed by an
  outer sigmoid — 6 + 15 parameters as stated;
* the discrete Choquet integral **over the N tiles**, one per pattern k: tiles
  are ranked by their membership `p_k`, the set function is evaluated on the mean
  pattern composition of the nested top-i sets `U_i`, and the sum is written in
  summation-by-parts form. `evaluation/check_fuzzy_measure.py` verifies the
  identity `code_k = x_(1) g(U_1) + x_(N) g(U_N) − C_g(x_k) + Σ_i Δx_i Δg_i`
  (max error 1.5e-7), where `C_g(x_k) = Σ_i (x_(i) − x_(i+1)) g(U_i)` is the Choquet
  integral; the sign and the boundary term are absorbed by `choquet_scale` and
  the linear merge, so the model family is the Choquet one;
* trained with BCE only: no L1 term and no monotonicity penalty exist in
  `train_one_epoch`.

Consequences. (i) Because the pair masses of a 2-additive function equal its
Shapley interaction indices (Grabisch 1997), the `fuzzy_interactions` values of
Table 6.12 (`m_jk`) are the interaction indices the text interprets; their sign
(synergy / redundancy) and ranking are unaffected by the outer sigmoid.
(ii) The JSON key `fuzzy_shapley_values` stores the singleton Möbius masses
`m_k = sigmoid(v_k)` (≈ 0.54), not Shapley values; `φ_k = m_k + ½ Σ_j m_jk`
(script above) is nearly uniform (0.162–0.174 after normalisation for KRAS),
i.e. the discriminative content of the measure is in the interactions.
(iii) Normalisation (`g(∅) = 0`, `g(N) = 1`) is not enforced; a Choquet integral
is invariant to it up to the affine terms absorbed downstream. (iv) Monotonicity
was not enforced but holds a posteriori for all 30 archived FC-MIL folds
(`m_k − Σ_j max(0, −m_jk) ≥ 0.444` for every pattern), so the missing penalty
had no effect on the archived checkpoints. (v) The integral acts over tiles,
not over a slide-level 6-vector: the co-presence term `m_jk s_j s_k` is evaluated
on the composition of the top-ranked tile sets, which is where inter-pattern
co-occurrence is observable.

Control experiment (9 Oct 2026, DGX `fuzzy_choquet_2additive/`, not part of the
thesis). A theory-faithful module — normalised monotone 2-additive capacity
over the six patterns, Shapley/Möbius exact, Choquet integral of the
slide-level membership vector — was trained on the same 505 slides and folds
with an inner 15 % validation split (not test-fold selection, cf. D3).
Mean AUROC: Choquet-only heads 0.46–0.59 (≈ B1 XGBoost, 0.47–0.63), hybrid with
the attention embedding 0.48–0.66 (≤ B2); learned interaction indices ≤ 0.002,
i.e. the slide-level capacity is essentially additive. A monotone scalar
function of the six slide-level fractions cannot carry more information than
B1, so this is the expected outcome and supports the mechanism-bound reading of
C5: the FC-MIL gain on KRAS originates in the tile-level sorting and
co-presence term, not in the normalisation of the capacity.

Like-for-like repeat (same day, `run_luad_choquet.py --select_on_test`, i.e.
the epoch-selection protocol of Table 6.5 / D3). Mean AUROC
(TP53 / EGFR / KRAS / STK11 / KEAP1 / RBM10):
Choquet on mean memberships 0.568 / 0.569 / 0.541 / 0.533 / 0.572 / 0.532;
Choquet on attention-weighted memberships 0.700 / 0.632 / 0.567 / 0.621 / 0.567 / 0.588;
hybrid (attention embedding + Choquet scalar) 0.711 / 0.691 / 0.576 / 0.665 / 0.575 / 0.622.
Reference under the same protocol: B2 0.718 / 0.701 / 0.607 / 0.684 / 0.597 / 0.642,
FC-MIL 0.716 / 0.684 / 0.609 / 0.658 / 0.589 / 0.661. Test-fold selection
inflates the control by 0.02–0.11 (the size of the D3 effect), but the ordering
is unchanged: the pure slide-level Choquet stays at B1 level, and the hybrid
remains below B2 and FC-MIL on every gene, including KRAS (0.576 vs 0.609).
Learned interaction indices stay ≤ 0.010 (≤ 0.0025 for the mean-membership
head): the slide-level capacity is additive under either protocol.

**D11 — Eq. 4.17 encoder depth.** Eq. 4.17 writes a two-layer feed-forward
encoder; the executed `ABMIL.encoder` is a single `Linear(input_dim, 256)` +
LayerNorm + ReLU + Dropout, as Table 5.6 (131,840 parameters) correctly
states.

## 5. Development material removed from the archive

The Nov–Dec 2025 development line of the XGBoost baseline was removed from
the repository because none of its numbers appear in the thesis and its
322-slide cohort is not one of the cohorts the thesis describes:

- `logs/tcga_tile_inference_dec2025/` — tile predictions and per-slide / per-case
  pattern percentages for the 322 TCGA slides available on 14 Dec 2025, produced
  by an earlier ROI pattern model (`anorak_roi_acc6_v5`, not FuzzyArcLoss V2)
  with `SLIMA_PARALELL_inferencing_hist_patterns_roi_parallel_ver_14_dec_2025.py`;
- `SLIMA Mapping MAF to CSV per tile wsi classification TGCA ver 17 dec 2025.ipynb`
  (join of those percentages to the GDC MAF) and `mutation_report.py`
  (local report over the same CSV);
- `inference/SLIMA_histology_mutation_xgboost_rev3_… ver 1 feb 2026.ipynb`
  (XGBoost + TreeSHAP exploration per gene on those profiles).

Condition B1 of Chapter 6 is computed inside
`pattern_informed_mil_benchmark.py` on the 505-slide cohort from
`pattern_probs.npy` of the final model, and the SHAP attributions of
Figure 4.12 / Table 6.10 come from the LCHAI inference service, not from these
notebooks. The files remain on the DGX under
`outputs/inference_results_parallel/` and in git history before commit
`91dea5f`.

## 6. File names

Scripts and logs were renamed on 9 Oct 2026 so that the name states what the
file does rather than when it was written. The old names still appear inside
the archived logs (command lines, `Loading ablation code from: …`) and in
`remap_manifest_dgx.json`; this table maps them.

| Old name (as printed in logs / on the DGX) | Archived as |
|---|---|
| `SLIMA_ablation_study_loss_functions_ver_23_feb_2026_gpu_rev_13.py` | `training/artefact1_pattern_classifier/ablation_loss_functions.py` |
| `SLIMA_optuna_fuzzyarcloss_v2_best model search_ 22 feb_2026 rev 2.py` | `training/artefact1_pattern_classifier/optuna_fuzzyarcloss_search.py` |
| `SLIMA_kfold_statistical_validation_23 feb_2026 rev 13.py` | `training/artefact1_pattern_classifier/kfold_statistical_validation.py` (now loads `ablation_loss_functions.py` from its own directory instead of the DGX path) |
| `pattern_informed_abmil_benchmark_v2_patched.py` | `training/artefact2_mutation_abmil/pattern_informed_mil_benchmark.py` |
| `SLIMA_PARALLEL_inferencing_hist_patterns_ver_24_feb_2026_gpu_optimized.py` | `training/data_preparation/tile_pattern_inference_multigpu.py` |
| `extract_embeddings (2).py`, `prepare_benchmark_inputs (1).py` | `training/data_preparation/extract_embeddings.py`, `prepare_benchmark_inputs.py` |
| `SLIMA_aggregation_xgboost_mutation_prediction_v24_feb_2026  rev 4 (1).py` | `training/xgboost_baseline/xgboost_mutation_from_pattern_profiles.py` |
| `output_ablation_best_rev13.txt` | `logs/pattern_classifier_results/output_ablation_loss_functions.txt` |
| `output_optuna_fuzzyarcv2_best.txt` | `logs/pattern_classifier_results/output_optuna_fuzzyarcloss_search.txt` |
| `output_kfold_fuzzyv2_sphereface.txt` | `logs/pattern_classifier_results/output_kfold_statistical_validation.txt` |
| `ablation_results_v16_optuna.json` | `logs/pattern_classifier_results/ablation_results.json` |
| `orchestrator_output_benchmark_v2_patched.txt` | `logs/mutation_5fold_results/orchestrator_output_benchmark.txt` |
| `output_pipeline_6gpu_r2.txt`, `_r3.txt` | `logs/data_pipeline/output_pipeline_6gpu_run2.txt`, `_run3.txt` (resumed runs of the same pipeline) |
| `output_tcga_luad_download_ver1.txt` | `logs/data_pipeline/output_tcga_luad_maf_download.txt` |
| `PATTERN_REMAP_4_apr_2026.py`, `remap_pattern_names_4apr2026.py` | `provenance/pattern_index_mapping.py`, `provenance/remap_pattern_names_in_results.py` |

DGX directory names quoted in scripts and logs (`outputs/ablation_study_v16_optuna/`,
`results_luad_full_v2/`) and the checkpoint key `id2label_legacy_pre_4apr2026`
are left as they are: they identify real locations and keys on the machine.
`best_fuzzyarcloss_v2.pth` keeps its name because "FuzzyArcLoss V2" is the
name of the loss in the thesis, not a file revision.
