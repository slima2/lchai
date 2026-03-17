"""
Fuzzy Choquet MIL (Artifact 3).

Combines fuzzy Choquet integral aggregation over pattern memberships
with attention-weighted embedding aggregation. Outputs mutation logit
plus interpretable Shapley values and interaction indices from the
learnable fuzzy measure.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from app.ml.models.fuzzy_measure import FuzzyMeasure


class FuzzyChoquetAggregation(nn.Module):
    """Dual aggregation: Choquet integral over patterns + gated attention over embeddings."""

    def __init__(
        self,
        embed_dim: int = 512,
        n_patterns: int = 6,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ):
        super().__init__()
        self.K = n_patterns
        self.fuzzy_measure = FuzzyMeasure(n_patterns)

        self.encoder = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.V_attn = nn.Linear(hidden_dim, attn_dim)
        self.U_attn = nn.Linear(hidden_dim, attn_dim)
        self.w_attn = nn.Linear(attn_dim, 1, bias=False)

        self.proj = nn.Sequential(
            nn.Linear(n_patterns + hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.choquet_scale = nn.Parameter(torch.tensor(10.0))

    def choquet_integral(self, pattern_probs: torch.Tensor) -> torch.Tensor:
        """Discrete Choquet integral using the learnable fuzzy measure."""
        N, K = pattern_probs.shape
        if N > 512:
            idx = torch.randperm(N, device=pattern_probs.device)[:512]
            pattern_probs = pattern_probs[idx]
            N = 512

        choquet_vals = torch.zeros(K, device=pattern_probs.device)
        for k in range(K):
            order = torch.argsort(pattern_probs[:, k], descending=True)
            sorted_p = pattern_probs[order]
            cumsum = torch.cumsum(sorted_p, dim=0)
            ranks = torch.arange(1, N + 1, device=pattern_probs.device).float().unsqueeze(1)
            cum_mean = cumsum / ranks
            mu_i = self.fuzzy_measure.measure(cum_mean)
            mu_i1 = torch.cat([mu_i[1:], torch.zeros(1, device=pattern_probs.device)])
            choquet_vals[k] = (sorted_p[:, k] * (mu_i - mu_i1)).sum()
        return choquet_vals

    def forward(
        self, H: torch.Tensor, probs: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.encoder(H)
        A = self.w_attn(torch.tanh(self.V_attn(h)) * torch.sigmoid(self.U_attn(h)))
        A = torch.softmax(A, dim=0)
        z_attn = (A * h).sum(dim=0)
        cv = self.choquet_integral(probs) * self.choquet_scale
        z = self.proj(torch.cat([cv, z_attn]))
        return z, A.squeeze(1)


class FuzzyChoquetMIL(nn.Module):
    """Full Fuzzy Choquet MIL: aggregation → classifier → mutation logit."""

    def __init__(
        self,
        embed_dim: int = 512,
        n_patterns: int = 6,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ):
        super().__init__()
        self.aggregator = FuzzyChoquetAggregation(
            embed_dim, n_patterns, hidden_dim, attn_dim, dropout
        )
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        inputs: tuple[torch.Tensor, torch.Tensor],
        return_attention: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        H, probs = inputs
        z, a = self.aggregator(H, probs)
        logit = self.classifier(z).squeeze(-1)
        return (logit, a) if return_attention else (logit, None)
