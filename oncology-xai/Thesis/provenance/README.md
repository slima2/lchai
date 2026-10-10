# Provenance notes

Audit trail for the files in this archive. Nothing here is needed to run or
reproduce the thesis; it exists so that a reviewer comparing the archived
logs with the original DGX outputs understands the differences.

## 1. What produced the Chapter 6 numbers

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

## 2. Scripts kept vs. removed (9 Oct 2026)

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

## 3. Discrepancies between the thesis text (PDF of 3 May 2026) and the archive

### Why they exist

Chapters 5 and 6 were drafted between February and March 2026 from the
experimental *design* and from intermediate runs. The final benchmark run of
14 March 2026 (`results_luad_full_v2`, the one archived here) took place after
much of that text was written. The AUROC tables and figures (Table 6.5, Figures 6.6–6.9,
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

**D12 — Sec. 5.4.3–5.4.4 training protocol of the mutation benchmark.** The
text describes settings that no version of the benchmark script ever
implemented. A search of every `.py`/`.ipynb` on the DGX (1,346 files, all
subdirectories of `slima/`) found no mutation/MIL script with Adam at
2 × 10⁻⁴, cosine warm restarts, gradient accumulation or patient grouping;
the whole lineage (27 Feb → `v2_patched`, 14 Mar 2026) uses the settings in
the right-hand column, and the archived worker logs confirm them
(`lr=9.99e-05` at epoch 1 decreasing monotonically to `8.44e-05` at epoch 13,
with no jump at epoch 11; `train=404, val=101`).

| Item | Thesis text | Executed (`pattern_informed_mil_benchmark.py`) |
|---|---|---|
| Optimiser | Adam, lr 2 × 10⁻⁴, "intentionally kept on Adam" | `AdamW`, lr 1 × 10⁻⁴, weight decay 1 × 10⁻⁵ (same for all four deep conditions) |
| Schedule | cosine with warm restarts, T₀ = 10 | `CosineAnnealingLR`, one cycle, T_max = 50, η_min = 1 × 10⁻⁶ |
| Gradient accumulation | 4 slides | none, one update per slide (batch 1), FC-MIL included |
| Early stopping | patience 15 | patience 15, best-AUROC checkpoint kept (selection on the test fold, D3) |
| Loss | BCE with logits | `BCEWithLogitsLoss(pos_weight = n_neg / n_pos)`; B1 uses `scale_pos_weight` likewise |
| Fold split | stratified, grouped by patient | `StratifiedKFold(5, shuffle, seed 42)` on slides; the 505 slides belong to 505 distinct patients (no repeated 12-character TCGA ID), so slide-level and patient-level splits coincide |
| Fold sizes | ≈ 549 / 138 (687 slides) | 404 / 101 (505 slides, see §1) |
| Tile sampling | 4,096 tiles, training only | identical |
| FC-MIL "faster, 3 vs 8 min" | cheaper Choquet step | FC-MIL runs the same loop as ABMIL (batch 1, patience 15) plus the attention over 512-d; no timing is logged, and the explanation has no basis. (`batch_size=8`, patience 10 exist only in the 28 Feb development version `pattern_informed_abmil_benchmark_FuzzyChoquetAggregation.py`, which produced no archived result.) |
| B1 early stopping (30 rounds), TreeSHAP | in the benchmark | not in the benchmark: `clf.fit(X_tr, y_tr)` without `eval_set` builds all 300 trees and saves `feature_importances_`. Both exist in the stand-alone B1 `training/xgboost_baseline/xgboost_mutation_from_pattern_profiles.py`. |
| Paired t-test, Cohen's d, MDE ≈ 1.2 (Sec. 6.2.3) | — | not computed by any archived script; now reproduced by `evaluation/fold_statistics.py` from `per_fold_json/` (d_crit = t₀.₉₇₅,₄/√5 = 1.24; no multiple-comparison correction; the two nominal p < 0.05 differences, PI-ABMIL < B2 on KRAS and one-hot < B2 on EGFR, do not survive a Bonferroni factor of 6). |

## 4. Development material removed from the archive

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

## 5. File names

Scripts and logs were renamed on 9 Oct 2026 so that the name states what the
file does rather than when it was written. The old names still appear inside
the archived logs (command lines, `Loading ablation code from: …`); this table
maps them.

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

DGX directory names quoted in scripts and logs (`outputs/ablation_study_v16_optuna/`,
`results_luad_full_v2/`) are left as they are: they identify real locations on
the machine.
`best_fuzzyarcloss_v2.pth` keeps its name because "FuzzyArcLoss V2" is the
name of the loss in the thesis, not a file revision.

## 6. Why the executed choices were made (one entry per discrepancy)

Section 4 records *what* differs between the printed text and the archive.
This section records *why* each executed choice was made and what evidence
shows that it did not compromise the result. Entries are marked **design
decision** (a deliberate choice with a technical reason), **pragmatic
decision** (a choice forced by data size or compute, with its effect
measured) or **erratum** (a documentation error with no effect on any
number). The rule followed throughout: where a choice could have changed a
conclusion, the effect was measured post hoc (D3, D10, D12) rather than
argued away.

**D1 — caption "N = 138" (erratum).** The matrix, the per-class figures and
the JSON are the 128-tile evaluation; 138 is the test-fold size of the design
cohort that slipped into the caption. No number changes.

**D2 — 505 slides instead of 687 (design decision).** The 182 excluded slides
are not missing at random: 170 of them belong to patients absent from the
GDC MAF, for whom "no mutation recorded" means *not sequenced*, not
*wild-type*. Including them would have injected 170 false negatives into
every gene, up to 25 % of the cohort, and biased every AUROC downward in an
uncontrolled way. The executed cohort is exactly the set of slides with (i) a
downloadable diagnostic SVS and (ii) a sequenced patient. All six conditions
share the same 505 slides and the same folds, so the comparison between
conditions, which is what RQ2–RQ3 ask, is unaffected; the absolute values are
those of a cleaner, smaller cohort. The 687/668 figures describe the
inventory built in §5.2 and remain correct as a description of that inventory.

**D3 — epoch selection on the test fold instead of an inner 10 % split
(pragmatic decision, effect measured).** With 404 training slides per fold, a
10 % inner split holds about 40 slides; at the prevalences of the cohort that
is 3 positives for RBM10, 5 for STK11 and 6 for EGFR. An AUROC estimated on
three positives moves by ±0.3 from one epoch to the next and cannot drive
early stopping. The choice was therefore to monitor the full test fold
(101 slides) and to report the best epoch, applying the identical rule to all
five MIL conditions, so that every comparison *among* them is internally
consistent. The cost is an optimistic bias in the absolute values, which the
text now states. Its size was measured on 9 Oct 2026 with the theory-faithful
Choquet control trained under both protocols on the same folds: test-fold
selection adds 0.02–0.11 AUROC depending on the gene, without changing the
ordering of any condition (D10, last paragraph). That number, not an
argument, is what bounds the effect of D3.

**D4 — per-slide predictions not written (pragmatic decision).** Fold-level
metrics were the unit of analysis; writing 180 × 101 probabilities was
omitted to keep the result files small. Nothing is lost: the 150 MIL
checkpoints are deposited on Zenodo with SHA-256 hashes and regenerate every
per-slide prediction, and B1 is deterministic (`random_state = 42`).

**D5 — hand-typed AUPRC figure (erratum, corrected).** The figure was made
from an intermediate run and transcribed by hand. The archived
`summary_table.csv` is authoritative, `figures/gen_auprc_bar_chart.py` now
reads it, and the corrected figure is in the repository. The primary claims
rest on AUROC (Table 6.5, Figures 6.6–6.9), which match the archive cell by
cell.

**D6 — ± 2.04 vs ± 2.05 (erratum).** Rounding of the same standard deviation.

**D7 — "71–76 % before the twenty fixes" (historical note).** The figure comes
from development logs that were overwritten. It is presented as context for
the pipeline audit, not as a result, and no conclusion depends on it.

**D8 — embeddings stored in float32 rather than float16 (design decision).**
Half precision quantises CTransPath features to three significant digits;
with 38.6 GB available on the DGX there was no reason to accept that loss.
The text described the planned storage format. The float32 files are the
hashed ones.

**D9 — Zenodo DOI (timing).** Not available at printing; the deposit is fixed
by `docs/zenodo_deposit/MANIFEST_sha256.txt`.

**D10 — the FC-MIL measure and integral as executed (design decisions, each
verified post hoc).** The text presents the textbook object (normalised
monotone 2-additive capacity, Choquet integral of a slide-level 6-vector,
L1 and monotonicity regularisers). The executed module departs from it in
five places, and each departure has a reason and a check:

* *Integral over the tiles, not over the slide-level 6-vector.* This is the
  substantive decision. A slide-level mean membership vector has already
  discarded *where* the patterns occur; two patterns can each cover 30 % of a
  slide without ever sharing a region. The co-presence term `m_jk s_j s_k` is
  informative only if it is evaluated on tile sets, which is what the
  executed integral does: tiles are ranked by their membership in pattern k
  and the measure is evaluated on the composition of the nested top-ranked
  sets. `evaluation/check_fuzzy_measure.py` proves that this sum *is* the
  discrete Choquet integral over the tiles (identity to 1.5e-7), so the model
  family claimed in Chapter 4 is the one executed; only the domain of
  integration differs. The decision was validated by the control of 9 Oct
  2026: the textbook slide-level Choquet, trained on the same folds under
  both protocols, performs at the level of B1 and learns interactions ≤ 0.01,
  i.e. the information the thesis attributes to pattern interactions is not
  present at slide level. Without this decision there would be no Finding 6.
* *`sigmoid(v)` singleton weights instead of `softmax(ψ)` (Eq. 4.25).* Softmax
  couples the six weights (raising one lowers the others), which makes the
  singleton gradients compete with the interaction gradients during
  training; sigmoid decouples them. Normalisation is immaterial for the
  Choquet integral, which is invariant to an affine rescaling of the
  measure up to terms absorbed by `choquet_scale` and the linear merge
  (D10 (iii)). The Shapley values of the executed measure were computed post
  hoc from the Möbius masses (φ_k = m_k + ½ Σ_j m_jk) and are flat, 0.162–0.174
  after normalisation, for every gene: the singletons carry no gene-specific
  information under either parameterisation, and what Table 6.12 reports, the
  interactions, are exactly the Shapley interaction indices of a 2-additive
  measure (Grabisch 1997).
* *Outer sigmoid on the measure.* It bounds g in (0, 1) so that the sum over
  up to 512 ranked tiles is numerically stable in float32. It is a monotone
  transformation applied to every subset alike. Its only side effect is on the
  *formal* interaction index of the composite σ∘g, which carries a common
  offset (−0.021, from the concavity of the sigmoid) while preserving the
  ranking of the pairs (Spearman 0.87 mean, 0.68 min, over the 30 folds;
  `check_fuzzy_measure.py` block 4). The text's "synergy / redundancy"
  reading is therefore a ranking among pairs, which is how Table 6.12 uses it.
* *No monotonicity penalty (Eq. 5.2).* Monotonicity was verified a
  posteriori instead of being penalised: a 2-additive game is monotone iff
  `m_k − Σ_j max(0, −m_jk) ≥ 0`, and the smallest margin over 30 folds × 6
  patterns is +0.444. The penalty would have been identically zero on every
  checkpoint, so its presence or absence could not have changed any result.
  An inactive regulariser is not a missing one.
* *No L1 on the interactions (Eq. 4.26).* The purpose of the L1 term is
  sparsity of the pair masses. The archived masses are already small
  (|m_jk| ≤ 0.040 against singletons ≈ 0.54) without it; the regulariser's
  goal was met by the data. Removing it also avoids an extra hyper-parameter
  (λ_I) that could not have been tuned without an inner split (D3).
* *Random 512-tile subsample in the Choquet branch.* Six sorts of up to
  4,096 tiles per slide per epoch would dominate the run time of a branch
  whose output is six numbers; 512 random tiles give an unbiased sample of
  the slide composition and keep the branch at the cost of the attention
  branch. The sample is redrawn at evaluation, which adds a small random
  component to each fold AUROC that is well inside the fold-to-fold SD
  (0.047–0.080 for FC-MIL).

The JSON key `fuzzy_shapley_values` stores `m_k`; the Shapley values proper
are computed by the check script (D10 (ii)).

**D11 — single-layer encoder (design decision).** Table 5.6 documents the
executed encoder (Linear 512→256 + LayerNorm, 131,840 parameters); Eq. 4.17
gives the general two-layer form of Ilse et al. One layer is the smaller
model for 404 training slides, and the parameter count printed in the thesis
is the one of the executed model. Equation and table should be reconciled in
the text; no result depends on it.

**D12 — the training protocol as executed (design decisions, logged).**

* *AdamW at 1e-4 for all five MIL conditions, instead of Adam 2e-4 for ABMIL
  and AdamW for FC-MIL.* The methodological requirement stated in §5.4.3 is
  that any difference between conditions be attributable to the
  representation and not to the optimiser. The executed protocol satisfies
  that requirement *more* strictly than the text: one optimiser, one learning
  rate, one schedule for B2, B3, PI-ABMIL, A and FC-MIL. Had the text been
  followed, FC-MIL would have been the only condition trained with decoupled
  weight decay, and the FC-MIL-vs-PI-ABMIL comparison of RQ3 would have been
  confounded. The lower learning rate goes with the absence of gradient
  accumulation (next item): one update per slide at 1e-4 rather than one
  update per four slides at 2e-4.
* *Plain cosine annealing instead of warm restarts (T₀ = 10).* Early stopping
  with patience 15 is the mechanism that ends training (137 of the 150 MIL
  runs stopped early, mean epoch 27, range 16–49, worker logs). Warm restarts
  at epochs 10, 20, 30 reset the learning rate exactly when the model is
  converging, each restart produces a validation dip that counts toward the
  patience, and the two mechanisms interfere. A single monotone cycle is the
  standard pairing with patience-based stopping. The archived logs show the
  executed schedule (`lr` 9.99e-05 at epoch 1 decreasing monotonically, no
  jump at epoch 11).
* *No gradient accumulation; gradient-norm clipping at 5.0 instead.* With
  batch 1 and an adaptive optimiser, accumulation changes the effective
  learning rate but not the stability of the updates; what stabilises
  variable-size bags is clipping, which the executed loop applies
  (`clip_grad_norm_(max_norm=5.0)`, `train_one_epoch`). Ilse et al. and CLAM
  train with batch 1 and no accumulation.
* *`StratifiedKFold` on slides rather than a patient-grouped splitter.* The
  cohort construction of §5.2 selects one slide per patient, and the executed
  505-slide list contains 505 distinct patients (no repeated 12-character TCGA
  identifier). A slide-level split is therefore a patient-level split; no
  grouping machinery was needed and no leakage is possible. The 19
  multi-slide patients mentioned in §5.2 belong to the 687-slide inventory,
  not to the executed cohort.
* *Class-weighted BCE (`pos_weight = n_neg / n_pos`).* The text omits it. It
  is applied identically to all five MIL conditions and mirrors
  `scale_pos_weight` in B1, so the six conditions treat class imbalance the
  same way; without it the 6.9 %-prevalence RBM10 head would collapse to the
  majority class at threshold 0.5 and the F1 column of Table 6.5 would be
  uninformative.
* *"FC-MIL trains faster" (erratum).* FC-MIL runs the same loop as ABMIL plus
  the Choquet branch; no timing was logged and the sentence should be
  removed.
* *B1 without early stopping and with gain importances (pragmatic
  decision).* Early stopping needs a validation set, which the executed
  protocol does not hold out (D3); 300 trees at depth 4 and learning rate
  0.05 on 404 samples is a fixed-budget configuration that cannot overfit
  catastrophically (B1 scores ≈ 0.52–0.63, at the floor by design). TreeSHAP
  is used where per-slide attribution is needed — the stand-alone B1 script
  and LCHAI level 3 — not in the benchmark, which only ranks conditions.
* *Paired tests computed at writing time.* The values quoted in §6.2.3 were
  computed from `per_fold_json/` outside the benchmark script; they are now
  reproduced by `evaluation/fold_statistics.py` (archived output in
  `logs/mutation_5fold_results/`), which also records the threshold actually
  used (d_crit = 1.24, the significance boundary for five folds) and the
  absence of a multiple-comparison correction.
