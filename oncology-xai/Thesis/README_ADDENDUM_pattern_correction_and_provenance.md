# Addendum — pattern-name correction (4 Apr 2026) and provenance of the Chapter 6 results

This addendum accompanies the files staged on the DGX under
`notebooks/slima/github_upload_4apr2026/Thesis/` and is meant to be committed
together with them into `oncology-xai/Thesis/` of `slima2/lchai`.

## 1. Pattern-name correction applied to all logs / JSON / CSV

The overlay index used to train FuzzyArcLoss V2 carried a permuted set of class
names (verified by a histopathologist on 4 Apr 2026; primary evidence:
`training/data_preparation/overlay_index_corrected_4_apr_2026.xlsx`, reference
constants: `tools/PATTERN_REMAP_4_apr_2026.py`). The models, their six output
indices and every numeric result are unchanged; only the names attached to each
index were wrong.

| model index | legacy name (pre‑4‑Apr) | true ANORAK class |
|---|---|---|
| 0 | acinar | **micropapillary** |
| 1 | lepidic | **cribriform** |
| 2 | micropapillary | **papillary** |
| 3 | mucinous | **lepidic** |
| 4 | papillary | **solid** |
| 5 | solid | **acinar** |

All result files produced before 4 Apr 2026 were rewritten with
`tools/remap_pattern_names_4apr2026.py` (single simultaneous permutation,
alphabetic token boundaries so that `pct_acinar`, `prob_mucinous`, `n_solid`,
`acinar×lepidic` … are covered). Every rewritten file carries a marker:

* JSON: top-level key `_pattern_names_corrected_4_apr_2026`
* TXT/LOG: first line `# [PATTERN NAMES CORRECTED 4-APR-2026] …`
* CSV: no in-file marker (would break parsers); tracked in
  `tools/remap_manifest_dgx.json`

The script refuses to touch a file that already carries a marker, because a
second pass would scramble the names again. Originals are archived on the DGX in
`notebooks/slima/backups_pre_pattern_fix_4apr2026/` (tar.gz + MD5 manifests).

Files corrected in this archive:

* `logs/mutation_5fold_results/per_fold_json/metrics_proposed_fuzzy_choquet_*` (30) — `fuzzy_shapley_values`, `fuzzy_interactions`
* `logs/mutation_5fold_results/per_fold_json/metrics_baseline1_xgboost_*` (30) — `feature_importances`
* `logs/pattern_classifier_results/output_kfold_fuzzyv2_sphereface.txt`, `output_ablation_best_rev13.txt`, `output_optuna_fuzzyarcv2_best.txt`, `ablation_results_v16_optuna.json`
* `logs/data_pipeline/output_pipeline_6gpu*.txt`

Check: with the corrected names, `metrics_proposed_fuzzy_choquet_KRAS_fold3.json`
gives `lepidic×solid = +0.0321` and `solid×acinar = +0.0254`, i.e. exactly the
first two rows of Table 6.12; RBM10 rows correspond to fold 4.

### 1b. Scripts, notebooks and tile-level inference CSVs (corrected 9 Oct 2026)

The same permutation was applied to the **source files** with
`tools/remap_pattern_names_in_scripts.py` (every file carries the
`[PATTERN NAMES CORRECTED 4-APR-2026]` header / notebook metadata, so a second
pass is a no-op). The index order baked into `best_fuzzyarcloss_v2.pth` and the
150 ABMIL/Choquet checkpoints is **unchanged**; only the name attached to each
index is:

| index | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| true class | micropapillary | cribriform | papillary | lepidic | solid | acinar |
| legacy name | acinar | lepidic | micropapillary | mucinous | papillary | solid |

* **Artefacts 2/3, XGBoost, `prepare_benchmark_inputs`, attention figures** —
  `PATTERN_NAMES` / `PATTERNS` / `PATTERN_ORDER` now list the true names in the
  same positions (`["micropapillary","cribriform","papillary","lepidic","solid","acinar"]`).
  These lists only label outputs (Shapley values, interactions, feature
  importances, axis labels); no numeric behaviour changes.
  `prepare_benchmark_inputs (1).py` additionally detects CSVs that still carry
  the legacy `prob_*` headers and maps them through the table above.
* **Artefact 1 (11 training scripts)** — `INCLUDE_PATTERNS` now names the six
  true classes, the default `XLS_PATH` points to
  `overlay_index_corrected_4_apr_2026.xlsx` (637 tiles, the N of Chapter 6), and
  `labels = sorted(...)` was replaced by a sort on `CLASS_ORDER_4APR2026`
  (true names in the legacy alphabetical order). This keeps `label2id` identical
  to the original runs, so the positional per-class parameters of FuzzyArcLoss
  (`class_tau`, `class_margin`, `class_scale`) and the checkpoint output indices
  keep their meaning. Comments such as `# Order: [...]` were remapped accordingly.
