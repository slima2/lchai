"""
Pattern-Informed ABMIL (Artifact 2).

Gated attention MIL on concatenated embeddings (512-d) + pattern probs (6-d) = 518-d.
One model per gene, trained with 5-fold stratified CV on TCGA-LUAD.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class GatedAttention(nn.Module):
    """Gated attention mechanism (Ilse et al., 2018) with tanh-sigmoid gating."""

    def __init__(self, input_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.V = nn.Linear(input_dim, hidden_dim)
        self.U = nn.Linear(input_dim, hidden_dim)
        self.w = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, H: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        A = self.w(torch.tanh(self.V(H)) * torch.sigmoid(self.U(H)))
        A = torch.softmax(A, dim=0)
        return (A * H).sum(dim=0), A.squeeze(1)


class ABMIL(nn.Module):
    """Attention-Based Multiple Instance Learning.

    Architecture:
        Linear(input_dim → hidden) → LayerNorm → ReLU → Dropout
        → GatedAttention(hidden → attn_dim)
        → Linear(hidden → 1)      # binary logit per gene
    """

    def __init__(
        self,
        input_dim: int = 518,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.attention = GatedAttention(hidden_dim, attn_dim)
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(
        self, H: torch.Tensor, return_attention: bool = False
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        h = self.encoder(H)
        z, a = self.attention(h)
        logit = self.classifier(z).squeeze(-1)
        return (logit, a) if return_attention else (logit, None)
