# Hand-layout figure scripts (post-defence revision, Nov 2026)

Scripts that redrew the thesis figures so that printed text is >= 8 pt and no label overflows its box or overlaps other text or lines.

- `fx.py`: helper `Canvas(W, H, minpt=8)` (7.2 in wide canvas, auto-wrap/fit text, boxes, arrows) and `audit(fig)` (overlap / out-of-canvas check).
- `batch1.py` ... `batch24.py`, `classparams.py`, `subcenters.py`, `b3_regimes.py`, `kras_*.py`: one function per figure; each writes `../man_out/<figure>.png` (create that folder next to the scripts).
  - batch23: Fig. 3.2 (`who_luad_patterns`) and Fig. 3.6 (`he_workflow_solca`), cropped from the original composites in `src/`.
  - batch24: Fig. 4.14 (five fuzzy membership functions as one figure, `fuzzy_mf_scales_combined`).
  - batch13/18 read data from the original `gen_*.py` scripts and from the Optuna log in `Thesis/logs/pattern_classifier_results/`.
- `install_figs.py`: copies the PNGs into the thesis figure folders; `audit.py`: OCR estimate of the smallest printed text per figure.

Photographs and software screenshots cannot be redrawn here. LaTeX: figures are set with `[H]` so they stay where they are cited.
