# Artefact 1 weights — FuzzyArcLoss V2 pattern classifier

`best_fuzzyarcloss_v2.pth.xz` (96.8 MiB) is the thesis model,
xz-compressed to fit GitHub's 100 MiB per-file limit. Decompressed it is the
111.8 MB PyTorch checkpoint `best_fuzzyarcloss_v2.pth`
(CTransPath Swin-T + ConvStem backbone, 512-d projection head, FuzzyArcLoss V2
class prototypes; ablation winner, 5-fold 92.31 % ± 2.04, held-out test
acc 0.9375 / macro-F1 0.939, best epoch 77).

It is the checkpoint used for every inference in the archive (DGX,
`outputs/ablation_study_v16_optuna/`, 24 Feb 2026). Its `id2label` carries the
fixed class index order below; the `id2label_legacy_pre_4apr2026` and
`provenance` keys are internal bookkeeping and can be ignored.

## Decompress and verify

```bash
cd Thesis/models
xz -d -k best_fuzzyarcloss_v2.pth.xz      # Linux / macOS (7-Zip on Windows)
sha256sum -c SHA256SUMS
```

or, without xz installed:

```bash
python -c "import lzma,shutil; shutil.copyfileobj(lzma.open('best_fuzzyarcloss_v2.pth.xz'), open('best_fuzzyarcloss_v2.pth','wb'))"
```

## Contents

```python
import torch
ck = torch.load("best_fuzzyarcloss_v2.pth", map_location="cpu", weights_only=False)
ck.keys()        # model, loss_fn, config, label2id, id2label, id2label_legacy_pre_4apr2026,
                 # provenance, loss_kwargs, test_f1, test_accuracy, best_epoch
ck["id2label"]   # {0:'micropapillary', 1:'cribriform', 2:'papillary', 3:'lepidic', 4:'solid', 5:'acinar'}
ck["config"]     # EMBED_DIM 512, IMG_SIZE 224, USE_MASK_AS_CHANNEL True, s 46.10, m 0.518, tau 0.448
```

| index | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| class | micropapillary | cribriform | papillary | lepidic | solid | acinar |

## Use

`training/data_preparation/pipeline_6gpu_parallel.py` and
`tile_pattern_inference_multigpu.py`
load it through `MODEL_PATH`; both read `id2label` from the checkpoint, so the
`prob_*` headers and the `pattern` column come out with the true names. The
fine-tuned backbone is inside the file; the third-party `ctranspath.pth` is
only needed to retrain from scratch (see `../README.md`, "Model weights and large artefacts").

The same file, the 150 ABMIL/Choquet checkpoints and the per-slide pattern
probabilities are also in the Zenodo deposit (`docs/zenodo_deposit/`).
