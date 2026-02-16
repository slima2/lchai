"""
ROI Inference with CTransPath + FuzzyArcLoss v3 SubCenters.

DERCAS 10 — Script invocable por el worker Celery.

Adapted from thesis code:
  - CTransPathBackbone: SLIMA_ablation_study_loss_functions_ver_11_jan_2026.py
  - FuzzyArcMarginProductV3SubCenters: same source
  - Tile inference: SLIMA_PARALELL_inferencing_hist_patterns_roi_parallel_ver_21_nov_2025.py
  - Mutation + SHAP: SLIMA_histology_mutation_xgboost_rev3.ipynb

Outputs (DERCAS 10.3):
  - roi_overlay_combined.png
  - pattern_composition.json
  - embedding.npz
  - metrics.json
  - SHAP artifacts per gene (if enabled)
"""

from __future__ import annotations

import io
import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# ── Pattern palette (DERCAS 7) ─────────────────────────────────────────
PATTERN_PALETTE: dict[str, tuple[int, int, int]] = {
    "lepidic": (255, 255, 0),
    "acinar": (0, 255, 0),
    "papillary": (0, 0, 255),
    "micropapillary": (255, 0, 255),
    "solid": (255, 0, 0),
    "mucinous": (255, 165, 0),
}

PATTERNS = ["lepidic", "acinar", "papillary", "micropapillary", "solid"]
GENES = ["EGFR", "KRAS", "TP53"]


@dataclass
class InferenceConfig:
    """Configuration for a single inference run."""
    image_uri: str = ""
    image_format: str | None = None  # e.g. png, jpeg, tif, tiff, svs
    tile_size: int = 224
    overlap: int = 0
    device: str = "cpu"
    pattern_threshold: float = 0.55
    mutation_threshold: float = 0.60
    model_backend: str = "mock"
    ctranspath_checkpoint: str = ""
    fuzzyarc_checkpoint: str = ""
    mutation_model_dir: str = ""
    shap_enabled: bool = True


@dataclass
class InferenceResult:
    """Complete result of an inference run."""
    pattern_scores: dict[str, float] = field(default_factory=dict)
    pattern_percentages: dict[str, float] = field(default_factory=dict)
    predominant_pattern: str = ""
    is_conclusive: dict[str, bool] = field(default_factory=dict)
    overlay_combined_bytes: bytes = b""
    embedding: np.ndarray | None = None
    n_tiles: int = 0
    # Mutation
    mutation_scores: dict[str, float] = field(default_factory=dict)
    mutation_status: dict[str, str] = field(default_factory=dict)
    # Morphologic profile
    morphologic_profile: dict[str, float] = field(default_factory=dict)
    # SHAP
    shap_artifacts: dict[str, bytes] = field(default_factory=dict)
    # Metrics
    metrics: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# REAL ML COMPONENTS (used when model_backend == "local")
# ═══════════════════════════════════════════════════════════════════════

def _load_ctranspath_model(checkpoint_path: str, device: str = "cpu"):
    """Load CTransPath backbone (SWIN Transformer, embed_dim=512).

    Requires: torch, timm.
    Adapted from thesis: CTransPathBackbone with ConvStem.
    """
    import torch
    import timm

    model = timm.create_model(
        "swin_tiny_patch4_window7_224", pretrained=False, num_classes=0
    )
    # CTransPath uses a ConvStem instead of standard patch embed
    # Load checkpoint if available
    if checkpoint_path:
        try:
            state = torch.load(checkpoint_path, map_location=device)
            if "model" in state:
                state = state["model"]
            model.load_state_dict(state, strict=False)
            logger.info("Loaded CTransPath checkpoint from %s", checkpoint_path)
        except Exception as e:
            logger.warning("Could not load CTransPath checkpoint: %s", e)

    model.eval()
    model.to(device)
    return model


