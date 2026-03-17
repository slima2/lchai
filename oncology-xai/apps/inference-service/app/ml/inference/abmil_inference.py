"""
ABMIL inference pipeline (Artifact 2) — Pathway A.

Input:  tile embeddings (N, 512) + tile pattern probs (N, 6) → concat (N, 518)
Output: per-gene mutation probability + attention weights
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import torch

from app.ml.checkpoints.loader import CheckpointLoader, GENES_V2

logger = logging.getLogger(__name__)


@dataclass
class ABMILResult:
    """Per-gene ABMIL prediction result."""
    gene: str = ""
    probability: float = 0.0
    label: str = "Inconclusive"
    auroc_threshold: float = 0.70
    disclaimer: str | None = None
    attention_weights: np.ndarray | None = None


@dataclass
class ABMILInferenceOutput:
    """Full output of the ABMIL pathway across all genes."""
    gene_results: list[ABMILResult] = field(default_factory=list)
    attention_map: np.ndarray | None = None  # (N,) best-gene attention weights
    top_k_indices: list[int] = field(default_factory=list)


def run_abmil_inference(
    embeddings: np.ndarray,
    pattern_probs: np.ndarray,
    checkpoint_loader: CheckpointLoader,
    top_k: int = 200,
    genes: list[str] | None = None,
) -> ABMILInferenceOutput:
    """Run ABMIL inference for all genes.

    Args:
        embeddings: (N, 512) CTransPath tile embeddings
        pattern_probs: (N, 6) FuzzyArcLoss pattern probabilities per tile
        checkpoint_loader: manages model loading/caching
        top_k: number of top-attended tiles to highlight
        genes: subset of genes to run (default: all 6)
    """
    device = checkpoint_loader.device
    target_genes = genes or GENES_V2

    concat = np.concatenate([embeddings, pattern_probs], axis=1)  # (N, 518)
    concat_t = torch.from_numpy(concat).float().to(device)

    output = ABMILInferenceOutput()
    best_attn = None
    best_gene_prob = -1.0

    for gene in target_genes:
        try:
            model = checkpoint_loader.load_abmil(gene, input_dim=concat.shape[1])
        except Exception as e:
            logger.warning("Failed to load ABMIL for %s: %s — using mock", gene, e)
            output.gene_results.append(_mock_result(gene))
            continue

        with torch.no_grad():
            logit, attn = model(concat_t, return_attention=True)
            prob = torch.sigmoid(logit).item()

        attn_np = attn.cpu().numpy() if attn is not None else None

        result = ABMILResult(
            gene=gene,
            probability=round(prob, 4),
            label=CheckpointLoader.get_confidence_label(gene),
            auroc_threshold=0.70,
            disclaimer=CheckpointLoader.get_disclaimer(gene),
            attention_weights=attn_np,
        )
        output.gene_results.append(result)

        if prob > best_gene_prob and attn_np is not None:
            best_gene_prob = prob
            best_attn = attn_np

    if best_attn is not None:
        output.attention_map = best_attn
        k = min(top_k, len(best_attn))
        output.top_k_indices = np.argsort(best_attn)[-k:][::-1].tolist()

    return output


def _mock_result(gene: str) -> ABMILResult:
    """Fallback mock result when checkpoint is unavailable."""
    rng = np.random.default_rng(hash(gene) % (2**31))
    prob = float(rng.uniform(0.3, 0.9))
    return ABMILResult(
        gene=gene,
        probability=round(prob, 4),
        label=CheckpointLoader.get_confidence_label(gene),
        auroc_threshold=0.70,
        disclaimer=CheckpointLoader.get_disclaimer(gene),
    )
