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
    "lepidic": (230, 255, 50),
    "acinar": (0, 255, 0),
    "papillary": (0, 0, 255),
    "micropapillary": (255, 215, 0),
    "solid": (255, 0, 0),
    "mucinous": (255, 165, 0),
}

PATTERNS = ["lepidic", "acinar", "papillary", "micropapillary", "solid", "mucinous"]
GENES_V1 = ["EGFR", "KRAS", "TP53"]
GENES_V2 = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]
GENES = GENES_V2

# Checkpoint label mapping (from training)
_CK_ID2LABEL: dict[int, str] = {
    0: "acinar", 1: "lepidic", 2: "micropapillary",
    3: "mucinous", 4: "papillary", 5: "solid",
}


@dataclass
class InferenceConfig:
    """Configuration for a single inference run."""
    image_uri: str = ""
    image_format: str | None = None
    tile_size: int = 224
    overlap: int = 0
    device: str = "cpu"
    pattern_threshold: float = 0.55
    mutation_threshold: float = 0.60
    model_backend: str = "mock"
    ctranspath_checkpoint: str = ""
    fuzzyarc_checkpoint: str = ""
    # v1 legacy
    mutation_model_dir: str = ""
    # v2 ABMIL + Choquet
    v2_checkpoint_dir: str = ""
    use_choquet: bool = True
    top_k_tiles: int = 200
    max_tiles_wsi: int = 50000
    genes: list[str] = field(default_factory=lambda: list(GENES_V2))
    shap_enabled: bool = True
    shap_decomposition_enabled: bool = True


@dataclass
class MutationReportEntry:
    """v2 per-gene mutation prediction with confidence labelling."""
    gene: str = ""
    probability: float = 0.0
    label: str = "Inconclusive"   # Conclusive | Inconclusive
    auroc_threshold: float = 0.70
    disclaimer: str | None = None
    method: str = "abmil"         # abmil | choquet


@dataclass
class SHAPDecompositionEntry:
    """v2 SHAP decomposition per gene: embedding vs pattern contribution."""
    gene: str = ""
    embedding_contribution_pct: float = 0.0
    pattern_contribution_pct: float = 0.0
    top_pattern_dims: list[str] = field(default_factory=list)


@dataclass
class ChoquetShapleyEntry:
    """v2 Choquet Shapley values + interaction indices per gene."""
    gene: str = ""
    shapley_values: dict[str, float] = field(default_factory=dict)
    interaction_indices: dict[str, float] = field(default_factory=dict)


@dataclass
class InferenceResult:
    """Complete result of an inference run (v2)."""
    pattern_scores: dict[str, float] = field(default_factory=dict)
    pattern_percentages: dict[str, float] = field(default_factory=dict)
    predominant_pattern: str = ""
    is_conclusive: dict[str, bool] = field(default_factory=dict)
    thumbnail_bytes: bytes = b""
    overlay_combined_bytes: bytes = b""
    attention_overlay_bytes: bytes = b""
    combined_overlay_bytes: bytes = b""
    embedding: np.ndarray | None = None
    tile_embeddings: np.ndarray | None = None   # (N, 512) per-tile
    tile_pattern_probs: np.ndarray | None = None  # (N, 6) per-tile
    n_tiles: int = 0
    tile_coords: list[tuple[int, int]] = field(default_factory=list)
    # v2 mutation report (replaces v1 XGBoost)
    mutation_report: list[MutationReportEntry] = field(default_factory=list)
    # v1 legacy fields (kept for backward compat)
    mutation_scores: dict[str, float] = field(default_factory=dict)
    mutation_status: dict[str, str] = field(default_factory=dict)
    # Morphologic profile
    morphologic_profile: dict[str, float] = field(default_factory=dict)
    # v2 SHAP decomposition
    shap_decompositions: list[SHAPDecompositionEntry] = field(default_factory=list)
    # v2 Choquet Shapley
    choquet_shapley: list[ChoquetShapleyEntry] = field(default_factory=list)
    # v1 legacy SHAP artifacts (images)
    shap_artifacts: dict[str, bytes] = field(default_factory=dict)
    # Attention map
    attention_top_k_indices: list[int] = field(default_factory=list)
    # Ablation comparison (proposed vs emb-only vs pat-only)
    ablation_results: list[Any] = field(default_factory=list)
    # Permutation importance
    permutation_results: list[Any] = field(default_factory=list)
    # Image quality warnings
    quality_warnings: list[str] = field(default_factory=list)
    # Metrics
    metrics: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# REAL ML COMPONENTS (used when model_backend == "local")
# v2: CTransPath Swin Tiny (4-ch) + FuzzyArcLoss V2 classifier
# ═══════════════════════════════════════════════════════════════════════

_MODEL_CACHE: dict[str, Any] = {}


