"""
CTransPath Swin Tiny backbone with ConvStem + Projection Head.

Architecture (from thesis):
  ConvStem(4ch → 96) → Swin Tiny (96 → 768) → ProjectionHead(768 → 512)

The backbone takes 4-channel input (RGB + binary mask) at 224×224.
Output: 512-d embedding per tile.

Checkpoint: `ctranspath.pth` — pretrained CTransPath weights (Wang et al., 2022)
            `best_fuzzyarcloss_v2.pth` — fine-tuned backbone + projection + classifier
"""

from __future__ import annotations

import logging
import os
from typing import Any

import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class ConvStem(nn.Module):
    """CTransPath's ConvStem patch embedding (replaces standard linear patch embed)."""

    def __init__(self, img_size: int = 224, patch_size: int = 4, in_chans: int = 3, embed_dim: int = 96):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.grid_size = (img_size // patch_size, img_size // patch_size)
        self.num_patches = self.grid_size[0] * self.grid_size[1]

        stem_dim1 = embed_dim // 8  # 12
        stem_dim2 = embed_dim // 4  # 24

        self.proj = nn.Sequential(
            nn.Conv2d(in_chans, stem_dim1, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(stem_dim1),
            nn.GELU(),
            nn.Conv2d(stem_dim1, stem_dim2, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(stem_dim2),
            nn.GELU(),
            nn.Conv2d(stem_dim2, embed_dim, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(embed_dim),
        )
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)
        x = x.permute(0, 2, 3, 1)
        x = self.norm(x)
        return x


class CTransPathBackbone(nn.Module):
    """CTransPath: Swin Tiny with ConvStem patch embedding.

    Input:  (B, 4, 224, 224) — RGB + mask channel
    Output: (B, 768)
    """

    def __init__(self, checkpoint_path: str | None = None, in_chans: int = 4):
        super().__init__()
        try:
            import timm
        except ImportError:
            raise ImportError("timm is required for CTransPath backbone")

        self.model = timm.create_model(
            "swin_tiny_patch4_window7_224",
            pretrained=False,
            num_classes=0,
        )

        embed_dim = 96
        self.model.patch_embed = ConvStem(
            img_size=224, patch_size=4, in_chans=in_chans, embed_dim=embed_dim
        )

        self.out_features = self.model.num_features  # 768

        if checkpoint_path and os.path.exists(checkpoint_path):
            self._load_checkpoint(checkpoint_path)
            logger.info("CTransPath backbone loaded from %s (out_features=%d)", checkpoint_path, self.out_features)

    def _load_checkpoint(self, checkpoint_path: str):
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)

        if isinstance(checkpoint, dict):
            state_dict = checkpoint.get("model", checkpoint.get("state_dict", checkpoint))
        else:
            state_dict = checkpoint

        remapped = {}
        for key, value in state_dict.items():
            if key.startswith("head.") or key.startswith("fc."):
                continue
            if "attn_mask" in key or "relative_position_index" in key:
                continue
            new_key = key
            if ".downsample." in key:
                for i in range(3):
                    if f"layers.{i}.downsample." in key:
                        new_key = key.replace(f"layers.{i}.downsample.", f"layers.{i+1}.downsample.")
                        break
            remapped[new_key] = value

        model_state = self.model.state_dict()
        filtered = {
            k: v for k, v in remapped.items()
            if k in model_state and v.shape == model_state[k].shape
        }

        if len(filtered) >= 100:
            self.model.load_state_dict(filtered, strict=False)
            logger.info("CTransPath: loaded %d/%d keys", len(filtered), len(model_state))
        else:
            logger.warning("CTransPath: only %d matching keys — checkpoint may be incompatible", len(filtered))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x)


class CTransPathPipeline(nn.Module):
    """Full CTransPath pipeline: Backbone(4ch→768) + ProjectionHead(768→512).

    This is the model saved in `best_fuzzyarcloss_v2.pth` under the 'model' key.
    The checkpoint stores nn.Sequential(CTransPathBackbone, ProjectionHead).
    """

    def __init__(
        self,
        ctranspath_pretrained: str | None = None,
        embed_dim: int = 512,
        in_chans: int = 4,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.backbone = CTransPathBackbone(ctranspath_pretrained, in_chans=in_chans)
        backbone_dim = self.backbone.out_features  # 768

        self.projection = nn.Sequential(
            nn.Linear(backbone_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.embed_dim = embed_dim

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """(B, 4, 224, 224) → (B, 512)"""
        features = self.backbone(x)  # (B, 768)
        return self.projection(features)  # (B, 512)

    @classmethod
    def from_finetuned(cls, checkpoint_path: str, device: str = "cpu") -> "CTransPathPipeline":
        """Load from best_fuzzyarcloss_v2.pth which has the finetuned backbone+projection."""
        ck = torch.load(checkpoint_path, map_location=device, weights_only=False)
        config = ck.get("config", {})
        embed_dim = config.get("EMBED_DIM", 512)
        in_chans = 4 if config.get("USE_MASK_AS_CHANNEL", True) else 3

        model = cls(ctranspath_pretrained=None, embed_dim=embed_dim, in_chans=in_chans)

        state_dict = ck.get("model", ck)
        remapped = {}
        for key, value in state_dict.items():
            new_key = key
            if key.startswith("0."):
                new_key = "backbone." + key[2:]
            elif key.startswith("1."):
                new_key = "projection." + key[2:]
            remapped[new_key] = value

        missing, unexpected = model.load_state_dict(remapped, strict=False)
        logger.info(
            "CTransPathPipeline loaded: %d params, missing=%d, unexpected=%d",
            len(remapped), len(missing), len(unexpected),
        )
        model.eval().to(device)
        return model

    @staticmethod
    def load_classifier_weights(checkpoint_path: str, device: str = "cpu") -> dict[str, Any]:
        """Load FuzzyArcLoss V2 classifier weights + config from checkpoint."""
        ck = torch.load(checkpoint_path, map_location=device, weights_only=False)
        config = ck.get("config", {})
        loss_fn = ck.get("loss_fn", {})
        id2label = {int(k): v for k, v in ck.get("id2label", {0: "micropapillary", 1: "cribriform", 2: "papillary", 3: "lepidic", 4: "solid", 5: "acinar"}).items()}

        head_weight = loss_fn.get("head.weight", loss_fn.get("weight"))
        if head_weight is None:
            raise ValueError("No classifier weight found in checkpoint")

        return {
            "head_weight": head_weight.to(device),
            "id2label": id2label,
            "s_scale": float(config.get("S_SCALE", 30.0)),
            "embed_dim": int(config.get("EMBED_DIM", 512)),
            "img_size": int(config.get("IMG_SIZE", 224)),
            "num_classes": head_weight.shape[0],
        }