* **`figures/visualize_attention_patterns.py`, `figures/generate_attention_maps.py`** —
  the gene→pattern *literature priors* are biology, not legacy labels, so they
  were restored by hand (TP53: solid/micropapillary; EGFR: lepidic/papillary;
  KRAS: lepidic×solid IMA proxy of Table 6.12; STK11: lepidic/solid; KEAP1,
  RBM10: acinar/solid). The former `mucinous` prior has no counterpart among the
  six ANORAK classes.
* **`inference/*.ipynb`** (B1 development notebooks) — column names
  `pct_<pattern>` / `n_<pattern>` and printed outputs remapped; their inputs are
  the corrected summaries in `logs/tcga_tile_inference_dec2025/`.
* **Tile-level inference CSVs on the DGX** — `outputs/inference_results_parallel/`
  (322 slides, `x,y,pred_class`) and `outputs/inference_pipeline_6gpu/` (336
  slides, `x,y,pred_class,prob_*`): `prob_*`/`pct_*`/`n_*` headers remapped and a
  `pattern` column (true name of `pred_class`) appended with
  `tools/add_pattern_names_to_tile_predictions.py`; a
  `pred_class_to_pattern_4apr2026.json` sidecar sits next to the files. The
  322-slide set (which fed the B1 development notebooks) is archived in
  `logs/tcga_tile_inference_dec2025/`; the 336-slide set (201 MB, 6-GPU pipeline
  used for the Chapter 6 benchmark) is not in git for size.
* Pre-correction copies of everything touched are kept on the DGX under
  `notebooks/slima/backups/` (`thesis_scripts_pre_pattern_remap_9oct2026.tar.gz`,
  `inference_results_parallel_pre_remap_9oct2026.tar.gz`,
  `inference_pipeline_6gpu_pre_remap_9oct2026.tar.gz`); the originals in
  `notebooks/slima/*.py` were not modified.

## 2. What actually produced the Chapter 6 numbers

* Script: `training/artefact2_mutation_abmil/pattern_informed_abmil_benchmark_v2_patched.py`
  (launched 14 Mar 2026; orchestrator log
  `logs/mutation_5fold_results/orchestrator_output_benchmark_v2_patched.txt`).
  The three Feb‑28 scripts previously in the repository produced earlier,
  different result sets (`results/`, `results_FuzzyChoquetAggregation/`).
* Cohort: `--slide_list data/cohort/luad_slide_ids_available.txt` →
  **505 slides from 505 patients** (one slide per 12‑character TCGA barcode,
  patients present in `cohortMAF_LUAD2.maf`). Folds: train = 404, test = 101.
  `data/cohort/labels.csv` contains the full 687‑slide / 668‑patient label
  matrix; `luad_slide_ids_full.txt` lists those 687 slides. Of the 182 slides
  not used, 170 carry all‑zero labels (patient absent from the MAF).
  Observed prevalence in the evaluated 505: TP53 50.3 %, KRAS 27.3 %,
  KEAP1 18.2 %, EGFR 14.7 %, STK11 13.3 %, RBM10 6.9 %.
* Model selection: `_abmil_loop()` evaluates AUROC after every epoch on
  `va_ld`, which is built from the CV **test** fold (`va_idx`), keeps the best
  epoch (patience 15) and reports that same `best_val` as the fold result.
  There is no inner validation split. The reported AUROCs are therefore
  "best‑epoch‑on‑test‑fold" values and are optimistically biased; §5.8.2 of the
  thesis ("10 % of the training fold") should be reworded accordingly, or the
  benchmark re‑run with an inner split.
* Per‑slide predictions: `_save_fold()` strips `probs`/`labels` before writing
  the JSON, so no per‑fold prediction CSV exists (§5.8.3). They can be
  regenerated from the 150 checkpoints in `results_luad_full_v2/checkpoints/`
  (not in git; 103 MB zip on the DGX) for the five MIL conditions; the XGBoost
  models were not persisted.
* Artefact 1: `output_kfold_fuzzyv2_sphereface.txt` line "FuzzyArcLoss V2
  (Optuna) 92.31 % ± 2.05" is the source of the 92.31 % figure (thesis prints
  ± 2.04).

## 3. New files in this archive (previously missing from the repository)

