"""
2-Additive Fuzzy Measure (Artifact 3 — component).

Parameterises singleton Shapley values (6 params) plus pairwise
interaction indices (C(6,2) = 15 params) → 21 learnable params total.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class FuzzyMeasure(nn.Module):
    """Learnable 2-additive fuzzy measure over `n_patterns` sources.

    Stores:
        v  — singleton importance weights (n_patterns,)
        v2 — pairwise interaction weights (n_patterns, n_patterns), upper-triangle used
    """

    def __init__(self, n_patterns: int = 6):
        super().__init__()
        self.K = n_patterns
        self.v = nn.Parameter(torch.ones(n_patterns) / n_patterns)
        self.v2 = nn.Parameter(torch.zeros(n_patterns, n_patterns))

    def measure(self, subset_mask: torch.Tensor) -> torch.Tensor:
        """Evaluate μ(S) for a soft subset mask ∈ [0,1]^K."""
        singleton = (subset_mask * torch.sigmoid(self.v)).sum(dim=-1)
        v2_upper = torch.triu(self.v2, diagonal=1)
        outer = subset_mask.unsqueeze(-1) * subset_mask.unsqueeze(-2)
        interaction = (outer * v2_upper).sum(dim=(-1, -2))
        return torch.sigmoid(singleton + interaction)

    def shapley_values(self) -> dict[str, float]:
        """Extract normalised Shapley values from singleton params."""
        with torch.no_grad():
            sv = torch.sigmoid(self.v).cpu().numpy()
            total = sv.sum()
            return {str(i): float(sv[i] / total) if total > 0 else 0.0 for i in range(self.K)}

    def interaction_indices(self) -> dict[str, float]:
        """Extract upper-triangle interaction weights."""
        with torch.no_grad():
            v2 = torch.triu(self.v2, diagonal=1).cpu().numpy()
            result = {}
            for i in range(self.K):
                for j in range(i + 1, self.K):
                    result[f"{i}_{j}"] = float(v2[i, j])
            return result
