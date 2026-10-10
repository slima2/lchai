#!/usr/bin/env python3
"""Fold-paired statistics for the mutation benchmark (Artefacts 2 and 3, Ch. 6 Sec. 6.2).

pattern_informed_mil_benchmark.py archives one JSON per (condition, gene, fold) under
logs/mutation_5fold_results/per_fold_json/ and a summary_table.csv with mean and SD,
but it does not compare conditions. This script reproduces the statistics quoted in
Sec. 6.2 (Finding 2 decision rules) and in the defense backup slides "Fold variation
vs effect size": for every gene and every comparison it reports the fold-to-fold SD,
the mean paired difference, the paired t-test, Cohen's d_z (mean difference / SD of the
differences) and two thresholds for n = 5 folds: d_crit = t_{0.975,4} / sqrt(5) = 1.24, the
smallest |d_z| that reaches p < 0.05 (the "about 1.2" of Sec. 6.2.3 and the backup slides),
and the 80 %-power minimum detectable effect, 1.68. Verdicts use d_crit, as the thesis does.
No multiple-comparison correction is applied (36 pairwise tests per metric); the two
nominal p < 0.05 results reported in block 4 do not survive a Bonferroni factor of 6.

Usage:
    python evaluation/fold_statistics.py [--results_dir logs/mutation_5fold_results]
                                         [--metric auroc] [--csv out.csv]
"""
import argparse
import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent.parent
CONDITIONS = {
    "baseline1_xgboost": "B1 XGBoost",
    "baseline2_abmil_embeddings": "B2 embedding-only",
    "baseline3_abmil_patterns": "B3 pattern-only",
    "proposed_abmil_concat": "PI-ABMIL",
    "ablation_abmil_onehot": "one-hot",
    "proposed_fuzzy_choquet": "FC-MIL",
}
GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]
COMPARISONS = [  # (condition, reference)
    ("proposed_abmil_concat", "baseline2_abmil_embeddings"),
    ("ablation_abmil_onehot", "baseline2_abmil_embeddings"),
    ("proposed_fuzzy_choquet", "baseline2_abmil_embeddings"),
    ("proposed_fuzzy_choquet", "proposed_abmil_concat"),
    ("proposed_abmil_concat", "ablation_abmil_onehot"),
    ("baseline3_abmil_patterns", "baseline1_xgboost"),
]


def load_folds(results_dir: Path, metric: str):
    """Return {condition: {gene: np.array of per-fold metric, fold order 0..n-1}}."""
    out = {}
    for f in sorted((results_dir / "per_fold_json").glob("metrics_*_fold*.json")):
        stem = f.stem[len("metrics_"):]
        cond_gene, fold = stem.rsplit("_fold", 1)
        cond, gene = cond_gene.rsplit("_", 1)
        out.setdefault(cond, {}).setdefault(gene, {})[int(fold)] = json.load(open(f))[metric]
    return {c: {g: np.array([v[k] for k in sorted(v)]) for g, v in gs.items()} for c, gs in out.items()}


def mde_dz(n: int, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable Cohen's d_z for a two-sided paired t-test with n pairs."""
    df = n - 1
    t_alpha = stats.t.ppf(1 - alpha / 2, df)
    # solve for ncp such that P(|T| > t_alpha | ncp) = power
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        pw = 1 - stats.nct.cdf(t_alpha, df, mid) + stats.nct.cdf(-t_alpha, df, mid)
        lo, hi = (mid, hi) if pw < power else (lo, mid)
    return (lo + hi) / 2 / math.sqrt(n)


def d_crit(n: int, alpha: float = 0.05) -> float:
    """|d_z| at which a paired t-test with n pairs is exactly significant at alpha."""
    return stats.t.ppf(1 - alpha / 2, n - 1) / math.sqrt(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results_dir", default=str(HERE / "logs" / "mutation_5fold_results"))
    ap.add_argument("--metric", default="auroc", choices=["auroc", "auprc", "f1"])
    ap.add_argument("--csv", default=None, help="optional path to write the comparison table")
    args = ap.parse_args()
    folds = load_folds(Path(args.results_dir), args.metric)
    n = len(next(iter(next(iter(folds.values())).values())))

    thr = d_crit(n)
    print(f"Metric: {args.metric}   folds: {n}   d_crit (p = 0.05): {thr:.2f}   MDE (power 0.80): {mde_dz(n):.2f}\n")
    print("1. Fold-to-fold SD per gene and condition (population SD, as summary_table.csv)")
    print("   gene   " + "  ".join(f"{CONDITIONS[c]:>18s}" for c in CONDITIONS))
    for g in GENES:
        print(f"   {g:6s} " + "  ".join(f"{folds[c][g].std():18.3f}" for c in CONDITIONS))

    print("\n2. Fold-paired comparisons (difference = condition - reference)")
    rows = []
    for cond, ref in COMPARISONS:
        print(f"\n   {CONDITIONS[cond]}  vs  {CONDITIONS[ref]}")
        print("   gene   mean_cond  mean_ref   diff    sd_diff   t      p      d_z    verdict")
        for g in GENES:
            a, b = folds[cond][g], folds[ref][g]
            d = a - b
            t, p = stats.ttest_rel(a, b)
            dz = d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else float("nan")
            verdict = "null (|d| < d_crit)" if abs(dz) < thr else ("gain" if dz > 0 else "loss")
            print(f"   {g:6s} {a.mean():8.3f}  {b.mean():8.3f}  {d.mean():+7.3f}  {d.std(ddof=1):7.3f}  {t:+5.2f}  {p:5.3f}  {dz:+5.2f}   {verdict}")
            rows.append(dict(metric=args.metric, condition=cond, reference=ref, gene=g, mean_condition=a.mean(),
                             mean_reference=b.mean(), diff=d.mean(), sd_diff=d.std(ddof=1), t=t, p=p, d_z=dz,
                             folds_cond=";".join(f"{x:.3f}" for x in a), folds_ref=";".join(f"{x:.3f}" for x in b)))

    print("\n3. Per-fold values for the KRAS close-up (FC-MIL vs B2)")
    for k, (a, b) in enumerate(zip(folds["proposed_fuzzy_choquet"]["KRAS"], folds["baseline2_abmil_embeddings"]["KRAS"])):
        print(f"   fold {k}: FC-MIL {a:.3f}  B2 {b:.3f}  diff {a-b:+.3f}")

    print("\n4. Pairwise ties among the four deep conditions (any gene with p < 0.05?)")
    deep = ["baseline2_abmil_embeddings", "proposed_abmil_concat", "ablation_abmil_onehot", "proposed_fuzzy_choquet"]
    sig = [(CONDITIONS[c1], CONDITIONS[c2], g, stats.ttest_rel(folds[c1][g], folds[c2][g])[1])
           for c1, c2 in combinations(deep, 2) for g in GENES if stats.ttest_rel(folds[c1][g], folds[c2][g])[1] < 0.05]
    print("   none" if not sig else "\n".join(f"   {a} vs {b} on {g}: p = {p:.3f}" for a, b, g, p in sig))

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        print(f"\nwritten {args.csv}")


if __name__ == "__main__":
    main()
