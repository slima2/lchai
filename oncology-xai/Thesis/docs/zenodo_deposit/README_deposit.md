# LCHAI thesis artefacts — model weights, checkpoints and per-slide inference outputs

Companion deposit for the code repository
<https://github.com/slima2/lchai> (folder `oncology-xai/Thesis/`), Ph.D. thesis
*Servio Fernando Lima Reina*, Department of Informatics, University of Fribourg:
"Pattern-Informed Fuzzy Deep Learning for Interpretable Genotype–Phenotype
Inference in Lung Adenocarcinoma under Data Scarcity".

Everything here is too large for git (except the Artefact 1 weights, which are
also in the repository xz-compressed).

## Contents

| File | Size | What it is |
|---|---|---|
| `best_fuzzyarcloss_v2.pth` | 112 MB | **Artefact 1** — CTransPath (Swin-T) + FuzzyArcLoss V2 six-pattern classifier (ablation winner, 5-fold 92.31 % ± 2.04, held-out test acc 0.9375 / macro-F1 0.939, best epoch 77). Keys: `model`, `loss_fn`, `config`, `label2id`, `id2label`, `loss_kwargs`, `test_f1`, `test_accuracy`, `best_epoch`, plus two bookkeeping keys (`provenance`, `id2label_legacy_pre_4apr2026`) that can be ignored. Same file as `Thesis/models/best_fuzzyarcloss_v2.pth.xz` in the repository. |
| `checkpoints_luad_v2.zip` | 104 MB | **Artefacts 2/3** — the 150 PyTorch checkpoints (`ckpt_<condition>_<gene>_fold<k>.pth`) of the Chapter 6 benchmark: 5 MIL conditions × 6 genes (TP53, KRAS, EGFR, STK11, KEAP1, RBM10) × 5 folds, trained by `training/artefact2_mutation_abmil/pattern_informed_mil_benchmark.py`. |
| `pattern_probs_687_slides.zip` | 138 MB | Per-slide `<slide_dir>/pattern_probs.npy`, float32 `[n_tiles, 6]`, Artefact 1 softmax over the six patterns for every 384-px tile of 687 TCGA-LUAD slides. This is the pattern channel consumed by Artefacts 2/3 (`baseline3_abmil_patterns`, `proposed_abmil_concat`, `proposed_fuzzy_choquet`). Column order = class index order below. |
| `embeddings_SAMPLE_6_case_study_slides.zip` | 341 MB | Sample of the per-slide CTransPath embeddings for the six slides discussed as case studies in Chapter 6 (TCGA-55-7815, TCGA-49-AAR9, TCGA-86-8280, TCGA-99-8025, TCGA-78-7148, TCGA-49-AAR0): `<slide_dir>/embeddings.npy` (`[n_tiles, 512]` float32), `pattern_probs.npy` (`[n_tiles, 6]` float32) and `pattern_labels.npy` (argmax, int). 569 MB uncompressed, 2 883 – 112 171 tiles per slide. Illustrates the format of the full 38.6 GB set (not deposited, see below). |
| `inference_pipeline_6gpu_tile_predictions_336_slides.zip` | 40 MB | Tile-level CSVs (`x,y,pred_class,prob_micropapillary,…,prob_acinar,pattern`) of the 336 slides processed by `training/data_preparation/pipeline_6gpu_parallel.py` (257 MB uncompressed). |
| `pred_class_to_pattern.json` | <1 KB | `pred_class` index → pattern name (table below). |
| `overlay_index.xlsx` | 38 KB | ANORAK tile index (637 tiles, tile → pattern) used to train Artefact 1; built by `training/data_preparation/build_anorak_overlay_index.py`. |
| `MANIFEST_sha256.txt` | | sha256 of every deposited file. |
| `ctranspath_sha256_NOT_REDISTRIBUTED.txt` | | sha256 of the third-party CTransPath weights (see below). |
| `embeddings_sha256_manifest_REGENERABLE_not_deposited.txt` | | sha256 of the 687 per-slide `embeddings.npy` that are not deposited (see below). |

## Class index order (all files)

| index | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| class | micropapillary | cribriform | papillary | lepidic | solid | acinar |

The order is fixed by the trained weights and is **not** alphabetical; take the
names from `id2label` / `pred_class_to_pattern.json` rather than re-deriving them.

## Not deposited

### `ctranspath.pth` (third-party, 111 MB)

CTransPath backbone of Wang et al., *Transformer-based unsupervised contrastive
learning for histopathological image classification*, Medical Image Analysis
81 (2022) 102559. Download from the authors' repository
<https://github.com/Xiyue-Wang/TransPath> and verify:

```
sha256  7c998680060c8743551a412583fac689db43cec07053b72dfec6dcd810113539  ctranspath.pth
```

Note: `best_fuzzyarcloss_v2.pth` already contains the fine-tuned backbone;
`ctranspath.pth` is only needed to re-run training from scratch or to
regenerate the raw 512-d embeddings.

### `embeddings.npy` per slide (687 × float32 `[n_tiles, 512]`, 38.6 GB total)

Deterministically regenerable from public inputs: TCGA-LUAD diagnostic slides
(GDC), `ctranspath.pth` and `training/data_preparation/pipeline_6gpu_parallel.py`
(stage 1 tiles + embeds at 384 px / 20×, stage 2 writes `embeddings.npy`,
`pattern_probs.npy`, `pattern_labels.npy`). The sha256 of every regenerated
file can be checked against `embeddings_sha256_manifest_REGENERABLE_not_deposited.txt`
(`sha256sum -c`). Six slides are included as a format sample
(`embeddings_SAMPLE_6_case_study_slides.zip`); the full set is available from the
author on request if regeneration is not practical.

## How to use

```python
import torch
ck = torch.load("best_fuzzyarcloss_v2.pth", map_location="cpu", weights_only=False)
ck["id2label"]   # {0:'micropapillary',1:'cribriform',2:'papillary',3:'lepidic',4:'solid',5:'acinar'}
```

Set `MODEL_PATH` in `pipeline_6gpu_parallel.py` /
`tile_pattern_inference_multigpu.py` to
this file; both scripts read `id2label` from the checkpoint, so the `prob_*`
headers and the `pattern` column come out with the right names.

Verify integrity with `sha256sum -c MANIFEST_sha256.txt`.

## License

Code: see repository. Weights and derived outputs: CC BY 4.0. TCGA-LUAD source
images are subject to the NIH/GDC data-use policies; no raw slide images are
included.
