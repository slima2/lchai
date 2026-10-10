#!/usr/bin/env python3
"""
FC-MIL exactly as written in the thesis (Sections 4.4.2, 4.4.4, 5.5).
=====================================================================

This module is an EXPOSITORY implementation: it shows what the Fuzzy Choquet MIL
aggregator looks like when every equation of Chapters 4 and 5 is followed literally.
It is NOT the module that produced the archived results in logs/mutation_5fold_results
(that is `FuzzyChoquetMIL` in ../artefact2_mutation_abmil/pattern_informed_mil_benchmark.py;
the differences are listed in ../../provenance/README.md, item D10).

What is implemented here, equation by equation
----------------------------------------------
Eq. 4.24  g(A) = sum_{k in A} phi_k + sum_{{j,k} subset A} I_jk        (2-additive measure)
Eq. 4.25  phi_k = softmax(psi)_k                                       (Shapley weights >= 0, sum 1)
Eq. 4.26  R_int = lambda_I * sum_{j<k} |I_jk|,  lambda_I = 0.01        (L1 on the interactions)
Eq. 5.2   R_mono = lambda_M * sum_{A subset B} max(0, g(A) - g(B)),  lambda_M = 0.1,
          evaluated on 100 random subset pairs per step                (soft monotonicity)
Sec. 5.5  Choquet module: sort the slide-level 6-vector ascending, A_i = {sigma(i..6)},
          c_i = (x_sigma(i) - x_sigma(i-1)) * g(A_i), return the 6-vector c_s (Eq. 5.1);
          the scalar Choquet integral is 1^T c_s.
Eq. 4.21  z_attn = sum_i alpha_i Encoder(x_i), two-layer encoder 512 -> 256 (LayerNorm, ReLU, Dropout)
Eq. 4.18  gated attention V, U: 256 -> 128, w: 128 -> 1
Eq. 4.27  z_s = ReLU(W_proj [c_s || z_attn] + b_proj), W_proj in R^{256 x 262} (+ LayerNorm, Table 5.7)
Eq. 4.28  Y = sigmoid(w_g^T z_s + b_g)
Eq. 4.29  L = L_BCE + R_int + R_mono
Table 5.7 choquet_scale, learnable, initialised at 10.0

The Choquet pathway input is the slide-level mean membership vector p_bar_s = mean_i p_i
(Sec. 4.4.2, "C_g(p_bar_s)").

Run `python fuzzy_choquet_mil_as_specified.py` for a self-test (no data needed).
"""
from __future__ import annotations

import itertools
import torch
import torch.nn as nn
import torch.nn.functional as F

PATTERN_NAMES = ["micropapillary", "cribriform", "papillary", "lepidic", "solid", "acinar"]


