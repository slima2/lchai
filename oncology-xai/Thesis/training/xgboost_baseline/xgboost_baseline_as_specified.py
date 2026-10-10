#!/usr/bin/env python3
"""
Condition B1 (XGBoost floor baseline) exactly as written in the thesis (Sec. 5.4.2, Table 5.8).
=================================================================================================

EXPOSITORY implementation. The archived B1 numbers (Table 6.5) come from `train_xgboost()` in
../artefact2_mutation_abmil/pattern_informed_mil_benchmark.py, which fits all 300 trees without
a validation set and stores `feature_importances_`; the stand-alone development script next to
this file (xgboost_mutation_from_pattern_profiles.py) uses other hyper-parameters and features.
See ../../provenance/README.md, item D12.

As written:
  features   : argmax pattern per tile -> 6 fractions + entropy  (the code block of Sec. 5.4.2)
  folds      : 5-fold, stratified on the gene label, all slides of a patient in one fold (Sec. 5.8)
  model      : XGBClassifier(max_depth=4, n_estimators=300, learning_rate=0.05,
               scale_pos_weight = n_neg / n_pos, eval_metric="logloss", random_state=42)
  early stop : 30 rounds without improvement of logloss on a held-out 10 % of the training fold
  TreeSHAP   : per-feature attributions on the test fold (Lundberg et al., 2020)
  outputs    : metrics_baseline1_xgboost_<gene>_fold<k>.json (with per-slide predictions),
               summary_table.csv

Usage:
  python xgboost_baseline_as_specified.py --data_dir /path/to/data --results_dir out [--genes TP53 KRAS]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "artefact2_mutation_abmil"))
from pattern_informed_mil_benchmark import GENES, SlideData, build_summary  # noqa: E402
from pattern_informed_mil_benchmark_as_specified import (  # noqa: E402
    Config, fit_xgboost, inner_split, patient_folds, patient_id, save_fold)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="/home/rapids/notebooks/slima/data")
    ap.add_argument("--results_dir", default="/home/rapids/notebooks/slima/results_b1_as_specified")
    ap.add_argument("--slide_list", default=None)
    ap.add_argument("--genes", nargs="+", default=GENES)
    args = ap.parse_args()
    cfg = Config(data_dir=args.data_dir, results_dir=args.results_dir, genes=args.genes, device="cpu")
    data_dir, results_dir = Path(cfg.data_dir), Path(cfg.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    labels_df = pd.read_csv(data_dir / "labels.csv").set_index("slide_id")
    allowed = {l.strip() for l in open(args.slide_list) if l.strip()} if args.slide_list else None
    slide_ids = sorted(d.name for d in (data_dir / "slides").iterdir()
                       if d.is_dir() and (d / "pattern_probs.npy").exists() and d.name in labels_df.index
                       and (allowed is None or d.name in allowed))
    slides = [SlideData(s, cfg.data_dir) for s in slide_ids]
    print(f"Slides: {len(slides)}  patients: {len({patient_id(s) for s in slide_ids})}")
    results = {"baseline1_xgboost": {}}

    for gene in cfg.genes:
        raw = labels_df.loc[slide_ids, gene]; keep = ~raw.isna()
        g_slides = [s for s, k in zip(slides, keep) if k]
        g_labels = raw[keep].values.astype(int)
        g_ids = [s.slide_id for s in g_slides]
        results["baseline1_xgboost"][gene] = []
        print(f"\nGene: {gene}  slides={len(g_slides)}  pos={g_labels.mean():.1%}")
        for fold, (trv, te) in enumerate(patient_folds(g_ids, g_labels, cfg.n_folds, cfg.seed)):
            tr_rel, va_rel = inner_split([g_ids[i] for i in trv], g_labels[trv], cfg.val_frac, cfg.seed + fold)
            tr, va = trv[tr_rel], trv[va_rel]
            sl = lambda ix: [g_slides[i] for i in ix]
            for s in sl(trv) + sl(te):
                s.load()
            m = fit_xgboost(sl(tr), g_labels[tr], sl(va), g_labels[va], sl(te), g_labels[te], cfg, "", gene, fold)
            results["baseline1_xgboost"][gene].append(m)
            save_fold(results_dir, "baseline1_xgboost", gene, fold, m)
            for s in sl(trv) + sl(te):
                s.unload()

    summary = build_summary(results, cfg, ["baseline1_xgboost"])
    summary.to_csv(results_dir / "summary_table.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
