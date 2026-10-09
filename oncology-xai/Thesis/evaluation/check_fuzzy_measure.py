#!/usr/bin/env python3
"""Post-hoc checks of the FC-MIL fuzzy measure as executed (provenance D10).

1. Identity: the aggregation in FuzzyChoquetAggregation.choquet_integral() is the
   discrete Choquet integral over the N tiles, written in summation-by-parts form:

       code_k = x_(1) g(U_1) + x_(N) g(U_N) - C_g(x_k) + sum_i (x_(i+1)-x_(i)) (g(U_{i+1})-g(U_i))

   where x_k are the tile memberships of pattern k sorted descending, U_i the top-i
   tiles, g(U) the 2-additive set function evaluated on the mean composition of U, and
   C_g(x_k) = sum_i (x_(i) - x_(i+1)) g(U_i) the discrete Choquet integral. The sign and the
   boundary term are absorbed by the learnable choquet_scale and the linear merge layer.

2. Monotonicity: a 2-additive set function with Mobius masses m_k (singletons) and
   m_jk (pairs) is monotone iff m_k - sum_j max(0, -m_jk) >= 0 for every k. Checked on
   every archived FC-MIL fold (logs/mutation_5fold_results/per_fold_json).

3. Shapley values from the archived Mobius masses: phi_k = m_k + 1/2 sum_j m_jk
   (the JSON key "fuzzy_shapley_values" stores m_k = sigmoid(v_k), i.e. the singleton
   Mobius masses, not phi_k).
"""
import glob
import json
import os

import numpy as np
import torch

PATTERNS = ["micropapillary", "cribriform", "papillary", "lepidic", "solid", "acinar"]
HERE = os.path.dirname(os.path.abspath(__file__))
PER_FOLD = os.path.join(HERE, "..", "logs", "mutation_5fold_results", "per_fold_json")


def g_factory(v, v2):
    def g(mask):
        singleton = (mask * torch.sigmoid(v)).sum(-1)
        outer = mask.unsqueeze(-1) * mask.unsqueeze(-2)
        return torch.sigmoid(singleton + (outer * torch.triu(v2, 1)).sum((-1, -2)))
    return g


def identity_check(trials=200, seed=0):
    torch.manual_seed(seed)
    v, v2 = torch.randn(6), torch.randn(6, 6) * 0.3
    g = g_factory(v, v2)
    worst = 0.0
    for _ in range(trials):
        n = int(torch.randint(20, 400, (1,)))
        p = torch.softmax(torch.randn(n, 6) * 2, 1)
        for k in range(6):
            order = torch.argsort(p[:, k], descending=True)
            sp = p[order]
            cum = torch.cumsum(sp, 0) / torch.arange(1, n + 1).float().unsqueeze(1)
            mu = g(cum)
            x = sp[:, k]
            code = (x * (mu - torch.cat([mu[1:], torch.zeros(1)]))).sum()          # as executed
            choquet = ((x - torch.cat([x[1:], torch.zeros(1)])) * mu).sum()        # C_g(x_k)
            second = ((x[1:] - x[:-1]) * (mu[1:] - mu[:-1])).sum()
            rhs = x[0] * mu[0] + x[-1] * mu[-1] - choquet + second
            worst = max(worst, float(abs(code - rhs)))
    return worst


def archived_measures():
    rows = []
    for f in sorted(glob.glob(os.path.join(PER_FOLD, "metrics_proposed_fuzzy_choquet_*_fold*.json"))):
        d = json.load(open(f))
        m1 = np.array([d["fuzzy_shapley_values"][p] for p in PATTERNS])
        M = np.zeros((6, 6))
        for key, val in d["fuzzy_interactions"].items():
            a, b = key.split("×")
            i, j = PATTERNS.index(a), PATTERNS.index(b)
            M[i, j] = M[j, i] = val
        gene = os.path.basename(f).split("_")[4]
        rows.append((gene, f, m1, M))
    return rows


if __name__ == "__main__":
    print(f"1. identity  max|code - rhs| over random bags: {identity_check():.1e}")
    rows = archived_measures()
    margins = [(m1 - np.clip(-M, 0, None).sum(1)).min() for _, _, m1, M in rows]
    print(f"2. monotonicity  {len(rows)} archived FC-MIL folds, min margin m_k - sum_j max(0,-m_jk) = {min(margins):.3f}  "
          f"({'all monotone' if min(margins) >= 0 else 'VIOLATION'})")
    print("3. Shapley values phi_k = m_k + 1/2 sum_j m_jk, normalised, mean over folds:")
    for gene in ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]:
        phis = [(m1 + 0.5 * M.sum(1)) / (m1 + 0.5 * M.sum(1)).sum() for g_, _, m1, M in rows if g_ == gene]
        if phis:
            ph = np.mean(phis, 0)
            print(f"   {gene:6s} " + "  ".join(f"{p[:5]}={x:.3f}" for p, x in zip(PATTERNS, ph)))