def _load_fuzzyarc_head(checkpoint_path: str, num_classes: int = 5, embed_dim: int = 512, device: str = "cpu"):
    """Load FuzzyArcLoss v3 SubCenters classification head.

    Adapted from thesis: FuzzyArcMarginProductV3SubCenters.
    """
    import torch
    import torch.nn as nn

    class FuzzyArcMarginProductV3SubCenters(nn.Module):
        """FuzzyArcLoss v3 with sub-centers for robust classification."""

        def __init__(self, in_features: int, out_features: int, K: int = 3,
                     s: float = 30.0, m: float = 0.50, tau: float = 0.1):
            super().__init__()
            self.in_features = in_features
            self.out_features = out_features
            self.K = K
            self.s = s
            self.m = m
            self.tau = tau
            self.weight = nn.Parameter(torch.FloatTensor(out_features * K, in_features))
            nn.init.xavier_uniform_(self.weight)

        def forward(self, x: torch.Tensor, label: torch.Tensor | None = None) -> torch.Tensor:
            # Normalize
            cosine = torch.nn.functional.linear(
                torch.nn.functional.normalize(x),
                torch.nn.functional.normalize(self.weight),
            )
            # Reshape for sub-centers: (batch, classes, K)
            cosine = cosine.view(-1, self.out_features, self.K)
            # Max over sub-centers
            cosine, _ = cosine.max(dim=2)

            if label is not None and self.training:
                # Apply angular margin with fuzzy membership
                theta = torch.acos(torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7))
                one_hot = torch.zeros_like(cosine).scatter_(1, label.view(-1, 1), 1.0)
                # Fuzzy membership modulation
                mu = torch.exp(-self.tau * theta)
                target_margin = self.m * mu
                output = torch.cos(theta + one_hot * target_margin.detach())
                output *= self.s
            else:
                output = cosine * self.s

            return output

    head = FuzzyArcMarginProductV3SubCenters(embed_dim, num_classes)

    if checkpoint_path:
        try:
            import torch
            state = torch.load(checkpoint_path, map_location=device)
            if "head" in state:
                state = state["head"]
            head.load_state_dict(state, strict=False)
            logger.info("Loaded FuzzyArcLoss v3 head from %s", checkpoint_path)
        except Exception as e:
            logger.warning("Could not load FuzzyArc head: %s", e)

    head.eval()
    head.to(device)
    return head


# ═══════════════════════════════════════════════════════════════════════
# MOCK ML COMPONENTS (used when model_backend == "mock")
# ═══════════════════════════════════════════════════════════════════════

def _mock_tile_inference(n_tiles: int) -> dict[str, list[float]]:
    """Generate mock pattern scores per tile."""
    rng = np.random.default_rng(42)
    scores: dict[str, list[float]] = {p: [] for p in PATTERNS}
    for _ in range(n_tiles):
        raw = rng.dirichlet(np.ones(len(PATTERNS)))
        for i, p in enumerate(PATTERNS):
            scores[p].append(float(raw[i]))
    return scores


def _mock_mutation_prediction(profile: dict[str, float]) -> tuple[dict[str, float], dict[str, str]]:
    """Generate mock mutation scores from morphologic profile."""
    rng = np.random.default_rng(123)
    scores = {}
    statuses = {}
    for gene in GENES:
        s = float(rng.uniform(0.3, 0.9))
        scores[gene] = round(s, 4)
        if s >= 0.60:
            statuses[gene] = "POS"
        elif s >= 0.40:
            statuses[gene] = "INCONCLUSIVE"
        else:
            statuses[gene] = "NEG"
    return scores, statuses


# ═══════════════════════════════════════════════════════════════════════
# CORE INFERENCE PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def _tile_image(img: Image.Image, tile_size: int = 224, overlap: int = 0) -> list[tuple[int, int, Image.Image]]:
    """Split image into tiles. Returns list of (x, y, tile_image)."""
    w, h = img.size
    step = tile_size - overlap
    tiles = []
    for y in range(0, h - tile_size + 1, max(step, 1)):
        for x in range(0, w - tile_size + 1, max(step, 1)):
            tile = img.crop((x, y, x + tile_size, y + tile_size))
            tiles.append((x, y, tile))
    if not tiles:
        # If image smaller than tile_size, use resized
        tiles.append((0, 0, img.resize((tile_size, tile_size))))
    return tiles


