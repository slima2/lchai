"""
Shared loader for the Chapter 6 figure generators.

Reads ``logs/mutation_5fold_results/summary_table.csv`` (the file written by
``pattern_informed_mil_benchmark.py`` at the end of the 5-fold
benchmark) so that every figure is regenerated from the archived results
instead of from numbers typed by hand.

Usage inside a generator::

    from summary_data import load_summary, parse_args, GENES, CONDITIONS
    args = parse_args("auroc_by_gene.png")
    S = load_summary(args.summary)          # S[label][gene] -> dict(auroc_mean, auroc_std, ...)
    fig.savefig(args.out_dir / args.out_name, ...)

Only the standard library is used for loading (no pandas dependency).
"""
from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
from typing import Dict

HERE = Path(__file__).resolve().parent
DEFAULT_SUMMARY = HERE.parent / "logs" / "mutation_5fold_results" / "summary_table.csv"
DEFAULT_OUT_DIR = HERE / "output"

GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

# benchmark condition id (as in summary_table.csv / per_fold_json)  ->  label used in the thesis figures
CONDITIONS: Dict[str, str] = {
    "baseline1_xgboost":          "B1: XGB",
    "baseline2_abmil_embeddings": "B2: ABMIL-emb",
    "baseline3_abmil_patterns":   "B3: ABMIL-pat",
    "proposed_abmil_concat":      "PI-ABMIL (ours)",
    "ablation_abmil_onehot":      "Abl: one-hot",
    "proposed_fuzzy_choquet":     "FC-MIL (ours)",
}
LABELS = list(CONDITIONS.values())

# consistent colours / hatches across all figures
COLORS = {
    "B1: XGB": "#7EC8E3", "B2: ABMIL-emb": "#1B3A5C", "B3: ABMIL-pat": "#2E8B57",
    "PI-ABMIL (ours)": "#E05252", "Abl: one-hot": "#B0A0D0", "FC-MIL (ours)": "#F5A623",
}
HATCHES = {lbl: ("//" if lbl == "Abl: one-hot" else "") for lbl in LABELS}


def load_summary(path: os.PathLike | str = DEFAULT_SUMMARY) -> Dict[str, Dict[str, Dict[str, float]]]:
    """Return ``{label: {gene: {metric: value}}}`` for the 36 (condition, gene) rows."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"summary_table.csv not found: {path}")
    out: Dict[str, Dict[str, Dict[str, float]]] = {lbl: {} for lbl in LABELS}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            cond, gene = row["condition"], row["gene"]
            if cond not in CONDITIONS or gene not in GENES:
                continue
            out[CONDITIONS[cond]][gene] = {
                k: float(row[k]) for k in ("auroc_mean", "auroc_std", "auprc_mean", "auprc_std", "f1_mean", "f1_std")
            } | {"n_folds": int(row["n_folds"])}
    missing = [(l, g) for l in LABELS for g in GENES if g not in out[l]]
    if missing:
        raise ValueError(f"summary_table.csv is missing {len(missing)} (condition, gene) rows, e.g. {missing[:3]}")
    return out


def matrix(S, metric: str, labels=None, genes=GENES):
    """Return a nested list [len(labels) x len(genes)] of ``metric``."""
    labels = labels or LABELS
    return [[S[l][g][metric] for g in genes] for l in labels]


def parse_args(default_out_name: str) -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", default=str(DEFAULT_SUMMARY),
                    help="path to summary_table.csv (default: Thesis/logs/mutation_5fold_results/summary_table.csv)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="directory for the PNG (default: Thesis/figures/output)")
    ap.add_argument("--out-name", default=default_out_name)
    args = ap.parse_args()
    args.out_dir = Path(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    return args