def _load_real_pipeline(checkpoint_path: str, device: str = "cpu") -> dict[str, Any]:
    """Load CTransPath Swin Tiny + FuzzyArcLoss V2 from best_fuzzyarcloss_v2.pth.

    Checkpoint structure (from thesis training):
      model    — nn.Sequential(CTransPathBackbone(4ch→768), ProjectionHead(768→512))
      loss_fn  — {'weight': [6, 512], 'head.weight': [6, 512]}
      config   — {EMBED_DIM: 512, IMG_SIZE: 224, S_SCALE: 46.1, ...}
    """
    if checkpoint_path in _MODEL_CACHE:
        return _MODEL_CACHE[checkpoint_path]

    import torch

    from app.ml.models.ctranspath_backbone import CTransPathPipeline

    model = CTransPathPipeline.from_finetuned(checkpoint_path, device)
    classifier_info = CTransPathPipeline.load_classifier_weights(checkpoint_path, device)

    pipeline = {
        "model": model,
        "head_weight": classifier_info["head_weight"],
        "id2label": classifier_info["id2label"],
        "num_classes": classifier_info["num_classes"],
        "embed_dim": classifier_info["embed_dim"],
        "s_scale": classifier_info["s_scale"],
        "img_size": classifier_info["img_size"],
    }
    _MODEL_CACHE[checkpoint_path] = pipeline
    logger.info(
        "CTransPath pipeline ready: %d classes, embed=%d, s=%.2f, img=%d",
        pipeline["num_classes"], pipeline["embed_dim"],
        pipeline["s_scale"], pipeline["img_size"],
    )
    return pipeline


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
    """Build RGBA overlay with Gaussian-smoothed pattern regions.

    Instead of hard rectangles, each tile's center is painted as a soft blob
    and then the whole overlay is blurred so boundaries blend naturally,
    producing a heatmap-like appearance over the histopathological image.
    """
    from PIL import ImageFilter

    w, h = img.size

    # Build per-channel float accumulators (R, G, B, weight) at image resolution
    acc_r = np.zeros((h, w), dtype=np.float32)
    acc_g = np.zeros((h, w), dtype=np.float32)
    acc_b = np.zeros((h, w), dtype=np.float32)
    acc_w = np.zeros((h, w), dtype=np.float32)

    # Paint each tile as a radial gradient from center (strongest) to edge (weakest)
    half = tile_size // 2
    ys = np.arange(tile_size, dtype=np.float32) - half
    xs = np.arange(tile_size, dtype=np.float32) - half
    gx, gy = np.meshgrid(xs, ys)
    sigma = tile_size * 0.38
    gaussian_kernel = np.exp(-(gx ** 2 + gy ** 2) / (2 * sigma ** 2))

    for (tx, ty), label in zip(tile_coords, tile_labels):
        color = PATTERN_PALETTE.get(label, (128, 128, 128))
        # Clip to image bounds
        y1, y2 = ty, min(ty + tile_size, h)
        x1, x2 = tx, min(tx + tile_size, w)
        ky2, kx2 = y2 - ty, x2 - tx
        kern = gaussian_kernel[:ky2, :kx2]
        acc_r[y1:y2, x1:x2] += kern * color[0]
        acc_g[y1:y2, x1:x2] += kern * color[1]
        acc_b[y1:y2, x1:x2] += kern * color[2]
        acc_w[y1:y2, x1:x2] += kern

    # Normalize and convert to uint8
    mask = acc_w > 0
    for ch in (acc_r, acc_g, acc_b):
        ch[mask] /= acc_w[mask]

    r_img = Image.fromarray(np.clip(acc_r, 0, 255).astype(np.uint8), "L")
    g_img = Image.fromarray(np.clip(acc_g, 0, 255).astype(np.uint8), "L")
    b_img = Image.fromarray(np.clip(acc_b, 0, 255).astype(np.uint8), "L")

    # Alpha channel: stronger where we have predictions, softened
    alpha_arr = np.where(mask, alpha, 0).astype(np.uint8)
    a_img = Image.fromarray(alpha_arr, "L")

    overlay = Image.merge("RGBA", (r_img, g_img, b_img, a_img))

    # Apply Gaussian blur to soften further (radius proportional to tile size)
    blur_radius = max(tile_size // 6, 4)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))

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

_WSI_SLIDE_HANDLE = None  # holds OpenSlide handle for full-resolution tiling
_IMAGE_QUALITY_WARNINGS: list[str] = []  # populated by _decode_image


def _convert_to_pyramidal_tiff(input_path: str, source_format: str = "tif") -> str:
    """Convert a flat TIFF or BIF to pyramidal TIFF using pyvips.

    pyvips/libvips can read many formats (TIFF, BIF/Ventana, JPEG, PNG, etc.)
    via its built-in loaders and OpenSlide integration. The output is always
    a standard pyramidal TIFF that OpenSlide can open reliably.

    Returns path to the new pyramidal file. The caller owns the temp file.
    """
    import pyvips
    import tempfile
    import os

    logger.info("Converting %s to pyramidal TIFF: %s (%.1f MB)",
                source_format.upper(), input_path, os.path.getsize(input_path) / 1e6)

    try:
        img = pyvips.Image.new_from_file(input_path, access="sequential")
    except Exception:
        img = pyvips.Image.openslideload(input_path, level=0)

    logger.info("pyvips loaded: %dx%d, %d bands", img.width, img.height, img.bands)

    if img.bands == 4:
        img = img[:3]

    out_fd, out_path = tempfile.mkstemp(suffix=".tiff")
    os.close(out_fd)

    img.tiffsave(
        out_path,
        pyramid=True,
        tile=True,
        tile_width=256,
        tile_height=256,
        compression="jpeg",
        Q=85,
        bigtiff=True,
    )
    out_size = os.path.getsize(out_path)
    logger.info("Pyramidal TIFF saved: %s (%.1f MB)", out_path, out_size / 1e6)
    return out_path


MIN_WSI_PIXELS = 20000
"""Minimum dimension (width or height) in pixels for WSI images.
Below this, the slide is too low-resolution for reliable pattern classification.
Reference: TCGA SVS at 20x ≈ 40,000+ px on longest side.
Slides under 20,000 px likely scanned at <10x or are thumbnails."""

MAX_MPP_THRESHOLD = 1.0
"""Maximum microns-per-pixel (MPP) accepted. 20x = ~0.5 MPP, 10x = ~1.0 MPP.
Slides above 1.0 MPP are too low-resolution for CTransPath (trained at 20x)."""


def _validate_wsi_quality(slide, image_format: str) -> list[str]:
    """Validate WSI quality. Returns list of warnings (empty = OK)."""
    warnings = []
    w, h = slide.dimensions

    if max(w, h) < MIN_WSI_PIXELS:
        warnings.append(
            f"LOW RESOLUTION: Image is only {w}x{h} pixels. "
            f"Minimum recommended: {MIN_WSI_PIXELS}px on longest side. "
            f"Pattern classification may be unreliable."
        )

    # Check MPP from OpenSlide properties
    mpp_x = slide.properties.get('openslide.mpp-x')
    mpp_y = slide.properties.get('openslide.mpp-y')
    if mpp_x:
        mpp = float(mpp_x)
        mag = 10.0 / mpp if mpp > 0 else 0
        logger.info("WSI resolution: %.3f MPP (≈%.0fx magnification)", mpp, mag)
        if mpp > MAX_MPP_THRESHOLD:
            warnings.append(
                f"LOW MAGNIFICATION: Slide scanned at {mpp:.2f} MPP (≈{mag:.0f}x). "
                f"CTransPath requires 20x (0.5 MPP) or higher. Results may be unreliable."
            )
    else:
        logger.info("WSI resolution: MPP not available in metadata")

    # Check for non-H&E staining by analyzing color distribution of thumbnail
    thumb = slide.get_thumbnail((512, 512))
    import numpy as np
    arr = np.array(thumb.convert("RGB"))
    r, g, b = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()

    # H&E tissue is predominantly pink (R>G, R>B) or purple (R~B>G)
    # IHC/special stains: brown (DAB), blue-only (alcian blue), red-only (PAS)
    # Very blue with no pink = likely non-H&E
    if b > r + 20 and b > g + 20 and r < 150:
        warnings.append(
            "NON-H&E STAIN DETECTED: Image color profile suggests a special stain "
            "(IHC, immunofluorescence, or other). LCHAI was trained exclusively on H&E slides. "
            "Results will be unreliable."
        )
    # Very brown = DAB (IHC)
    if r > 150 and g > 100 and b < 80 and (r - b) > 70:
        warnings.append(
            "IHC STAIN DETECTED: Brown chromogen (DAB) detected. "
            "LCHAI was trained on H&E stains only. Upload an H&E slide instead."
        )

    # Tissue folds: check for very dark regions in the thumbnail
    gray = arr.mean(axis=2)
    very_dark_pct = (gray < 60).mean()
    if very_dark_pct > 0.15:
        warnings.append(
            f"TISSUE FOLDS: {very_dark_pct*100:.0f}% of the slide contains very dark regions, "
            f"likely tissue folds or thick areas. These artifacts may affect pattern classification."
        )

    global _IMAGE_QUALITY_WARNINGS
    _IMAGE_QUALITY_WARNINGS = warnings
    for w_msg in warnings:
        logger.warning("Image quality: %s", w_msg)

    return warnings


def _decode_image(image_bytes: bytes, image_format: str | None) -> Image.Image:
    """Decode image bytes to PIL RGB. Supports PNG, JPEG, TIFF (PIL) and SVS (OpenSlide).

    For WSI formats (svs, tif, tiff), returns a *thumbnail* for overlay rendering
    but stores the OpenSlide handle in _WSI_SLIDE_HANDLE for full-resolution tiling.
    Flat TIFFs are automatically converted to pyramidal format via pyvips.
    Validates image quality (resolution, stain type, artifacts).
    """
    global _WSI_SLIDE_HANDLE
    _WSI_SLIDE_HANDLE = None

    fmt = (image_format or "").lower().strip()
    logger.info("_decode_image: format=%r, bytes=%d, fmt=%r", image_format, len(image_bytes), fmt)
    if fmt in ("svs", "tif", "tiff", "bif"):
        try:
            import os
            import tempfile
            import openslide
            suffix = {"svs": ".svs", "bif": ".bif"}.get(fmt, ".tif")
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(image_bytes)
                path = f.name

            pyramidal_path = None
            try:
                slide = openslide.OpenSlide(path)
                _WSI_SLIDE_HANDLE = (slide, path)
                quality_warnings = _validate_wsi_quality(slide, fmt)
                thumb = slide.get_thumbnail((4096, 4096))
                logger.info(
                    "OpenSlide WSI opened: dims=%s, thumbnail=%s, warnings=%d",
                    slide.dimensions, thumb.size, len(quality_warnings),
                )
                return thumb.convert("RGB")
            except Exception as openslide_err:
                logger.warning("OpenSlide failed for %s: %s — attempting pyramidal conversion via pyvips", fmt, openslide_err)
                try:
                    os.unlink(path)
                except OSError:
                    pass

                if fmt in ("tif", "tiff", "bif"):
                    try:
                        src_suffix = {"bif": ".bif"}.get(fmt, ".tif")
                        with tempfile.NamedTemporaryFile(suffix=src_suffix, delete=False) as f2:
                            f2.write(image_bytes)
                            src_path = f2.name
                        pyramidal_path = _convert_to_pyramidal_tiff(src_path, source_format=fmt)
                        try:
                            os.unlink(src_path)
                        except OSError:
                            pass

                        slide = openslide.OpenSlide(pyramidal_path)
                        _WSI_SLIDE_HANDLE = (slide, pyramidal_path)
                        quality_warnings = _validate_wsi_quality(slide, fmt)
                        thumb = slide.get_thumbnail((4096, 4096))
                        logger.info(
                            "OpenSlide WSI opened (converted from %s): dims=%s, thumbnail=%s, warnings=%d",
                            fmt.upper(), slide.dimensions, thumb.size, len(quality_warnings),
                        )
                        return thumb.convert("RGB")
                    except Exception as conv_err:
                        logger.error("Pyramidal conversion failed for %s: %s", fmt, conv_err)
                        if pyramidal_path:
                            try:
                                os.unlink(pyramidal_path)
                            except OSError:
                                pass
                        raise ValueError(
                            f"{fmt.upper()} decode failed: OpenSlide error: {openslide_err}; "
                            f"Pyramidal conversion error: {conv_err}"
                        ) from conv_err
                else:
                    raise ValueError(f"WSI decode failed for {fmt}: {openslide_err}") from openslide_err

        except ImportError as ie:
            logger.error("OpenSlide import failed: %s", ie)
            if fmt == "svs":
                raise ValueError(
                    "SVS format requires openslide-python. Install with: pip install openslide-python (and system libopenslide)."
                ) from None
        except ValueError:
            raise
        except Exception as e:
            logger.warning("WSI decode failed for %s: %s, trying PIL", fmt, e)
            if fmt == "svs":
                raise ValueError(f"SVS decode failed: {e}") from e
    # PIL path for regular images
    try:
        old_max = getattr(Image, "MAX_IMAGE_PIXELS", None)
        Image.MAX_IMAGE_PIXELS = None
        try:
            return Image.open(io.BytesIO(image_bytes)).convert("RGB")
        finally:
            if old_max is not None:
                Image.MAX_IMAGE_PIXELS = old_max
    except Exception as e:
        logger.error("Failed to decode image (format=%s): %s", image_format, e)
        raise ValueError(f"Image decode failed: {e}") from e


def _cleanup_wsi():
    """Close OpenSlide handle and delete temp file."""
    global _WSI_SLIDE_HANDLE
    if _WSI_SLIDE_HANDLE is not None:
        slide, path = _WSI_SLIDE_HANDLE
        _WSI_SLIDE_HANDLE = None
        try:
            slide.close()
        except Exception:
            pass
        try:
            import os
            os.unlink(path)
        except OSError:
            pass


def _is_tcga_slide() -> bool:
    """Detect if current slide is from TCGA (curated, no pen markers)."""
    if _WSI_SLIDE_HANDLE is None:
        return False
    _, path = _WSI_SLIDE_HANDLE
    return "TCGA" in (path or "").upper()


def _tile_wsi_full_resolution(
    tile_size: int = 224,
    level: int = 0,
    tissue_threshold: float = 0.15,
    max_tiles: int = 50000,
    image_uri: str = "",
) -> list[tuple[int, int, Image.Image]] | None:
    """Tile a WSI at full resolution using OpenSlide read_region.

    Applies two filtering levels:
    - TCGA slides (curated): minimal filters (background + very dark only)
    - Hospital/real slides: full artifact rejection (pen markers, saturation, etc.)
    """
    if _WSI_SLIDE_HANDLE is None:
        return None

    is_tcga = _is_tcga_slide() or "TCGA" in image_uri.upper()
    slide, _ = _WSI_SLIDE_HANDLE
    w, h = slide.level_dimensions[level]
    filter_mode = "TCGA-minimal" if is_tcga else "hospital-full"
    logger.info("WSI full-resolution tiling: level=%d, dims=(%d, %d), tile=%d, filters=%s",
                level, w, h, tile_size, filter_mode)

    tiles = []
    step = tile_size
    n_x = (w - tile_size) // step + 1
    n_y = (h - tile_size) // step + 1
    total_candidates = n_x * n_y
    logger.info("WSI tile grid: %d x %d = %d candidates (max_tiles=%d)", n_x, n_y, total_candidates, max_tiles)

    stride = 1
    if total_candidates > max_tiles * 2:
        stride = max(1, int(math.sqrt(total_candidates / max_tiles)))
        logger.info("WSI subsampling with stride=%d to stay under max_tiles", stride)

    count = 0
    rejected_bg = 0
    rejected_artifact = 0

    for yi in range(0, n_y, stride):
        for xi in range(0, n_x, stride):
            if count >= max_tiles:
                break
            x = xi * step
            y = yi * step
            region = slide.read_region((x, y), level, (tile_size, tile_size))
            tile_rgb = region.convert("RGB")

            arr = np.array(tile_rgb)
            gray = arr.mean(axis=2)

            # --- FILTER 1: Background (both TCGA and hospital) ---
            tissue_frac = (gray < 220).mean()
            if tissue_frac < tissue_threshold:
                rejected_bg += 1
                continue

            # --- FILTER 2: Very dark tiles (both TCGA and hospital) ---
            very_dark = (gray < 50).mean()
            if very_dark > 0.3:
                rejected_artifact += 1
                continue

            # --- FILTER 2b: Tissue folds (dark thick areas, both TCGA and hospital) ---
            # Folds appear as unnaturally dark bands with high local intensity variance
            dark_moderate = (gray < 100).mean()
            if dark_moderate > 0.5:
                rejected_artifact += 1
                continue

            # --- FILTER 2c: Low texture (holes, glass, mounting medium) ---
            # Real tissue has high intensity variance (nuclei, stroma, glands)
            # Empty areas (lumen, holes, glass) have very uniform appearance
            gray_std = gray.std()
            if gray_std < 12:
                rejected_artifact += 1
                continue

            # --- FILTER 3: Low saturation (both, but lenient for TCGA) ---
            r, g, b = arr[:,:,0].astype(float), arr[:,:,1].astype(float), arr[:,:,2].astype(float)
            max_rgb = np.maximum(np.maximum(r, g), b)
            min_rgb = np.minimum(np.minimum(r, g), b)
            saturation = np.where(max_rgb > 0, (max_rgb - min_rgb) / max_rgb, 0)
            mean_sat = saturation.mean()
            if mean_sat < 0.03:
                rejected_artifact += 1
                continue

            # --- TCGA: skip all marker filters (curated images) ---
            if not is_tcga:
                # Straight edges (barcodes, text, labels)
                gray_uint8 = gray.astype(np.uint8)
                dx = np.abs(np.diff(gray_uint8, axis=1)).mean()
                dy = np.abs(np.diff(gray_uint8, axis=0)).mean()
                edge_ratio = max(dx, dy) / (min(dx, dy) + 1e-6)
                if edge_ratio > 3.0 and (dx > 15 or dy > 15):
                    rejected_artifact += 1
                    continue

                # Green marker pen
                green_dominant = ((g > r + 20) & (g > b + 20)).mean()
                if green_dominant > 0.4:
                    rejected_artifact += 1
                    continue

                # Red marker pen
                red_marker = ((r > 150) & (r > g + 40) & (r > b + 40)).mean()
                if red_marker > 0.3:
                    rejected_artifact += 1
                    continue

                # Olive/yellow marker
                olive_marker = ((r > 140) & (g > 120) & (b < 100) & ((r + g) > 2.5 * b)).mean()
                if olive_marker > 0.3:
                    rejected_artifact += 1
                    continue

                # Blue/teal marker pen
                blue_marker = ((b > r + 30) & (b > g + 20) & (b > 100)).mean()
                if blue_marker > 0.25:
                    rejected_artifact += 1
                    continue

                # Teal/cyan marker
                teal_marker = ((g > r + 20) & (b > r + 20) & (r < 100)).mean()
                if teal_marker > 0.30:
                    rejected_artifact += 1
                    continue

                # Non-H&E highly saturated regions
                high_sat = (saturation > 0.6).mean()
                if high_sat > 0.5 and mean_sat > 0.45:
                    rejected_artifact += 1
                    continue

            tiles.append((x, y, tile_rgb))
            count += 1
        if count >= max_tiles:
            break

    logger.info("WSI tiling complete: %d tissue tiles from %d candidates "
                "(rejected: %d background, %d artifacts, filters=%s)",
                len(tiles), total_candidates, rejected_bg, rejected_artifact, filter_mode)
    return tiles if tiles else None


# ═══════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def run_inference(image_bytes: bytes, config: InferenceConfig, progress_callback=None) -> InferenceResult:
    """Execute complete v2 inference pipeline.

    Steps:
      1) Decode image
      2) Tile image
      3-4) CTransPath + FuzzyArcLoss pattern classification
      5) Pattern composition
      6) Build pattern overlay
      7) Morphologic profile
      8) v2 ABMIL mutation prediction (Pathway A)
      9) v2 Choquet mutation prediction (Pathway B, if enabled)
      10) v2 Attention map from ABMIL
      11) v2 SHAP decomposition (DeepSHAP on ABMIL)
      12) v2 Choquet Shapley values
      13) v1 legacy SHAP (backward compat)
      14) Metrics
    """
    t0 = time.time()
    result = InferenceResult()
    global _IMAGE_QUALITY_WARNINGS
    _IMAGE_QUALITY_WARNINGS = []

    old_max = getattr(Image, "MAX_IMAGE_PIXELS", None)
    Image.MAX_IMAGE_PIXELS = None
    try:
        img = _decode_image(image_bytes, config.image_format)
    finally:
        if old_max is not None:
            Image.MAX_IMAGE_PIXELS = old_max

    _p = progress_callback or (lambda *a: None)
    _p(0.08, "Decoding image...")

    # Save clean thumbnail (no overlay) for the Viewer "Original" layer
    thumb_buf = io.BytesIO()
    img.save(thumb_buf, format="PNG")
    result.thumbnail_bytes = thumb_buf.getvalue()
    _p(0.10, "Image decoded. Loading CTransPath model...")

    # 2) Tile — use full-resolution WSI tiling when available
    tile_sz = config.tile_size
    if config.model_backend == "local" and config.fuzzyarc_checkpoint:
        pipe = _load_real_pipeline(config.fuzzyarc_checkpoint, config.device)
        tile_sz = pipe["img_size"]

    _p(0.12, "Extracting tissue tiles from WSI (filtering artifacts)...")

    wsi_tiles = _tile_wsi_full_resolution(
        tile_size=tile_sz, tissue_threshold=0.15, max_tiles=config.max_tiles_wsi,
        image_uri=config.image_uri,
    )
    if wsi_tiles is not None and len(wsi_tiles) > 0:
        tiles = wsi_tiles
        logger.info("Using full-resolution WSI tiling: %d tissue tiles at %dpx", len(tiles), tile_sz)
    else:
        tiles = _tile_image(img, tile_sz, config.overlap)
        logger.info("Using thumbnail tiling: %d tiles (%dx%d, overlap=%d)", len(tiles), tile_sz, tile_sz, config.overlap)

    result.n_tiles = len(tiles)
    tile_coords = [(x, y) for x, y, _ in tiles]
    result.tile_coords = tile_coords
    logger.info("Total tiles for inference: %d", len(tiles))
    _p(0.18, f"Tiling complete: {len(tiles)} tissue tiles. Starting CTransPath inference...")
    _p(0.20, f"Running CTransPath on {len(tiles)} tiles...")

    # 3-4) Pattern inference
    if config.model_backend == "mock":
        tile_scores = _mock_tile_inference(len(tiles))
    else:
        tile_scores = _real_tile_inference(tiles, config)

    # Build per-tile pattern probability matrix (N, 6) for v2
    n_tiles = len(tiles)
    tile_probs_matrix = np.zeros((n_tiles, len(PATTERNS)), dtype=np.float32)
    for j, p in enumerate(PATTERNS):
        if p in tile_scores:
            for i in range(min(n_tiles, len(tile_scores[p]))):
                tile_probs_matrix[i, j] = tile_scores[p][i]
    result.tile_pattern_probs = tile_probs_matrix

    _p(0.50, "Computing pattern composition + overlays...")

    # 5) Pattern composition
    active_patterns = [p for p in PATTERNS if p in tile_scores]
    avg_scores: dict[str, float] = {}
    for p in active_patterns:
        scores = tile_scores[p]
        avg_scores[p] = float(np.mean(scores)) if scores else 0.0

    total = sum(avg_scores.values())
    percentages = {p: round((v / total) * 100, 2) if total > 0 else 0.0 for p, v in avg_scores.items()}
    result.pattern_scores = {p: round(v, 4) for p, v in avg_scores.items()}
    result.pattern_percentages = percentages
    result.predominant_pattern = max(percentages, key=percentages.get) if percentages else ""  # type: ignore[arg-type]
    result.is_conclusive = {p: avg_scores[p] >= config.pattern_threshold for p in active_patterns}

    # 6) Pattern overlay — scale WSI coords to thumbnail for rendering
    tile_labels = []
    for i in range(n_tiles):
        best_p = max(active_patterns, key=lambda p: tile_scores[p][i])
        tile_labels.append(best_p)

    overlay_coords = tile_coords
    overlay_tile_sz = tile_sz
    if _WSI_SLIDE_HANDLE is not None:
        wsi_slide, _ = _WSI_SLIDE_HANDLE
        wsi_w, wsi_h = wsi_slide.dimensions
        thumb_w, thumb_h = img.size
        sx, sy = thumb_w / wsi_w, thumb_h / wsi_h
        overlay_coords = [(int(x * sx), int(y * sy)) for x, y in tile_coords]
        scaled_tile = int(tile_sz * min(sx, sy))
        min_visible = max(40, min(thumb_w, thumb_h) // 30)
        overlay_tile_sz = max(min_visible, scaled_tile)
        logger.info("WSI overlay: thumb=%dx%d, scale=%.4f, scaled_tile=%d, min_visible=%d, overlay_tile_sz=%d",
                    thumb_w, thumb_h, min(sx, sy), scaled_tile, min_visible, overlay_tile_sz)
        result.overlay_combined_bytes = _build_overlay(img, overlay_coords, tile_labels, overlay_tile_sz, alpha=160)
    else:
        result.overlay_combined_bytes = _build_overlay(img, tile_coords, tile_labels, tile_sz)

    # 7) Morphologic profile
    profile = {
        "n_tiles_total": result.n_tiles,
        "pct_lepidic": percentages.get("lepidic", 0.0),
        "pct_acinar": percentages.get("acinar", 0.0),
        "pct_papillary": percentages.get("papillary", 0.0),
        "pct_micropapillary": percentages.get("micropapillary", 0.0),
        "pct_solid": percentages.get("solid", 0.0),
        "pct_mucinous": percentages.get("mucinous", 0.0),
    }
    result.morphologic_profile = profile

    # Tile embeddings: use real CTransPath embeddings or generate mock
    if config.model_backend == "mock":
        rng = np.random.default_rng(42)
        result.tile_embeddings = rng.normal(size=(n_tiles, 512)).astype(np.float32)
        result.embedding = result.tile_embeddings.mean(axis=0)
    else:
        if "embeddings" in _REAL_TILE_EMBEDDINGS:
            result.tile_embeddings = _REAL_TILE_EMBEDDINGS["embeddings"]
            result.embedding = result.tile_embeddings.mean(axis=0)
            logger.info("Using real CTransPath embeddings: shape=%s", result.tile_embeddings.shape)
        else:
            logger.warning("No real embeddings available — falling back to random")
            result.tile_embeddings = np.random.default_rng(42).normal(size=(n_tiles, 512)).astype(np.float32)
            result.embedding = result.tile_embeddings.mean(axis=0)

    _p(0.55, "Running mutation prediction (ABMIL/Choquet)...")

    # ── v2: Pathway A — Pattern-Informed ABMIL ──
    try:
        from app.ml.inference.abmil_inference import run_abmil_inference
        from app.ml.checkpoints.loader import CheckpointLoader

        loader = CheckpointLoader(config.v2_checkpoint_dir, config.device)
        abmil_output = run_abmil_inference(
            result.tile_embeddings,
            tile_probs_matrix,
            loader,
            top_k=config.top_k_tiles,
            genes=config.genes,
        )

        for gr in abmil_output.gene_results:
            result.mutation_report.append(MutationReportEntry(
                gene=gr.gene,
                probability=gr.probability,
                label=gr.label,
                auroc_threshold=gr.auroc_threshold,
                disclaimer=gr.disclaimer,
                method=gr.method or "abmil",
            ))
            result.mutation_scores[gr.gene] = gr.probability
            from app.ml.checkpoints.loader import GENE_MUTATION_THRESHOLD
            gene_thr = GENE_MUTATION_THRESHOLD.get(gr.gene, config.mutation_threshold)
            status = "POS" if gr.probability >= gene_thr else "NEG"
            result.mutation_status[gr.gene] = status

        result.attention_top_k_indices = abmil_output.top_k_indices

        # Build attention heatmap overlay from ABMIL (scale coords for WSI)
        if abmil_output.attention_map is not None and len(tile_coords) > 0:
            use_coords = overlay_coords if _WSI_SLIDE_HANDLE is not None else tile_coords
            use_tile_sz = overlay_tile_sz if _WSI_SLIDE_HANDLE is not None else tile_sz

            result.attention_overlay_bytes = _build_attention_overlay(
                img, use_coords, abmil_output.attention_map,
                abmil_output.top_k_indices, use_tile_sz,
            )

            comb_alpha = 160 if _WSI_SLIDE_HANDLE is not None else 120
            result.combined_overlay_bytes = _build_combined_overlay(
                img, use_coords, tile_labels,
                abmil_output.attention_map, abmil_output.top_k_indices,
                use_tile_sz, pattern_alpha=comb_alpha,
            )

    except Exception as e:
        logger.warning("v2 ABMIL pathway failed: %s — falling back to v1 XGBoost", e)
        pct_features = {k: v for k, v in profile.items() if k.startswith("pct_")}
        if config.model_backend == "mock":
            m_scores, m_status = _mock_mutation_prediction(pct_features)
        else:
            m_scores, m_status = _real_mutation_prediction(pct_features, config)
        result.mutation_scores = m_scores
        result.mutation_status = m_status

    # ── v2: Pathway B — Fuzzy Choquet MIL (optional) ──
    if config.use_choquet:
        try:
            from app.ml.inference.choquet_inference import run_choquet_inference
            from app.ml.checkpoints.loader import CheckpointLoader

            loader = CheckpointLoader(config.v2_checkpoint_dir, config.device)
            choquet_output = run_choquet_inference(
                result.tile_embeddings,
                tile_probs_matrix,
                loader,
                genes=config.genes,
            )
            for cr in choquet_output.gene_results:
                result.choquet_shapley.append(ChoquetShapleyEntry(
                    gene=cr.gene,
                    shapley_values=cr.shapley_values,
                    interaction_indices=cr.interaction_indices,
                ))
        except Exception as e:
            logger.warning("v2 Choquet pathway failed: %s", e)

    _p(0.65, "Running ablation + permutation analysis...")

    # ── v2: Ablation comparison (proposed vs emb-only vs pat-only) ──
    try:
        from app.ml.inference.abmil_inference import run_ablation_comparison, run_permutation_importance
        from app.ml.checkpoints.loader import CheckpointLoader as CL2

        loader2 = CL2(config.v2_checkpoint_dir, config.device)
        result.ablation_results = run_ablation_comparison(
            result.tile_embeddings, tile_probs_matrix, loader2, genes=config.genes,
        )
        result.permutation_results = run_permutation_importance(
            result.tile_embeddings, tile_probs_matrix, loader2,
            n_repeats=10, genes=config.genes,
        )
    except Exception as e:
        logger.warning("Ablation/permutation analysis failed: %s", e)

    _p(0.75, "Computing SHAP decomposition...")

    # ── v2: SHAP Decomposition (DeepSHAP on ABMIL) ──
    if config.shap_decomposition_enabled:
        try:
            from app.ml.inference.shap_decompose import run_shap_decomposition
            from app.ml.checkpoints.loader import CheckpointLoader

            loader = CheckpointLoader(config.v2_checkpoint_dir, config.device)
            concat = np.concatenate([result.tile_embeddings, tile_probs_matrix], axis=1)

            for gene in config.genes:
                try:
                    model = loader.load_abmil(gene, input_dim=concat.shape[1])
                    decomp = run_shap_decomposition(concat, model, gene, config.device)
                    result.shap_decompositions.append(SHAPDecompositionEntry(
                        gene=gene,
                        embedding_contribution_pct=decomp.embedding_contribution_pct,
                        pattern_contribution_pct=decomp.pattern_contribution_pct,
                        top_pattern_dims=decomp.top_pattern_dims,
                    ))
                    if decomp.bar_plot_bytes:
                        result.shap_artifacts[f"shap_decomp_{gene}_bar.png"] = decomp.bar_plot_bytes
                    if decomp.decomposition_plot_bytes:
                        result.shap_artifacts[f"shap_decomp_{gene}_patterns.png"] = decomp.decomposition_plot_bytes
                except Exception as e:
                    logger.warning("SHAP decomposition failed for %s: %s", gene, e)
        except Exception as e:
            logger.warning("SHAP decomposition module failed: %s", e)

    # v1 legacy SHAP (backward compat — kept for existing artifacts)
    if config.shap_enabled and not config.shap_decomposition_enabled:
        pct_features = {k: v for k, v in profile.items() if k.startswith("pct_")}
        for gene in GENES_V1:
            if config.model_backend == "mock":
                shap_arts = _generate_shap_mock(pct_features, gene)
            else:
                shap_arts = _generate_shap_real(pct_features, gene, config.mutation_model_dir)
            result.shap_artifacts.update(shap_arts)

    # Metrics
    elapsed = time.time() - t0
    result.metrics = {
        "processing_time_seconds": round(elapsed, 3),
        "device": config.device,
        "model_backend": config.model_backend,
        "model_profile": "ctranspath_fuzzyarcloss_v2_abmil_choquet",
        "pipeline_version": "2.0.0",
        "tile_size": config.tile_size,
        "n_tiles": result.n_tiles,
        "pattern_threshold": config.pattern_threshold,
        "mutation_threshold": config.mutation_threshold,
        "use_choquet": config.use_choquet,
        "top_k_tiles": config.top_k_tiles,
        "genes": config.genes,
        "seed": 42,
    }

    logger.info(
        "v2 Inference complete: %d tiles, predominant=%s (%.1f%%), mutations=%d genes, time=%.2fs",
        result.n_tiles, result.predominant_pattern,
        percentages.get(result.predominant_pattern, 0),
        len(result.mutation_report), elapsed,
    )

    result.quality_warnings = _IMAGE_QUALITY_WARNINGS.copy()

    _cleanup_wsi()
    return result


def _build_attention_overlay(
    img: Image.Image,
    tile_coords: list[tuple[int, int]],
    attention_weights: np.ndarray,
    top_k_indices: list[int],
    tile_size: int,
    alpha: int = 180,
) -> bytes:
    """Build attention overlay: original image + cyan fill + white contour borders.

    Top-K attended tiles are filled with semi-transparent cyan and outlined
    with white contour lines around the attended regions.
    """
    from PIL import ImageFilter
    import cv2

    w, h = img.size
    base_arr = np.array(img.convert("RGB")).astype(np.float32)

    heat = np.zeros((h, w), dtype=np.float32)

    render_size = max(tile_size * 2, min(w, h) // 35)
    half = render_size // 2
    ys = np.arange(render_size, dtype=np.float32) - half
    xs = np.arange(render_size, dtype=np.float32) - half
    gx, gy = np.meshgrid(xs, ys)
    sigma = render_size * 0.42
    gaussian = np.exp(-(gx ** 2 + gy ** 2) / (2 * sigma ** 2))

    top_set = set(top_k_indices)
    top_weights = attention_weights[list(top_k_indices)] if len(top_k_indices) > 0 else np.array([1.0])
    w_min, w_max = top_weights.min(), top_weights.max()
    w_range = w_max - w_min if w_max > w_min else 1e-8

    for idx, (tx, ty) in enumerate(tile_coords):
        if idx >= len(attention_weights):
            break
        if idx not in top_set:
            continue
        norm_w = (attention_weights[idx] - w_min) / w_range
        weight = 0.3 + 0.7 * norm_w

        cx, cy = tx + tile_size // 2, ty + tile_size // 2
        y1, x1 = max(0, cy - half), max(0, cx - half)
        y2 = min(h, cy + render_size - half)
        x2 = min(w, cx + render_size - half)
        gy1, gx1 = y1 - (cy - half), x1 - (cx - half)
        gy2, gx2 = gy1 + (y2 - y1), gx1 + (x2 - x1)
        if gy2 > gy1 and gx2 > gx1:
            heat[y1:y2, x1:x2] = np.maximum(
                heat[y1:y2, x1:x2], gaussian[gy1:gy2, gx1:gx2] * weight
            )

    if heat.max() > 0:
        heat /= heat.max()

    heat_blur = Image.fromarray((heat * 255).astype(np.uint8), "L")
    heat_blur = heat_blur.filter(ImageFilter.GaussianBlur(radius=max(render_size // 3, 6)))
    heat = np.array(heat_blur).astype(np.float32) / 255.0

    # Cyan fill on original
    cyan = np.stack([
        np.zeros_like(heat),
        heat * 255,
        heat * 255,
    ], axis=2)

    blend = heat[:, :, np.newaxis]
    blend_strength = np.clip(blend * 0.55, 0, 1)
    result = base_arr * (1 - blend_strength) + cyan * blend_strength
    result = np.clip(result, 0, 255).astype(np.uint8)

    # White contour lines around attended regions
    heat_smooth = cv2.GaussianBlur(heat, (0, 0), sigmaX=max(render_size // 2, 8))
    if heat_smooth.max() > 0:
        heat_smooth /= heat_smooth.max()

    for thresh, lw in [(0.15, 2), (0.35, 3), (0.55, 4)]:
        binary = (heat_smooth >= thresh).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (render_size * 0.5) ** 2
        for cnt in contours:
            if cv2.contourArea(cnt) < min_area:
                continue
            smooth_cnt = cv2.approxPolyDP(cnt, epsilon=render_size * 0.3, closed=True)
            cv2.drawContours(result, [smooth_cnt], -1, (255, 255, 255), lw, cv2.LINE_AA)

    buf = io.BytesIO()
    Image.fromarray(result, "RGB").save(buf, format="PNG")
    return buf.getvalue()


def _build_combined_overlay(
    img: Image.Image,
    tile_coords: list[tuple[int, int]],
    tile_labels: list[str],
    attention_weights: np.ndarray,
    top_k_indices: list[int],
    tile_size: int,
    pattern_alpha: int = 120,
) -> bytes:
    """Build combined overlay: pattern colours + white attention region contours.

    Patterns are shown as coloured regions (same as pattern overlay).
    Attention is shown as white contour lines tracing the boundaries of
    high-attention regions at multiple intensity levels.
    """
    from PIL import ImageFilter, ImageDraw
    import cv2

    w, h = img.size

    # 1) Build pattern colour overlay (same as _build_overlay)
    acc_r = np.zeros((h, w), dtype=np.float32)
    acc_g = np.zeros((h, w), dtype=np.float32)
    acc_b = np.zeros((h, w), dtype=np.float32)
    acc_w = np.zeros((h, w), dtype=np.float32)

    half = tile_size // 2
    ys = np.arange(tile_size, dtype=np.float32) - half
    xs = np.arange(tile_size, dtype=np.float32) - half
    gx, gy = np.meshgrid(xs, ys)
    sigma = tile_size * 0.38
    gaussian_kernel = np.exp(-(gx ** 2 + gy ** 2) / (2 * sigma ** 2))

    for (tx, ty), label in zip(tile_coords, tile_labels):
        color = PATTERN_PALETTE.get(label, (128, 128, 128))
        y1, y2 = ty, min(ty + tile_size, h)
        x1, x2 = tx, min(tx + tile_size, w)
        ky2, kx2 = y2 - ty, x2 - tx
        kern = gaussian_kernel[:ky2, :kx2]
        acc_r[y1:y2, x1:x2] += kern * color[0]
        acc_g[y1:y2, x1:x2] += kern * color[1]
        acc_b[y1:y2, x1:x2] += kern * color[2]
        acc_w[y1:y2, x1:x2] += kern

    mask = acc_w > 0
    for ch in (acc_r, acc_g, acc_b):
        ch[mask] /= acc_w[mask]

    r_img = Image.fromarray(np.clip(acc_r, 0, 255).astype(np.uint8), "L")
    g_img = Image.fromarray(np.clip(acc_g, 0, 255).astype(np.uint8), "L")
    b_img = Image.fromarray(np.clip(acc_b, 0, 255).astype(np.uint8), "L")
    alpha_arr = np.where(mask, pattern_alpha, 0).astype(np.uint8)
    a_img = Image.fromarray(alpha_arr, "L")

    overlay = Image.merge("RGBA", (r_img, g_img, b_img, a_img))
    blur_radius = max(tile_size // 6, 4)
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    base = img.convert("RGBA")
    combined = Image.alpha_composite(base, overlay).convert("RGB")
    result_arr = np.array(combined)

    # 2) Build attention heatmap for contour extraction
    render_size = max(tile_size * 2, min(w, h) // 35)
    r_half = render_size // 2
    r_ys = np.arange(render_size, dtype=np.float32) - r_half
    r_xs = np.arange(render_size, dtype=np.float32) - r_half
    r_gx, r_gy = np.meshgrid(r_xs, r_ys)
    r_sigma = render_size * 0.42
    r_gaussian = np.exp(-(r_gx ** 2 + r_gy ** 2) / (2 * r_sigma ** 2))

    heat = np.zeros((h, w), dtype=np.float32)
    top_set = set(top_k_indices)
    top_weights = attention_weights[list(top_k_indices)] if len(top_k_indices) > 0 else np.array([1.0])
    w_min, w_max = top_weights.min(), top_weights.max()
    w_range = w_max - w_min if w_max > w_min else 1e-8

    for idx, (tx, ty) in enumerate(tile_coords):
        if idx >= len(attention_weights) or idx not in top_set:
            continue
        norm_w = (attention_weights[idx] - w_min) / w_range
        weight = 0.3 + 0.7 * norm_w
        cx, cy = tx + tile_size // 2, ty + tile_size // 2
        y1, x1 = max(0, cy - r_half), max(0, cx - r_half)
        y2 = min(h, cy + render_size - r_half)
        x2 = min(w, cx + render_size - r_half)
        gy1, gx1 = y1 - (cy - r_half), x1 - (cx - r_half)
        gy2, gx2 = gy1 + (y2 - y1), gx1 + (x2 - x1)
        if gy2 > gy1 and gx2 > gx1:
            heat[y1:y2, x1:x2] = np.maximum(
                heat[y1:y2, x1:x2], r_gaussian[gy1:gy2, gx1:gx2] * weight
            )

    if heat.max() > 0:
        heat /= heat.max()

    heat_smooth = cv2.GaussianBlur(heat, (0, 0), sigmaX=max(render_size // 2, 8))
    if heat_smooth.max() > 0:
        heat_smooth /= heat_smooth.max()

    # 3) Extract contours at multiple threshold levels and draw white lines
    thresholds = [0.15, 0.30, 0.50, 0.70]
    line_widths = [1, 2, 3, 4]

    for thresh, lw in zip(thresholds, line_widths):
        binary = (heat_smooth >= thresh).astype(np.uint8) * 255
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = (render_size * 0.5) ** 2
        for cnt in contours:
            if cv2.contourArea(cnt) < min_area:
                continue
            smooth_cnt = cv2.approxPolyDP(cnt, epsilon=render_size * 0.3, closed=True)
            cv2.drawContours(result_arr, [smooth_cnt], -1, (255, 255, 255), lw, cv2.LINE_AA)

    buf = io.BytesIO()
    Image.fromarray(result_arr, "RGB").save(buf, format="PNG")
    return buf.getvalue()


def _real_tile_inference(tiles: list[tuple[int, int, Image.Image]], config: InferenceConfig) -> dict[str, list[float]]:
    """Run CTransPath Swin Tiny backbone + FuzzyArcLoss V2 cosine head on tiles.

    Each tile is resized to 224×224, normalised with ImageNet stats, given a
    4th channel of ones (mask = full ROI), and passed through CTransPath.
    Cosine similarity with the V2 class prototypes yields per-pattern scores.

    Also stores per-tile 512-d embeddings for downstream ABMIL/Choquet.
    """
    import torch
    import torch.nn.functional as F
    from torchvision import transforms

    device = config.device
    pipe = _load_real_pipeline(config.fuzzyarc_checkpoint, device)
    model = pipe["model"]
    head_weight = pipe["head_weight"]
    id2label = pipe["id2label"]
    s_scale = pipe["s_scale"]
    img_size = pipe["img_size"]  # 224

    normalize = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    scores: dict[str, list[float]] = {p: [] for p in PATTERNS}
    all_embeddings: list[np.ndarray] = []
    batch_size = 64 if device != "cpu" else 16
    logger.info("Tile inference: %d tiles, batch_size=%d, device=%s", len(tiles), batch_size, device)

    with torch.no_grad():
        for i in range(0, len(tiles), batch_size):
            batch_3ch = [normalize(t[2]) for t in tiles[i:i + batch_size]]
            mask_ch = torch.ones(1, img_size, img_size)
            batch_4ch = [torch.cat([img3, mask_ch], dim=0) for img3 in batch_3ch]
            batch_tensor = torch.stack(batch_4ch).to(device)

            embeddings = model(batch_tensor)                   # (B, 512)
            all_embeddings.append(embeddings.cpu().numpy())

            emb_norm = F.normalize(embeddings, dim=1)
            w_norm = F.normalize(head_weight, dim=1)           # (6, 512)
            cosine = emb_norm @ w_norm.t()                     # (B, 6)
            logits = cosine * s_scale
            probs = torch.softmax(logits, dim=1).cpu().numpy()  # (B, 6)

            for j in range(probs.shape[0]):
                for class_idx in range(probs.shape[1]):
                    label_name = id2label.get(class_idx, f"class_{class_idx}")
                    if label_name in scores:
                        scores[label_name].append(float(probs[j, class_idx]))

    _REAL_TILE_EMBEDDINGS.clear()
    _REAL_TILE_EMBEDDINGS["embeddings"] = np.concatenate(all_embeddings, axis=0)

    return scores


_REAL_TILE_EMBEDDINGS: dict[str, np.ndarray] = {}


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