class FuzzyMeasure2Additive(nn.Module):
    """2-additive fuzzy measure with softmax-normalised Shapley weights (Eq. 4.24-4.25)."""

    def __init__(self, n_criteria: int = 6):
        super().__init__()
        self.K = n_criteria
        self.psi = nn.Parameter(torch.zeros(n_criteria))                       # phi = softmax(psi) = 1/6 at init
        self.pairs = list(itertools.combinations(range(n_criteria), 2))        # 15 pairs, fixed order
        self.I = nn.Parameter(torch.zeros(len(self.pairs)))                    # interaction indices, init 0
        idx = torch.tensor(self.pairs)
        self.register_buffer("pair_i", idx[:, 0])
        self.register_buffer("pair_j", idx[:, 1])

    # -- parameters in their interpretable form -------------------------------------------
    def shapley(self) -> torch.Tensor:
        return torch.softmax(self.psi, dim=0)                                  # Eq. 4.25

    def interactions(self) -> torch.Tensor:
        return self.I

    def interaction_matrix(self) -> torch.Tensor:
        M = torch.zeros(self.K, self.K, device=self.I.device)
        M[self.pair_i, self.pair_j] = self.I
        return M + M.T

    def grabisch_shapley(self) -> torch.Tensor:
        """Shapley value of the measure in the sense of Grabisch & Roubens: phi_k + 1/2 sum_j I_jk.
        (The thesis calls phi_k itself the Shapley value; both are reported.)"""
        return self.shapley() + 0.5 * self.interaction_matrix().sum(1)

    # -- the set function -----------------------------------------------------------------
    def forward(self, mask: torch.Tensor) -> torch.Tensor:
        """g(A) for crisp subsets given as 0/1 masks of shape (..., K)  (Eq. 4.24)."""
        phi = self.shapley()
        singles = (mask * phi).sum(-1)
        pairs = (mask[..., self.pair_i] * mask[..., self.pair_j] * self.I).sum(-1)
        return singles + pairs

    # -- regularisers -----------------------------------------------------------------------
    def interaction_l1(self) -> torch.Tensor:
        return self.I.abs().sum()                                              # Eq. 4.26 (without lambda)

    def monotonicity_penalty(self, n_pairs: int = 100, generator: torch.Generator | None = None) -> torch.Tensor:
        """sum over sampled A strict-subset B of max(0, g(A) - g(B))   (Eq. 5.2, without lambda)."""
        dev = self.I.device
        B = (torch.rand(n_pairs, self.K, generator=generator, device=dev) < 0.5).float()
        B[B.sum(1) == 0, 0] = 1.0                                              # B non-empty
        drop = (torch.rand(n_pairs, self.K, generator=generator, device=dev) < 0.5).float() * B
        no_drop = drop.sum(1) == 0                                             # force A != B
        if no_drop.any():
            first = B[no_drop].argmax(1)
            drop[no_drop.nonzero(as_tuple=True)[0], first] = 1.0
        A = B - drop
        return F.relu(self(A) - self(B)).sum()

    @torch.no_grad()
    def is_monotone(self) -> bool:
        """Exact check over all 64 subsets (only pairs A = B \\ {k} need testing)."""
        masks = torch.tensor(list(itertools.product([0.0, 1.0], repeat=self.K)), device=self.I.device)
        g = self(masks)
        for m, gm in zip(masks, g):
            for k in range(self.K):
                if m[k] == 1:
                    sub = m.clone(); sub[k] = 0
                    if self(sub.unsqueeze(0))[0] > gm + 1e-7:
                        return False
        return True

    @torch.no_grad()
    def is_normalised(self) -> bool:
        """g(empty) = 0 holds by construction; g(N) = 1 + sum I_jk, so it holds iff sum I_jk = 0."""
        return bool(abs(float(self.I.sum())) < 1e-6)


def choquet_terms(x: torch.Tensor, measure: FuzzyMeasure2Additive) -> torch.Tensor:
    """Rank-ordered Choquet differential terms c_s (Sec. 5.5, Eq. 5.1).

    x: (K,) slide-level membership vector. Returns c of shape (K,) with
    c_i = (x_sigma(i) - x_sigma(i-1)) * g(A_i), A_i = {sigma(i), ..., sigma(K)}, x_sigma(0) = 0.
    The classical Choquet integral is c.sum().
    """
    K = x.shape[0]
    xs, order = torch.sort(x)                                                  # ascending, differentiable in values
    prev = torch.cat([xs.new_zeros(1), xs[:-1]])
    masks = torch.zeros(K, K, device=x.device)
    for i in range(K):
        masks[i, order[i:]] = 1.0                                              # A_i = indices with x >= x_sigma(i)
    return (xs - prev) * measure(masks)