```
Thesis/
├── data/cohort/            labels.csv, luad_slide_ids_available.txt (505),
│                           luad_slide_ids_full.txt (687), luad_cases_missing_slides.txt
├── training/artefact2_mutation_abmil/
│                           pattern_informed_abmil_benchmark_v2_patched.py
├── training/data_preparation/
│                           pipeline_6gpu_parallel.py            (tiling → FuzzyArcLoss → CTransPath → .npy)
│                           SLIMA_PARALLEL_inferencing_hist_patterns_ver_24_feb_2026_gpu_optimized.py
│                           SLIMA_PARALELL_inferencing_hist_patterns_roi_parallel_ver_14_dec_2025.py
│                                                                (produced logs/tcga_tile_inference_dec2025/; added 9 Oct 2026)
│                           crossref_slides_vs_luad_maf.py       (defines the 505-slide cohort)
│                           download_tcga_luad_maf.py, download_missing_luad_svs.py, run_all_downloads.sh
│                           overlay_index_corrected_4_apr_2026.xlsx
├── figures/                generate_attention_maps.py, visualize_attention_patterns.py
├── logs/mutation_5fold_results/   per_fold_json/ (180, corrected), worker_logs/ (6),
│                           summary_table.csv, orchestrator_output_benchmark_v2_patched.txt
├── logs/pattern_classifier_results/
│                           output_kfold_fuzzyv2_sphereface.txt, output_ablation_best_rev13.txt,
│                           output_optuna_fuzzyarcv2_best.txt, ablation_results_v16_optuna.json
├── logs/data_pipeline/     output_pipeline_6gpu*.txt, output_svs_download.txt, output_tcga_luad_download_ver1.txt
├── logs/tcga_tile_inference_dec2025/
│                           tcga_tiles_384_predictions_322_slides.zip (x,y,pred_class,pattern),
│                           tcga_case_histologic_patterns*.csv, tcga_histologic_pattern_summary_per_slide*.csv,
│                           pred_class_to_pattern_4apr2026.json
└── tools/                  remap_pattern_names_4apr2026.py, remap_pattern_names_in_scripts.py,
                            add_pattern_names_to_tile_predictions.py, remap_manifest_dgx.json,
                            PATTERN_REMAP_4_apr_2026.py
```

## 4. Large artefacts outside git (Zenodo deposit, prepared 9 Oct 2026)

Files above GitHub's 100 MB limit (or too large to be sensible in git) are
packaged on the DGX in `notebooks/slima/zenodo_deposit_thesis_4apr2026/`
(≈393 MB) with `README_deposit.md`, `MANIFEST_sha256.txt` and a draft
`zenodo_metadata.json`; copies of the three text files are in
`docs/zenodo_deposit/`. **DOI: _pending upload_** — replace this line with the
Zenodo DOI and cite it from the Reproducibility Statement.

| Deposited file | Size | sha256 (prefix) |
|---|---|---|
| `best_fuzzyarcloss_v2_labels4apr2026.pth` — Artefact 1 weights. Byte-identical tensors to the DGX `best_fuzzyarcloss_v2.pth` (`e2b2c99b…`, 24 Feb 2026); only `id2label`/`label2id` rewritten to the true names, legacy map kept in `id2label_legacy_pre_4apr2026`, `provenance` key added. `pipeline_6gpu_parallel.py` and the parallel inference script now point to it (they take `prob_*` headers from `id2label`). | 112 MB | `dc2847d4…` |
| `checkpoints_luad_v2.zip` — 150 ABMIL/Choquet checkpoints of the Chapter 6 benchmark | 104 MB | `24395fbd…` |
| `pattern_probs_687_slides.zip` — `<slide>/pattern_probs.npy` (`[n_tiles, 6]` float32) for 687 TCGA-LUAD slides, the pattern channel of Artefacts 2/3 | 138 MB | `ba4b392e…` |
| `inference_pipeline_6gpu_tile_predictions_336_slides.zip` — tile CSVs `x,y,pred_class,prob_*,pattern` (257 MB uncompressed) | 40 MB | `3cc40e14…` |
| `pred_class_to_pattern_4apr2026.json`, `overlay_index_corrected_4_apr_2026.xlsx` | <40 KB | `50a9e061…`, `c6a0659c…` |

Deliberately **not** deposited:

* `ctranspath.pth` (111 MB) — third-party weights (Wang et al., MedIA 2022,
  <https://github.com/Xiyue-Wang/TransPath>); download from the authors and
  check `sha256 7c998680060c8743551a412583fac689db43cec07053b72dfec6dcd810113539`.
  Not needed for inference: the fine-tuned backbone is inside
  `best_fuzzyarcloss_v2_labels4apr2026.pth`.
* `embeddings.npy` per slide (687 × `[n_tiles, 512]` float32, **38.6 GB**) —
  regenerable from public TCGA-LUAD slides + `ctranspath.pth` with
  `training/data_preparation/pipeline_6gpu_parallel.py`; the sha256 of every
  file is in `docs/zenodo_deposit/embeddings_sha256_manifest_REGENERABLE_not_deposited.txt`
  (`sha256sum -c`), and the files are available from the author on request.

The pattern-classifier checkpoints trained after the correction
(`outputs/optuna_v2_search/best_fuzzyarcloss_v31_subcenter_optuna.pth`,
`…_v4_boundary_optuna.pth`, 6 Jul 2026) belong to the follow-up paper, use a
*different* index order (alphabetical on the true names: acinar, cribriform,
lepidic, micropapillary, papillary, solid) and are **not** the thesis model.

## 5. Pruning of superseded script versions (9 Oct 2026)

Rule applied: for every result in the thesis, keep the **one** script version
that produced the archived log / CSV / JSON, plus the data-preparation scripts
on its path. Earlier or parallel versions that produced no archived result were
removed from the repository. All of them remain in git history (commit
`d7543a2`) and on the DGX (`notebooks/slima/`, and
`backups/thesis_scripts_pre_pattern_remap_9oct2026.tar.gz`).

| Removed | Why |
|---|---|
| `artefact1/SLIMA_ablation_study_loss_functions_ver_11_jan_2026 rev 2 (2).py`, `…_ver_12_feb_2026_rev5.py` | pre-audit ablation versions (150 epochs, before the 20 fixes of §3.7); superseded by `…_ver_23_feb_2026_gpu_rev_13 (1).py`, whose log `output_ablation_best_rev13.txt` is the archived Table 6.1 run |
| `artefact1/SLIMA_ablation_v2_5 fuzzyarcloss ver 6 jan 2026.py`, `SLIMA_ablation_v3 improved ver 5 jan 2026.py`, `SLIMA_complete_ablation_multigpu ver 3 jan 2026.py`, `SLIMA fuzzy_arc_loss_v2 ver 3 jan 2026.py` | January 2026 exploratory variants; all loss variants they introduced (V2.5, V3 entropy/sub-centers/top-gap) are contained in the rev-13 ablation; the loss module was never imported by any kept script |
| `artefact1/SLIMA_advanced_benchmark_v3 FSL fixed ver 21 jan 2026 rev 3 (3).py` | few-shot / meta-learning benchmark (Proto, MAML, Relation, TraNFS); not reported in the thesis |
| `artefact1/SLIMA_improved_pathology_backbone_90_target ver 27 dec 2025 rev 10.py` | Dec-2025 backbone experiment; its model is not the one used anywhere in the archive (the Dec-2025 TCGA inference used the ROI model `anorak_roi_acc6_v5`) |
| `artefact2/pattern_informed_abmil_benchmark.py`, `…_paralell.py`, `SLIMA pattern informed ABMIL benchmark … ver 27 feb 2026.py` | Feb-28 LUAD+LUSC / 768-d versions; produced the superseded `results/` set |
| `artefact2/pattern_informed_abmil_benchmark_v2.py` | identical to `…_v2_patched.py` except that it does not save the per-fold checkpoints |
| `artefact3/pattern_informed_abmil_benchmark_FuzzyChoquetAggregation.py` | Feb-28 stand-alone FC-MIL; produced the superseded `results_FuzzyChoquetAggregation/` set. FC-MIL classes live in `…_v2_patched.py` (see `artefact3_mutation_choquet/README.md`) |
| `xgboost_baseline/SLIMA_aggregation_xgboost_mutation_prediction_v2_feb_2026 ver 24 feb 2026 (1).py` | earlier revision of `…_v24_feb_2026  rev 4 (1).py` (rev 4 adds multi-MAF / LUSC label loading) |
| `data_preparation/run_all_downloads.sh` | drives CPTAC-3 / APOLLO / EAGLE downloads through five scripts that were never written; those cohorts are explicitly *not* used (thesis §3.4, Table 3.10) |
| `inference/SLIMA_histology_mutation_xgboost ver 25 nov 2025 (1).ipynb` | Nov-2025 B1 notebook on 138 slides; superseded by the 1 Feb 2026 notebook on the 322-slide Dec-2025 inference |
| `logs/tcga_tile_inference_dec2025/tcga_case_histologic_patterns.csv`, `tcga_histologic_pattern_summary_per_slide.csv` | Nov-2025 summaries (134 cases / 138 slides); the `*_dec2025.csv` files (305 cases / 322 slides) match the archived zip |

Added at the same time: `training/data_preparation/SLIMA_PARALELL_inferencing_hist_patterns_roi_parallel_ver_14_dec_2025.py`,
the script that actually produced `logs/tcga_tile_inference_dec2025/` (it reads
`id2label` from the checkpoint, so it carries no hard-coded pattern names).

Known gap: the pre-audit figure quoted in §3.7 / §6.1.1 ("71–76 % before the
twenty fixes") has no archived script + log pair. The only pre-audit log on the
DGX (`output_ablation_allfuzzy_allothers.txt`, 150 epochs) was run on a
775-tile split (542/116/117) rather than the 637-tile split and is truncated
after 3 of 18 losses, so it was not added.
