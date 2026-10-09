# Artefact 3 — Fuzzy Choquet MIL (FC-MIL)

The FC-MIL condition (`proposed_fuzzy_choquet` in `summary_table.csv` and the
`per_fold_json/`) was trained by the **same script** as the other five conditions:

`../artefact2_mutation_abmil/pattern_informed_abmil_benchmark_v2_patched.py`

| Component | Location in that script |
|---|---|
| `FuzzyMeasure` — 2-additive fuzzy measure (6 singleton densities + 15 pairwise interactions = 21 parameters) | `class FuzzyMeasure` (≈ line 282) |
| `FuzzyChoquetAggregation` — discrete Choquet integral over the 6 pattern memberships | `class FuzzyChoquetAggregation` (≈ line 297) |
| `FuzzyChoquetMIL` — dual pathway: gated-attention ABMIL on the 512-d embedding + Choquet branch | `class FuzzyChoquetMIL` (≈ line 343) |
| Training loop / fold routine, writes `fuzzy_shapley_values` and `fuzzy_interactions` into the fold JSON | `train_fuzzy_choquet()` (≈ line 499) |

The Shapley values and interaction indices of Table 6.12 are read from
`logs/mutation_5fold_results/per_fold_json/metrics_proposed_fuzzy_choquet_<gene>_fold<k>.json`
and plotted by `figures/gen_choquet_plots.py`.

A stand-alone, earlier version of the same classes
(`pattern_informed_abmil_benchmark_FuzzyChoquetAggregation.py`, 28 Feb 2026,
LUAD+LUSC cohort, 768-d embeddings) produced a different, superseded result set
and was removed from the repository on 9 Oct 2026; it remains in git history
(commit `d7543a2`) and on the DGX.
