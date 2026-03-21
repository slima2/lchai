"""
Checkpoint loader for v2 per-gene, per-fold ABMIL and Fuzzy Choquet models.

Checkpoint naming convention (from thesis training):
  ABMIL:   ckpt_proposed_abmil_concat_{GENE}_fold{K}.pth
  Choquet:  ckpt_proposed_fuzzy_choquet_{GENE}_fold{K}.pth

Best fold per gene (from K-fold AUROC calibration):
  TP53: fold 2, EGFR: fold 4, KRAS: fold 3,
  STK11: fold 3, KEAP1: fold 1, RBM10: fold 4
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import torch

from app.ml.models.abmil import ABMIL
from app.ml.models.choquet_mil import FuzzyChoquetMIL

logger = logging.getLogger(__name__)

GENES_V2 = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

BEST_FOLD: dict[str, int] = {
    "TP53": 2,
    "EGFR": 4,
    "KRAS": 3,
    "STK11": 3,
    "KEAP1": 1,
    "RBM10": 4,
}

CONCLUSIVE_GENES = {"TP53", "EGFR"}
INCONCLUSIVE_GENES = {"KRAS", "STK11", "KEAP1", "RBM10"}

AUROC_THRESHOLD = 0.70

# Best method per gene (from thesis Table 6.7, Finding 2)
# "baseline2" = emb-only ABMIL (512-d)
# "proposed"  = pattern-informed ABMIL concat (518-d)
# "choquet"   = Fuzzy Choquet MIL
BEST_METHOD: dict[str, str] = {
    "TP53":  "baseline2",   # Visual features sufficient
    "EGFR":  "baseline2",   # Visual features sufficient
    "STK11": "proposed",    # Patterns add signal
    "KEAP1": "proposed",    # Patterns add signal over B2
    "KRAS":  "choquet",     # Fuzzy aggregation captures signal
    "RBM10": "choquet",     # Choquet best despite low prevalence
}

BEST_METHOD_LABEL: dict[str, str] = {
    "baseline2": "B2 (embeddings)",
    "proposed":  "P (proposed concat)",
    "choquet":   "FC (Fuzzy Choquet)",
}

PROPOSED_AUROC: dict[str, float] = {
    "TP53": 0.8024, "EGFR": 0.7504, "KRAS": 0.6800,
    "STK11": 0.6962, "KEAP1": 0.6218, "RBM10": 0.7371,
}
BASELINE2_AUROC: dict[str, float] = {
    "TP53": 0.7929, "EGFR": 0.7302, "KRAS": 0.7148,
    "STK11": 0.6708, "KEAP1": 0.6600, "RBM10": 0.6930,
}
BASELINE3_AUROC: dict[str, float] = {
    "TP53": 0.5518, "EGFR": 0.6806, "KRAS": 0.6155,
    "STK11": 0.5419, "KEAP1": 0.5361, "RBM10": 0.7644,
}
CHOQUET_AUROC: dict[str, float] = {
    "TP53": 0.7835, "EGFR": 0.7171, "KRAS": 0.6698,
    "STK11": 0.5287, "KEAP1": 0.6760, "RBM10": 0.7082,
}

_CACHE: dict[str, Any] = {}


class CheckpointLoader:
    """Manages loading and caching of v2 model checkpoints."""

    def __init__(self, checkpoint_dir: str, device: str = "cpu"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.device = device

    def _cache_key(self, model_type: str, gene: str) -> str:
        return f"{model_type}_{gene}_{self.device}"

    def load_abmil(
        self,
        gene: str,
        input_dim: int = 518,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ) -> ABMIL:
        """Load best-fold ABMIL checkpoint for a gene."""
        key = self._cache_key("abmil", gene)
        if key in _CACHE:
            return _CACHE[key]

        fold = BEST_FOLD.get(gene)
        if fold is None:
            raise ValueError(f"No best fold defined for gene {gene}")

        fname = f"ckpt_proposed_abmil_concat_{gene}_fold{fold}.pth"
        ckpt_path = self.checkpoint_dir / fname

        model = ABMIL(input_dim, hidden_dim, attn_dim, dropout)

        if ckpt_path.exists():
            ckpt = torch.load(str(ckpt_path), map_location=self.device, weights_only=False)
            state = ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt))
            model.load_state_dict(state, strict=False)
            logger.info("Loaded ABMIL checkpoint %s for %s (fold %d)", fname, gene, fold)
        else:
            logger.warning("ABMIL checkpoint not found: %s — using random init", ckpt_path)

        model.eval().to(self.device)
        _CACHE[key] = model
        return model

    def load_baseline2(
        self,
        gene: str,
        input_dim: int = 512,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ) -> ABMIL:
        """Load baseline2 ABMIL (embeddings-only, 512-d input)."""
        key = self._cache_key("baseline2", gene)
        if key in _CACHE:
            return _CACHE[key]

        fold = BEST_FOLD.get(gene, 0)
        fname = f"ckpt_baseline2_abmil_embeddings_{gene}_fold{fold}.pth"
        ckpt_path = self.checkpoint_dir / fname

        model = ABMIL(input_dim, hidden_dim, attn_dim, dropout)
        if ckpt_path.exists():
            ckpt = torch.load(str(ckpt_path), map_location=self.device, weights_only=False)
            state = ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt))
            model.load_state_dict(state, strict=False)
            logger.info("Loaded baseline2 (emb-only) %s for %s", fname, gene)
        else:
            logger.warning("Baseline2 checkpoint not found: %s", ckpt_path)

        model.eval().to(self.device)
        _CACHE[key] = model
        return model

    def load_baseline3(
        self,
        gene: str,
        input_dim: int = 6,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ) -> ABMIL:
        """Load baseline3 ABMIL (patterns-only, 6-d input)."""
        key = self._cache_key("baseline3", gene)
        if key in _CACHE:
            return _CACHE[key]

        fold = BEST_FOLD.get(gene, 0)
        fname = f"ckpt_baseline3_abmil_patterns_{gene}_fold{fold}.pth"
        ckpt_path = self.checkpoint_dir / fname

        model = ABMIL(input_dim, hidden_dim, attn_dim, dropout)
        if ckpt_path.exists():
            ckpt = torch.load(str(ckpt_path), map_location=self.device, weights_only=False)
            state = ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt))
            model.load_state_dict(state, strict=False)
            logger.info("Loaded baseline3 (pat-only) %s for %s", fname, gene)
        else:
            logger.warning("Baseline3 checkpoint not found: %s", ckpt_path)

        model.eval().to(self.device)
        _CACHE[key] = model
        return model

    def load_choquet(
        self,
        gene: str,
        embed_dim: int = 512,
        n_patterns: int = 6,
        hidden_dim: int = 256,
        attn_dim: int = 128,
        dropout: float = 0.25,
    ) -> FuzzyChoquetMIL:
        """Load best-fold Fuzzy Choquet checkpoint for a gene."""
        key = self._cache_key("choquet", gene)
        if key in _CACHE:
            return _CACHE[key]

        fold = BEST_FOLD.get(gene)
        if fold is None:
            raise ValueError(f"No best fold defined for gene {gene}")

        fname = f"ckpt_proposed_fuzzy_choquet_{gene}_fold{fold}.pth"
        ckpt_path = self.checkpoint_dir / fname

        model = FuzzyChoquetMIL(embed_dim, n_patterns, hidden_dim, attn_dim, dropout)

        if ckpt_path.exists():
            ckpt = torch.load(str(ckpt_path), map_location=self.device, weights_only=False)
            state = ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt))
            model.load_state_dict(state, strict=False)
            logger.info("Loaded Choquet checkpoint %s for %s (fold %d)", fname, gene, fold)
        else:
            logger.warning("Choquet checkpoint not found: %s — using random init", ckpt_path)

        model.eval().to(self.device)
        _CACHE[key] = model
        return model

    def get_checkpoint_status(self) -> dict[str, dict[str, Any]]:
        """Return status of all expected checkpoints."""
        status: dict[str, dict[str, Any]] = {}
        for gene in GENES_V2:
            fold = BEST_FOLD[gene]
            abmil_path = self.checkpoint_dir / f"ckpt_proposed_abmil_concat_{gene}_fold{fold}.pth"
            choquet_path = self.checkpoint_dir / f"ckpt_proposed_fuzzy_choquet_{gene}_fold{fold}.pth"
            status[gene] = {
                "best_fold": fold,
                "abmil_loaded": self._cache_key("abmil", gene) in _CACHE,
                "abmil_exists": abmil_path.exists(),
                "abmil_path": str(abmil_path),
                "choquet_loaded": self._cache_key("choquet", gene) in _CACHE,
                "choquet_exists": choquet_path.exists(),
                "choquet_path": str(choquet_path),
                "conclusive": gene in CONCLUSIVE_GENES,
            }
        return status

    @staticmethod
    def is_conclusive(gene: str) -> bool:
        return gene in CONCLUSIVE_GENES

    @staticmethod
    def get_confidence_label(gene: str) -> str:
        return "Conclusive" if gene in CONCLUSIVE_GENES else "Inconclusive"

    @staticmethod
    def get_disclaimer(gene: str) -> str | None:
        if gene in INCONCLUSIVE_GENES:
            return (
                "Molecular testing recommended. This gene cannot be reliably "
                "predicted from histological features alone."
            )
        return None
