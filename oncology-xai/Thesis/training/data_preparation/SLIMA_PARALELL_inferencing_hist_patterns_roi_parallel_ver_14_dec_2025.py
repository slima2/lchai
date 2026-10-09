#!/usr/bin/env python
# coding: utf-8

# # SLIMA ROI Histologic Pattern Inference (Parallel CPU tiling + GPU batching)
# 
# This notebook implements:
# - **Parallel tile extraction and preprocessing on CPU** using `multiprocessing.Pool` and OpenSlide.
# - **Streaming, batched inference on GPU** using the trained ResNet-based model with 4-channel input (RGB + dummy mask).
# 
# Edit the configuration cell below with your paths and parameters, then run all cells.
# 

# In[1]:


import os
from pathlib import Path
import torch.serialization  # for add_safe_globals

# ----------------------
# CONFIGURATION
# ----------------------

# Path to the trained checkpoint (.pth)
MODEL_PATH = "/home/rapids/notebooks/slima/outputs/anorak_roi_acc6_v5/best_model_roi_acc6_v3_focus_precisionrecall.pth"

# Root directory containing .svs files (recursively scanned)
SVS_DIR = "/home/rapids/notebooks/sftp-uploads/slima"

# Directory where prediction CSVs will be stored
OUT_DIR = "/home/rapids/notebooks/slima/outputs/inference_results_parallel2"

# Tile size at level 0 (pixels)
TILE_SIZE = 384

# Batch size for GPU inference
BATCH_SIZE = 64

# Number of CPU workers for tile extraction; set to None to auto-select
NUM_WORKERS = None  # e.g., 8

# Device for inference: "cuda" or "cpu"
DEVICE = "cuda"

# Optional background filter threshold in [0,1].
# Tiles with a fraction of near-white pixels > BACKGROUND_THRESHOLD will be skipped.
BACKGROUND_THRESHOLD = 0.9  # or None to disable

# Optional limit on number of slides to process (for testing)
MAX_SLIDES = None  # e.g., 2

# FuzzyArc params
#Best trial: {'S_SCALE': 21.974440768151116, 'M_MARGIN': 0.2321722732484806, 'TAU': 0.6498209770940636}
S_SCALE = 21.974440768151116
M_MARGIN = 0.2321722732484806
TAU = 0.6498209770940636


# Ensure output directory exists
os.makedirs(OUT_DIR, exist_ok=True)

SVS_DIR, OUT_DIR, MODEL_PATH


# In[2]:


import numpy as np
from PIL import Image
import torch
from torch import nn
from torchvision import models
import openslide
import multiprocessing as mp
from typing import Dict, Tuple, List


import torch.nn.functional as F   # <-- ADD / ENSURE THIS LINE


# In[3]:


import openslide
from openslide import OpenSlideError
from openslide.lowlevel import OpenSlideUnsupportedFormatError


# In[4]:


print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

device = torch.device(DEVICE if torch.cuda.is_available() and DEVICE == "cuda" else "cpu")
print("Using device:", device)


# In[5]:


# ---------------------
# FuzzyArcLoss
# ---------------------
class FuzzyArcMarginProduct(nn.Module):
    def __init__(self, in_features, out_features, s=30.0, m=0.50, tau=0.10):
        super().__init__()
        self.s, self.m, self.tau = float(s), float(m), float(tau)
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    def forward(self, features, labels):
        x = F.normalize(features); W = F.normalize(self.weight).to(features.device)
        cos = (x @ W.t()).clamp(-1,1)
        idx = torch.arange(x.size(0), device=x.device)
        cos_y = cos[idx, labels]
        mu = torch.where(torch.abs(cos_y) >= self.tau, torch.abs(cos_y), torch.ones_like(cos_y))
        m_eff = self.m * mu
        cos_m, sin_m = torch.cos(m_eff), torch.sin(m_eff)
        sin_t = torch.sqrt((1 - cos_y**2).clamp(0,1))
        cos_theta_m = cos_y * cos_m - sin_t * sin_m
        logits = cos * self.s
        logits[idx, labels] = cos_theta_m * self.s
        return logits
    def infer_logits(self, feats):
        """
        Inference-time logits, no labels:
        - cosine similarity to class weights
        - scaled by s
        (No margin, no fuzzy membership, no CE.)
        """
        x = F.normalize(feats, dim=1)
        W = F.normalize(self.weight, dim=1)
        cos = torch.matmul(x, W.t())  # [B, num_classes]
        return cos * self.s