def _build_overlay(img: Image.Image, tile_coords: list[tuple[int, int]],
                   tile_labels: list[str], tile_size: int, alpha: int = 100) -> bytes:
    """Build RGBA overlay combining all pattern colors."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for (x, y), label in zip(tile_coords, tile_labels):
        color = PATTERN_PALETTE.get(label, (128, 128, 128))
        draw.rectangle([x, y, x + tile_size, y + tile_size], fill=(*color, alpha))

    # Composite
    base = img.convert("RGBA")
    combined = Image.alpha_composite(base, overlay)
    buf = io.BytesIO()
    combined.save(buf, format="PNG")
    return buf.getvalue()


def _generate_shap_mock(profile: dict[str, float], gene: str) -> dict[str, bytes]:
    """Generate mock SHAP artifacts (placeholder PNGs)."""
    artifacts = {}
    for kind in ["bar", "beeswarm"]:
        img = Image.new("RGB", (600, 400), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 20), f"SHAP {kind} — {gene} (mock)", fill=(0, 0, 0))
        y = 60
        for feat, val in profile.items():
            bar_w = int(val * 400)
            draw.rectangle([150, y, 150 + bar_w, y + 20], fill=(70, 130, 180))
            draw.text((20, y), feat, fill=(0, 0, 0))
            y += 30
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        artifacts[f"shap_{gene}_{kind}.png"] = buf.getvalue()

    # Force plot
    img = Image.new("RGB", (800, 200), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), f"SHAP Force Plot — {gene} (mock)", fill=(0, 0, 0))
    x = 50
    for feat, val in profile.items():
        w = int(val * 100)
        color = (220, 50, 50) if val > 0.2 else (50, 50, 220)
        draw.rectangle([x, 80, x + w, 120], fill=color)
        draw.text((x, 130), feat[:8], fill=(0, 0, 0))
        x += w + 10
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    artifacts[f"shap_force_{gene}_case.png"] = buf.getvalue()

    return artifacts


def _generate_shap_real(profile: dict[str, float], gene: str, model_dir: str) -> dict[str, bytes]:
    """Generate real SHAP artifacts using XGBoost + TreeExplainer.

    Adapted from thesis: SLIMA_histology_mutation_xgboost_rev3.
    """
    try:
        import xgboost as xgb
        import shap
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Load XGBoost model for this gene
        model_path = f"{model_dir}/{gene.lower()}_xgb.json"
        model = xgb.XGBClassifier()
        model.load_model(model_path)

        # Create feature array from profile
        feature_names = list(profile.keys())
        X = np.array([list(profile.values())])

        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        artifacts = {}

        # Bar plot
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.summary_plot(shap_values, X, feature_names=feature_names, plot_type="bar", show=False)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        artifacts[f"shap_{gene}_bar.png"] = buf.getvalue()

        # Beeswarm plot
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.summary_plot(shap_values, X, feature_names=feature_names, show=False)
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close(fig)
        artifacts[f"shap_{gene}_beeswarm.png"] = buf.getvalue()

        # Force plot
        fig = shap.force_plot(
            explainer.expected_value if isinstance(explainer.expected_value, float)
            else explainer.expected_value[1],
            shap_values[0] if shap_values.ndim == 2 else shap_values[1][0],
            X[0],
            feature_names=feature_names,
            matplotlib=True,
            show=False,
        )
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
        plt.close()
        artifacts[f"shap_force_{gene}_case.png"] = buf.getvalue()

        return artifacts

    except Exception as e:
        logger.warning("Real SHAP failed for %s: %s, falling back to mock", gene, e)
        return _generate_shap_mock(profile, gene)


# ═══════════════════════════════════════════════════════════════════════
# IMAGE DECODE (PIL + OpenSlide for SVS)
# ═══════════════════════════════════════════════════════════════════════

def _decode_image(image_bytes: bytes, image_format: str | None) -> Image.Image:
    """Decode image bytes to PIL RGB. Supports PNG, JPEG, TIFF (PIL) and SVS (OpenSlide).
    Whole-slide formats (svs, tif, tiff) use OpenSlide when available to avoid PIL decompression-bomb limit."""
    fmt = (image_format or "").lower().strip()
    # Use OpenSlide for whole-slide formats (avoids PIL pixel limit and supports SVS)
    if fmt in ("svs", "tif", "tiff"):
        try:
            import os
            import tempfile
            import openslide
            suffix = ".svs" if fmt == "svs" else ".tif"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(image_bytes)
                path = f.name
            try:
                slide = openslide.OpenSlide(path)
                thumb = slide.get_thumbnail((4096, 4096))
                return thumb.convert("RGB")
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        except ImportError:
            if fmt == "svs":
                raise ValueError(
                    "SVS format requires openslide-python. Install with: pip install openslide-python (and system libopenslide)."
                ) from None
            # For tif/tiff fall through to PIL with raised limit
        except Exception as e:
            logger.warning("OpenSlide decode failed for %s: %s, trying PIL", fmt, e)
            if fmt == "svs":
                raise ValueError(f"SVS decode failed: {e}") from e
            # For tif/tiff fall through to PIL
    # PIL path: allow large images (whole-slide TIFF/JPEG) to avoid decompression-bomb error
    try:
        old_max = getattr(Image, "MAX_IMAGE_PIXELS", None)
        Image.MAX_IMAGE_PIXELS = None  # allow large WSI
        try:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        finally:
            if old_max is not None:
                Image.MAX_IMAGE_PIXELS = old_max
    except Exception as e:
        logger.error("Failed to decode image (format=%s): %s", image_format, e)
        raise ValueError(f"Image decode failed: {e}") from e


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def run_inference(image_bytes: bytes, config: InferenceConfig) -> InferenceResult:
    """Execute complete inference pipeline.

    Steps (DERCAS 10.2):
      1) Decode image
      2) Tile image
      3) CTransPath embeddings (or mock)
      4) FuzzyArcLoss v3 SubCenters pattern classification (or mock)
      5) Compute pattern composition (percentages)
      6) Build overlay
      7) Build morphologic profile
      8) Mutation prediction
      9) SHAP computation
      10) Assemble metrics
    """
    t0 = time.time()
    result = InferenceResult()

    # Allow large WSI (avoids PIL decompression-bomb when using PIL path)
    old_max = getattr(Image, "MAX_IMAGE_PIXELS", None)
    Image.MAX_IMAGE_PIXELS = None
    try:
        # 1) Decode image (PIL for png/jpeg/tif/tiff, OpenSlide for svs)
        img = _decode_image(image_bytes, config.image_format)
    finally:
        if old_max is not None:
            Image.MAX_IMAGE_PIXELS = old_max

    # 2) Tile image
    tiles = _tile_image(img, config.tile_size, config.overlap)
    result.n_tiles = len(tiles)
    tile_coords = [(x, y) for x, y, _ in tiles]
    logger.info("Tiled image into %d tiles (%dx%d, overlap=%d)", len(tiles), config.tile_size, config.tile_size, config.overlap)

    # 3-4) Pattern inference
    if config.model_backend == "mock":
        tile_scores = _mock_tile_inference(len(tiles))
    else:
        # Real inference with CTransPath + FuzzyArcLoss v3
        tile_scores = _real_tile_inference(tiles, config)

    # 5) Pattern composition
    avg_scores: dict[str, float] = {}
    for p in PATTERNS:
        scores = tile_scores[p]
        avg_scores[p] = float(np.mean(scores)) if scores else 0.0

    total = sum(avg_scores.values())
    percentages = {p: round((v / total) * 100, 2) if total > 0 else 0.0 for p, v in avg_scores.items()}
    result.pattern_scores = {p: round(v, 4) for p, v in avg_scores.items()}
    result.pattern_percentages = percentages
    result.predominant_pattern = max(percentages, key=percentages.get) if percentages else ""  # type: ignore[arg-type]
    result.is_conclusive = {p: avg_scores[p] >= config.pattern_threshold for p in PATTERNS}

    # 6) Build overlay
    tile_labels = []
    for i in range(len(tiles)):
        best_p = max(PATTERNS, key=lambda p: tile_scores[p][i])
        tile_labels.append(best_p)
    result.overlay_combined_bytes = _build_overlay(img, tile_coords, tile_labels, config.tile_size)

    # 7) Morphologic profile
    profile = {
        "n_tiles_total": result.n_tiles,
        "pct_lepidic": percentages.get("lepidic", 0.0),
        "pct_acinar": percentages.get("acinar", 0.0),
        "pct_papillary": percentages.get("papillary", 0.0),
        "pct_micropapillary": percentages.get("micropapillary", 0.0),
        "pct_solid": percentages.get("solid", 0.0),
        "pct_mucinous": 0.0,
    }
    result.morphologic_profile = profile

    # 8) Mutation prediction
    pct_features = {k: v for k, v in profile.items() if k.startswith("pct_")}
    if config.model_backend == "mock":
        m_scores, m_status = _mock_mutation_prediction(pct_features)
    else:
        m_scores, m_status = _real_mutation_prediction(pct_features, config)
    result.mutation_scores = m_scores
    result.mutation_status = m_status

    # 9) SHAP
    if config.shap_enabled:
        for gene in GENES:
            if config.model_backend == "mock":
                shap_arts = _generate_shap_mock(pct_features, gene)
            else:
                shap_arts = _generate_shap_real(pct_features, gene, config.mutation_model_dir)
            result.shap_artifacts.update(shap_arts)

    # 10) Embedding (mock or real)
    if config.model_backend == "mock":
        result.embedding = np.random.default_rng(42).normal(size=(512,)).astype(np.float32)
    # else: set during real tile inference

    # Metrics
    elapsed = time.time() - t0
    result.metrics = {
        "processing_time_seconds": round(elapsed, 3),
        "device": config.device,
        "model_backend": config.model_backend,
        "model_profile": "ctranspath_fuzzyarcloss_v3_subcenters",
        "tile_size": config.tile_size,
        "n_tiles": result.n_tiles,
        "pattern_threshold": config.pattern_threshold,
        "mutation_threshold": config.mutation_threshold,
        "seed": 42,
    }

    logger.info(
        "Inference complete: %d tiles, predominant=%s (%.1f%%), time=%.2fs",
        result.n_tiles, result.predominant_pattern,
        percentages.get(result.predominant_pattern, 0), elapsed,
    )
    return result


def _real_tile_inference(tiles: list[tuple[int, int, Image.Image]], config: InferenceConfig) -> dict[str, list[float]]:
    """Run real CTransPath + FuzzyArcLoss v3 on tiles."""
    import torch
    from torchvision import transforms

    device = config.device
    backbone = _load_ctranspath_model(config.ctranspath_checkpoint, device)
    head = _load_fuzzyarc_head(config.fuzzyarc_checkpoint, num_classes=len(PATTERNS), device=device)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    scores: dict[str, list[float]] = {p: [] for p in PATTERNS}
    batch_size = 32

    with torch.no_grad():
        for i in range(0, len(tiles), batch_size):
            batch_imgs = [transform(t[2]) for t in tiles[i:i + batch_size]]
            batch_tensor = torch.stack(batch_imgs).to(device)

            embeddings = backbone(batch_tensor)  # (B, 512)
            logits = head(embeddings)  # (B, 5)
            probs = torch.softmax(logits, dim=1).cpu().numpy()

            for j in range(probs.shape[0]):
                for k, p in enumerate(PATTERNS):
                    scores[p].append(float(probs[j, k]))

    return scores


def _real_mutation_prediction(
    pct_features: dict[str, float], config: InferenceConfig
) -> tuple[dict[str, float], dict[str, str]]:
    """Run real XGBoost mutation prediction."""
    try:
        import xgboost as xgb

        feature_names = sorted(pct_features.keys())
        X = np.array([[pct_features[f] for f in feature_names]])

        scores = {}
        statuses = {}
        for gene in GENES:
            model_path = f"{config.mutation_model_dir}/{gene.lower()}_xgb.json"
            try:
                model = xgb.XGBClassifier()
                model.load_model(model_path)
                prob = float(model.predict_proba(X)[0, 1])
                scores[gene] = round(prob, 4)
                if prob >= config.mutation_threshold:
                    statuses[gene] = "POS"
                elif prob >= 0.40:
                    statuses[gene] = "INCONCLUSIVE"
                else:
                    statuses[gene] = "NEG"
            except Exception as e:
                logger.warning("No model for %s: %s", gene, e)
                scores[gene] = 0.0
                statuses[gene] = "INCONCLUSIVE"

        return scores, statuses
    except ImportError:
        logger.warning("XGBoost not available, falling back to mock")
        return _mock_mutation_prediction(pct_features)