class FuzzyChoquetMILAsSpecified(nn.Module):
    """Dual-pathway FC-MIL of Fig. 4.9 with the measure, integral and merge of the text."""

    def __init__(self, embed_dim: int = 512, n_patterns: int = 6, hidden: int = 256,
                 attn_dim: int = 128, dropout: float = 0.25, choquet_scale_init: float = 10.0,
                 lambda_I: float = 0.01, lambda_M: float = 0.1, mono_pairs: int = 100):
        super().__init__()
        self.measure = FuzzyMeasure2Additive(n_patterns)
        self.encoder = nn.Sequential(                                          # Eq. 4.21: two layers
            nn.Linear(embed_dim, hidden), nn.LayerNorm(hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden), nn.LayerNorm(hidden), nn.ReLU(), nn.Dropout(dropout),
        )
        self.V = nn.Linear(hidden, attn_dim)                                   # Eq. 4.18
        self.U = nn.Linear(hidden, attn_dim)
        self.w = nn.Linear(attn_dim, 1, bias=False)
        self.proj = nn.Sequential(                                             # Eq. 4.27 (+ LayerNorm, Table 5.7)
            nn.Linear(n_patterns + hidden, hidden), nn.LayerNorm(hidden), nn.ReLU(), nn.Dropout(dropout))
        self.classifier = nn.Linear(hidden, 1)                                 # Eq. 4.28
        self.choquet_scale = nn.Parameter(torch.tensor(float(choquet_scale_init)))
        self.lambda_I, self.lambda_M, self.mono_pairs = lambda_I, lambda_M, mono_pairs

    def forward(self, inputs, return_attention: bool = False):
        H, probs = inputs                                                      # H: (N, 512), probs: (N, 6)
        h = self.encoder(H)
        a = torch.softmax(self.w(torch.tanh(self.V(h)) * torch.sigmoid(self.U(h))), dim=0)
        z_attn = (a * h).sum(0)
        p_bar = probs.mean(0)                                                  # slide-level membership vector
        c_s = choquet_terms(p_bar, self.measure) * self.choquet_scale
        z = self.proj(torch.cat([c_s, z_attn]))
        logit = self.classifier(z).squeeze(-1)
        return (logit, a.squeeze(1)) if return_attention else (logit, None)

    def regularisation(self) -> torch.Tensor:
        """R_int + R_mono of Eq. 4.29."""
        return self.lambda_I * self.measure.interaction_l1() + self.lambda_M * self.measure.monotonicity_penalty(self.mono_pairs)

    @torch.no_grad()
    def measure_report(self) -> dict:
        phi = self.measure.shapley().cpu().tolist()
        gsh = self.measure.grabisch_shapley().cpu().tolist()
        I = self.measure.interactions().cpu().tolist()
        return {
            "fuzzy_shapley_values": dict(zip(PATTERN_NAMES, phi)),            # phi_k of Eq. 4.25
            "shapley_grabisch": dict(zip(PATTERN_NAMES, gsh)),
            "fuzzy_interactions": {f"{PATTERN_NAMES[i]}×{PATTERN_NAMES[j]}": v for (i, j), v in zip(self.measure.pairs, I)},
            "measure_monotone": self.measure.is_monotone(),
            "measure_normalised": self.measure.is_normalised(),
            "choquet_scale": float(self.choquet_scale),
        }


if __name__ == "__main__":
    torch.manual_seed(0)
    m = FuzzyMeasure2Additive()
    x = torch.rand(6)
    # 1. additive measure (I = 0): Choquet integral == weighted mean with Shapley weights
    assert torch.allclose(choquet_terms(x, m).sum(), (m.shapley() * x).sum(), atol=1e-6)
    # 2. at init the measure is monotone and normalised, penalty is zero
    assert m.is_monotone() and m.is_normalised() and float(m.monotonicity_penalty().detach()) == 0.0
    # 3. a strongly negative interaction breaks monotonicity and the penalty sees it
    with torch.no_grad():
        m.I[0] = -0.5
    assert not m.is_monotone() and float(m.monotonicity_penalty(1000).detach()) > 0
    # 4. the full model runs and its regularisation is differentiable
    net = FuzzyChoquetMILAsSpecified()
    H, P = torch.randn(300, 512), torch.softmax(torch.randn(300, 6), 1)
    logit, _ = net((H, P))
    loss = F.binary_cross_entropy_with_logits(logit.unsqueeze(0), torch.ones(1)) + net.regularisation()
    loss.backward()
    assert net.measure.I.grad is not None and net.measure.psi.grad is not None
    print("self-test passed;", {k: v for k, v in net.measure_report().items() if k.startswith("measure")})