class FuzzyArcLoss(nn.Module):
    def __init__(self, in_features, out_features, s=30.0, m=0.50, tau=0.10, ce_weight=None):
        super().__init__()
        self.head = FuzzyArcMarginProduct(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = nn.CrossEntropyLoss(weight=ce_weight)
    def forward(self, feats, labels):
        logits = self.head(feats, labels)
        return self.ce(logits, labels), logits

    def infer_logits(self, feats):
        """
        Inference-time logits (no labels):
        delegates to the underlying FuzzyArcMarginProduct head.
        """
        return self.head.infer_logits(feats)




# In[6]:


def build_backbone(
    arch: str = "resnet101",
    embed_dim: int = 512,
    in_channels: int = 3,
    pretrained: bool = False,
) -> Tuple[nn.Module, int]:
    """
    ResNet backbone + embedding head:

      [ResNet (conv1 adapted to in_channels, fc->Identity)]
      -> BatchNorm1d(in_dim)
      -> Linear(in_dim, embed_dim, bias=False)
      -> BatchNorm1d(embed_dim)
    """
    if arch == "resnet50":
        backbone = models.resnet50(
            weights=models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        )
    elif arch == "resnet101":
        backbone = models.resnet101(
            weights=models.ResNet101_Weights.IMAGENET1K_V2 if pretrained else None
        )
    else:
        raise ValueError(f"Unsupported arch={arch}. Use 'resnet50' or 'resnet101'.")

    # Adapt conv1 to in_channels (3 or 4)
    if in_channels != 3:
        old = backbone.conv1
        backbone.conv1 = nn.Conv2d(
            in_channels,
            old.out_channels,
            kernel_size=old.kernel_size,
            stride=old.stride,
            padding=old.padding,
            bias=False,
        )
        with torch.no_grad():
            # copy RGB weights
            backbone.conv1.weight[:, :3] = old.weight
            if in_channels > 3:
                mean_rgb = old.weight.mean(dim=1, keepdim=True)
                backbone.conv1.weight[:, 3:in_channels] = mean_rgb.repeat(
                    1, in_channels - 3, 1, 1
                )

    in_dim = backbone.fc.in_features
    backbone.fc = nn.Identity()

    head = nn.Sequential(
        backbone,
        nn.BatchNorm1d(in_dim),
        nn.Linear(in_dim, embed_dim, bias=False),
        nn.BatchNorm1d(embed_dim),
    )
    return head, embed_dim



# In[7]:


def build_model_and_head_from_checkpoint(checkpoint: dict, device: torch.device):
    cfg       = checkpoint["config"]
    label2id  = checkpoint["label2id"]
    id2label  = checkpoint["id2label"]
    n_classes = len(label2id)

    arch      = cfg.get("ARCH", "resnet101")
    embed_dim = int(cfg.get("EMBED_DIM", 512))
    use_mask  = bool(cfg.get("USE_MASK_AS_CHANNEL", False))
    in_ch     = 4 if use_mask else 3

    # Backbone (same as training)
    model, _ = build_backbone(
        arch=arch,
        embed_dim=embed_dim,
        in_channels=in_ch,
        pretrained=False,
    )

    # Load backbone weights
    raw_model_state = checkpoint["model_state"]
    model_state = {k.replace("module.", ""): v for k, v in raw_model_state.items()}
    model.load_state_dict(model_state, strict=False)

    # Rebuild FuzzyArcLoss head with same hyperparams
    # loss_head = FuzzyArcLoss(
    #     embed_dim,
    #     n_classes,
    #     s=cfg.get("S_SCALE", 30.0),
    #     m=cfg.get("M_MARGIN", 0.5),
    #     tau=cfg.get("TAU", 0.1),
    #     ce_weight=None,
    # )

    loss_head = FuzzyArcLoss(
        embed_dim,
        n_classes,
        s=S_SCALE,
        m=M_MARGIN,
        tau=TAU,
        ce_weight=None,
    )


    raw_head_state = checkpoint["head_state"]
    head_state = {k.replace("module.", ""): v for k, v in raw_head_state.items()}
    loss_head.load_state_dict(head_state, strict=False)

    model.to(device).eval()
    loss_head.to(device).eval()

    return model, loss_head, cfg, label2id, id2label


# In[8]:


torch.serialization.add_safe_globals([
    np.core.multiarray.scalar,
    np.dtype,
    np.dtypes.Float64DType,
])


# In[9]:


# Load checkpoint and rebuild model
#print("Loading checkpoint from:", MODEL_PATH)
#checkpoint = torch.load(MODEL_PATH, map_location=device)
# checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)

# model, cfg, IN_CHANNELS = build_model_from_checkpoint(checkpoint, device=device)

print("Loading checkpoint from:", MODEL_PATH)
checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
model, loss_head, cfg, label2id, id2label = build_model_and_head_from_checkpoint(checkpoint, device=device)
IN_CHANNELS = 4 if cfg.get("USE_MASK_AS_CHANNEL", False) else 3
IMG_SIZE    = int(cfg.get("IMG_SIZE", TILE_SIZE))
N_CLASSES   = len(label2id)


# In[10]:


# After: model, cfg, IN_CHANNELS = build_model_from_checkpoint(...)

if device.type == "cuda" and torch.cuda.device_count() > 1:
    print(f"Using DataParallel over {torch.cuda.device_count()} GPUs")
    model = nn.DataParallel(model)


# In[11]:


# Sanity checks:
print("First model parameter device:", next(model.parameters()).device)
print("Visible GPUs:", torch.cuda.device_count())
print("Initial GPU memory allocated (MB):", torch.cuda.memory_allocated() / 1024**2)


# In[12]:


# Use IMG_SIZE from config if available; else TILE_SIZE as default
IMG_SIZE = int(cfg.get("IMG_SIZE", TILE_SIZE))
print(f"Using IMG_SIZE={IMG_SIZE} for model input, TILE_SIZE={TILE_SIZE} for extraction.")


# In[13]:


# ------------------------------
# Worker-side globals
# ------------------------------
_worker_slide = None
_worker_tile_size = None
_worker_img_size = None
_worker_background_thr = None
_worker_means = None
_worker_stds = None
_worker_in_channels = None

def worker_init(
    slide_path: str,
    tile_size: int,
    img_size: int,
    background_threshold: float,
    in_channels: int,
) -> None:
    """
    Initializer for each worker process: open WSI and store parameters.
    """
    global _worker_slide, _worker_tile_size, _worker_img_size
    global _worker_background_thr, _worker_means, _worker_stds, _worker_in_channels

    _worker_slide = openslide.OpenSlide(slide_path)
    _worker_tile_size = tile_size
    _worker_img_size = img_size
    _worker_background_thr = background_threshold
    _worker_in_channels = in_channels

    _worker_means = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    _worker_stds = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def worker_process_tile(coord: Tuple[int, int]):
    """
    Worker function (CPU-only):

    1. Read tile from OpenSlide.
    2. Optional background filter.
    3. Resize to img_size.
    4. Convert to normalized CHW array.
    5. If in_channels=4 → append a zero mask channel.

    Returns:
        ((x, y), np.ndarray[shape=(in_channels, img_size, img_size), dtype=float32])
        or None if tile is skipped (background).
    """
    global _worker_slide, _worker_tile_size, _worker_img_size
    global _worker_background_thr, _worker_means, _worker_stds, _worker_in_channels

    x, y = coord
    tile = _worker_slide.read_region(
        (x, y), 0, (_worker_tile_size, _worker_tile_size)
    ).convert("RGB")

    # Background filter (simple near-white heuristic)
    if _worker_background_thr is not None:
        arr_full = np.asarray(tile, dtype=np.float32) / 255.0  # H, W, 3
        near_white = np.all(arr_full > 0.9, axis=2)
        frac = float(near_white.mean())
        if frac > _worker_background_thr:
            return None  # skip

    # Resize if needed
    if _worker_img_size != _worker_tile_size:
        tile = tile.resize((_worker_img_size, _worker_img_size), Image.BILINEAR)

    arr = np.asarray(tile, dtype=np.float32) / 255.0  # H, W, 3
    # Normalize
    arr = (arr - _worker_means) / _worker_stds  # broadcast over H,W

    # To CHW (3, H, W)
    chw = np.transpose(arr, (2, 0, 1))

    if _worker_in_channels == 3:
        chwX = chw
    elif _worker_in_channels == 4:
        mask = np.zeros((_worker_img_size, _worker_img_size), dtype=np.float32)
        chwX = np.concatenate([chw, mask[None, :, :]], axis=0)  # (4, H, W)
    else:
        raise ValueError(f"Unsupported in_channels={_worker_in_channels} in worker.")

    return (x, y), chwX


# In[14]:


@torch.no_grad()
def run_inference_on_slide_parallel(
    slide_path: Path,
    model: nn.Module,
    device: torch.device,
    tile_size: int,
    img_size: int,
    batch_size: int,
    num_workers: int,
    background_threshold: float,
    in_channels: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    For a single slide:

    - Main process: compute tile coordinates, create multiprocessing Pool.
    - Workers: read & preprocess tiles (CPU, OpenSlide + NumPy).
    - Main process: accumulates worker outputs into batches, moves to GPU, runs model.

    Returns:
        coords: (N, 2) array of (x, y) at level 0
        preds:  (N,) array of predicted class indices (argmax)
    """
    slide_path_str = str(slide_path)
    print(f"\n=== Processing slide: {slide_path_str} ===")

    # Open once in main just for dimensions
    #slide = openslide.OpenSlide(slide_path_str)
    try:
        slide = openslide.OpenSlide(slide_path_str)
    except OpenSlideUnsupportedFormatError as e:
        print(f"[SKIP] Unsupported or missing WSI: {slide_path_str} ({e})")
        # Return empty results so caller can skip saving
        return np.empty((0, 2), dtype=int), np.empty((0,), dtype=int)
    except OpenSlideError as e:
        print(f"[SKIP] OpenSlideError on {slide_path_str}: {e}")
        return np.empty((0, 2), dtype=int), np.empty((0,), dtype=int)
    except Exception as e:
        print(f"[SKIP] Unexpected error opening {slide_path_str}: {e}")
        return np.empty((0, 2), dtype=int), np.empty((0,), dtype=int)




    width, height = slide.level_dimensions[0]
    slide.close()
    print(f"Slide dimensions (level 0): {width} x {height}")

    # Build coordinate list at level 0
    coords_tasks: List[Tuple[int, int]] = []
    total_tiles = len(coords_tasks)
    processed = 0  # <-- init here


    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            coords_tasks.append((x, y))

    print(f"Total tiles (before background filter): {len(coords_tasks)}")

    # Prepare multiprocessing context
    ctx = mp.get_context("spawn")
    if num_workers is None:
        num_workers = min(mp.cpu_count(), 8)
    print(f"Using {num_workers} worker process(es) for tile extraction.")

    all_coords: List[Tuple[int, int]] = []
    all_preds: List[int] = []
    batch_imgs: List[torch.Tensor] = []
    batch_coords: List[Tuple[int, int]] = []

    with ctx.Pool(
        processes=num_workers,
        initializer=worker_init,
        initargs=(
            slide_path_str,
            tile_size,
            img_size,
            background_threshold,
            in_channels,
        ),
    ) as pool:
        # stream worker outputs into GPU batches
        for res in pool.imap_unordered(worker_process_tile, coords_tasks, chunksize=32):
            if res is None:
                continue  # skipped due to background
            processed += 1
            if processed % 500 == 0:
                print(f"[TILES] {processed}/{len(coords_tasks)} tiles preprocessed")




            (x, y), chwX = res

            # chwX: (C, H, W), float32 CPU → torch tensor
            batch_imgs.append(torch.from_numpy(chwX))
            batch_coords.append((x, y))

            if len(batch_imgs) == batch_size:
                # batch = torch.stack(batch_imgs).to(device, non_blocking=True)
                # logits = model(batch)
                # preds = torch.argmax(logits, dim=1).cpu().numpy()
                batch = torch.stack(batch_imgs).to(device, non_blocking=True)
                print(f"[GPU] Running batch of {batch.shape[0]} tiles on {device}")

                # Backbone → features
                feats = model(batch)                        # [B, EMBED_DIM]
                # FuzzyArc head → class logits
                logits = loss_head.infer_logits(feats)      # [B, N_CLASSES]
                # Optionally: probs = torch.softmax(logits, dim=1)
                preds  = torch.argmax(logits, dim=1).cpu().numpy()  # values in [0..N_CLASSES-1]


                all_coords.extend(batch_coords)
                all_preds.extend(preds.tolist())

                batch_imgs.clear()
                batch_coords.clear()


        # Flush last partial batch
        if batch_imgs:
            # batch = torch.stack(batch_imgs).to(device, non_blocking=True)
            # logits = model(batch)
            # preds = torch.argmax(logits, dim=1).cpu().numpy()
            batch = torch.stack(batch_imgs).to(device, non_blocking=True)
            # Backbone → features
            feats = model(batch)                        # [B, EMBED_DIM]
            # FuzzyArc head → class logits
            logits = loss_head.infer_logits(feats)      # [B, N_CLASSES]
            # Optionally: probs = torch.softmax(logits, dim=1)
            preds  = torch.argmax(logits, dim=1).cpu().numpy()  # values in [0..N_CLASSES-1]


            all_coords.extend(batch_coords)
            all_preds.extend(preds.tolist())

    coords_arr = np.array(all_coords, dtype=np.int32)
    preds_arr = np.array(all_preds, dtype=np.int64)
    print(
        f"Tiles classified (after background filter): {coords_arr.shape[0]} "
        f"out of {len(coords_tasks)} total."
    )
    counts, freqs = summarize_slide_distribution(preds_arr, id2label)

    return coords_arr, preds_arr


def save_predictions_csv(
    coords: np.ndarray,
    preds: np.ndarray,
    out_path: Path,
) -> None:
    """
    Save tile-level predictions for one slide to CSV:

      x,y,pred_class
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if coords.shape[0] == 0:
        print(f"WARNING: no tiles classified for {out_path.stem}. Writing empty file.")
        with out_path.open("w") as f:
            f.write("x,y,pred_class\n")
        return

    arr = np.column_stack([coords, preds])
    header = "x,y,pred_class"
    np.savetxt(out_path, arr, fmt="%d", delimiter=",", header=header, comments="")
    print(f"Saved predictions to: {out_path}")


# In[15]:


# Main driver: scan SVS_DIR and process slides one by one

def run_all_slides():
    svs_root = Path(SVS_DIR)
    out_root = Path(OUT_DIR)
    out_root.mkdir(parents=True, exist_ok=True)

    # Discover .svs
    svs_files: List[Path] = []
    for root, _, files in os.walk(svs_root):
        for name in files:
            if name.lower().endswith(".svs"):
                svs_files.append(Path(root) / name)

    svs_files.sort()
    print(f"Found {len(svs_files)} slide(s) under {svs_root}")

    if MAX_SLIDES is not None:
        svs_files_limited = svs_files[: MAX_SLIDES]
        print(f"Restricting to first {len(svs_files_limited)} slides due to MAX_SLIDES={MAX_SLIDES}.")
    else:
        svs_files_limited = svs_files

    if not svs_files_limited:
        print("No .svs files found. Nothing to do.")
        return

    for svs_path in svs_files_limited:
        out_name = f"{svs_path.stem}_tiles_{TILE_SIZE}_predictions.csv"
        out_path = out_root / out_name

        # 1) Resume: skip slides already processed
        if out_path.exists():
            print(f"[RESUME] Skipping {svs_path}, output already exists: {out_path}")
            continue

        print(f"Processing slide: {svs_path}")



        coords, preds = run_inference_on_slide_parallel(
            slide_path=svs_path,
            model=model,
            device=device,
            tile_size=TILE_SIZE,
            img_size=IMG_SIZE,
            batch_size=BATCH_SIZE,
            num_workers=NUM_WORKERS,
            background_threshold=BACKGROUND_THRESHOLD,
            in_channels=IN_CHANNELS,
        )

        # 2) Skip saving if slide failed or produced no tiles
        if coords.size == 0:
            print(f"[WARN] No predictions for {svs_path} (likely unsupported or empty). Skipping save.")
            continue

        # out_name = f"{svs_path.stem}_tiles_{TILE_SIZE}_predictions.csv"
        # out_path = out_root / out_name
        save_predictions_csv(coords, preds, out_path)

    print("All slides processed.")





# In[16]:


def summarize_slide_distribution(preds_arr: np.ndarray, id2label: dict):
    n_classes = len(id2label)
    counts = np.bincount(preds_arr, minlength=n_classes)
    total  = counts.sum()
    freqs  = counts / max(1, total)

    print("Tile distribution for this slide:")
    for cid in range(n_classes):
        label = id2label.get(cid, str(cid))
        print(
            f"  class {cid} ({label}): "
            f"{counts[cid]} tiles ({freqs[cid]*100:.2f}%)"
        )
    return counts, freqs


# In[ ]:


# Uncomment the next line to start processing immediately when running this cell:
#run_all_slides()
if __name__ == "__main__":
    import multiprocessing as mp

    # Use spawn to be safe with PyTorch + CUDA
    mp.set_start_method("spawn", force=True)

    run_all_slides()


# In[ ]:




