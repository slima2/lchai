#!/usr/bin/env python3
"""
SLIMA TCGA Histologic Pattern Inference — v6 GPU-Optimized (Feb 2026)
=====================================================================
Maximizes throughput on multi-GPU (6x H100 80GB):

  SPEED OPTIMIZATIONS:
  1. Prefetch DataLoader: GPU never waits — next batch already in memory
  2. FP16 inference:      2x throughput on H100 tensor cores
  3. Multi-GPU parallel:  Each GPU processes different slides → 6x throughput
  4. Large batches:       bs=512 (CTransPath is only 28M params ~ 4GB)
  5. Pin memory:          Zero-copy CPU→GPU transfer via DMA
  6. Persistent workers:  No fork overhead between batches

  MODEL (K-fold validated — 92.31% ± 2.04 macro-F1, #1 of 18 methods):
  - CTransPath backbone (Swin-Tiny + ConvStem)
  - FuzzyArcLoss V2 (inverse fuzzy membership): s=46.10, m=0.518, tau=0.448
  - 4-channel input: RGB + Otsu tissue mask
  - Margin-free cosine logits for prediction (NOT margin-distorted)

  CHECKPOINT:
  The ablation script (rev 11+) saves: best_fuzzyarcloss_v2.pth

  Expected: ~500 TCGA slides in 1.5-3 hours on 6x H100
"""

# ── CRITICAL: Limit threads BEFORE any import (prevents OpenBLAS thread explosion) ──
import os
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"
os.environ["VECLIB_MAXIMUM_THREADS"] = "2"

import sys, math, time, csv
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Dict, Tuple, List

import torch
import torch.nn as nn
import torch.nn.functional as F
import multiprocessing as mp
from torch.utils.data import Dataset, DataLoader

try:
    import timm
except ImportError:
    print("[ERROR] timm required. pip install timm"); sys.exit(1)
try:
    import openslide
    from openslide import OpenSlideError
    from openslide.lowlevel import OpenSlideUnsupportedFormatError
except ImportError:
    print("[ERROR] openslide-python required."); sys.exit(1)


# ============================================================
# CONFIGURATION
# ============================================================

# Ablation winner: V2 Optuna (K-fold validated: 92.31% ± 2.04). Artefact 1 checkpoint
# (Thesis/models/best_fuzzyarcloss_v2.pth.xz, decompressed); prob_* headers come from its id2label.
MODEL_PATH     = "/home/rapids/notebooks/slima/models/best_fuzzyarcloss_v2.pth"
CTRANSPATH_CKPT = "/home/rapids/notebooks/slima/models/ctranspath.pth"
SVS_DIR        = "/home/rapids/notebooks/slima/TGCA LUAD LUSC/TCGA LUAD LUSC"
OUT_DIR        = "/home/rapids/notebooks/slima/outputs/inference_results_v2_ctranspath_fast"

TILE_SIZE            = 224
BACKGROUND_THRESHOLD = 0.9
BATCH_SIZE           = 512
NUM_TILE_WORKERS     = 4     # 4 per GPU × 6 GPUs = 24 processes (safe limit)
PREFETCH_FACTOR      = 4
USE_FP16             = True
NUM_GPUS             = None   # None = auto-detect
MAX_SLIDES           = None

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# CTransPath BACKBONE
# ============================================================

class ConvStem(nn.Module):
    def __init__(self, in_chans=3, embed_dim=96):
        super().__init__()
        d1, d2 = embed_dim // 8, embed_dim // 4
        self.proj = nn.Sequential(
            nn.Conv2d(in_chans, d1, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(d1), nn.GELU(),
            nn.Conv2d(d1, d2, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(d2), nn.GELU(),
            nn.Conv2d(d2, embed_dim, 1, bias=False), nn.BatchNorm2d(embed_dim),
        )
        self.norm = nn.LayerNorm(embed_dim)

    def forward(self, x):
        return self.norm(self.proj(x).permute(0, 2, 3, 1))


class CTransPathBackbone(nn.Module):
    def __init__(self, checkpoint_path=None, in_channels=3):
        super().__init__()
        self.model = timm.create_model('swin_tiny_patch4_window7_224', pretrained=False, num_classes=0)
        self.model.patch_embed = ConvStem(in_chans=3, embed_dim=96)
        self.out_features = self.model.num_features

        if checkpoint_path and os.path.exists(checkpoint_path):
            self._load_ckpt(checkpoint_path)

        if in_channels != 3:
            old = self.model.patch_embed.proj[0]
            new = nn.Conv2d(in_channels, old.out_channels, old.kernel_size, old.stride, old.padding, bias=False)
            with torch.no_grad():
                new.weight[:, :3] = old.weight
                new.weight[:, 3:] = old.weight.mean(dim=1, keepdim=True)
            self.model.patch_embed.proj[0] = new

    def _load_ckpt(self, path):
        ckpt = torch.load(path, map_location='cpu', weights_only=False)
        sd = ckpt.get('model', ckpt.get('state_dict', ckpt)) if isinstance(ckpt, dict) else ckpt
        remap = {}
        for k, v in sd.items():
            if any(s in k for s in ('head.', 'fc.', 'attn_mask', 'relative_position_index')):
                continue
            nk = k
            for i in range(3):
                if f'layers.{i}.downsample.' in k:
                    nk = k.replace(f'layers.{i}.downsample.', f'layers.{i+1}.downsample.')
                    break
            remap[nk] = v
        ms = self.model.state_dict()
        filt = {k: v for k, v in remap.items() if k in ms and v.shape == ms[k].shape}
        if filt:
            self.model.load_state_dict(filt, strict=False)

    def forward(self, x):
        return self.model(x)


# ============================================================
# FuzzyArcLoss V2 HEAD (inference only — just cosine logits)
# ============================================================

class FuzzyArcLossV2Head(nn.Module):
    def __init__(self, in_features, out_features, s=30.0):
        super().__init__()
        self.s = s
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)

    def infer_logits(self, feats):
        return F.normalize(feats, dim=1) @ F.normalize(self.weight, dim=1).t() * self.s


# ============================================================
# TILE DATASET (for prefetch DataLoader)
# ============================================================

MEANS = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STDS  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class SlideTileDataset(Dataset):
    """Reads tiles on-the-fly from OpenSlide. Each worker opens its own handle."""
    def __init__(self, slide_path, coords, tile_size=224, bg_thr=0.9, in_channels=4):
        self.slide_path = slide_path
        self.coords = coords
        self.tile_size = tile_size
        self.bg_thr = bg_thr
        self.in_channels = in_channels
        self._slide = None

    def __len__(self):
        return len(self.coords)

    def __getitem__(self, idx):
        if self._slide is None:
            self._slide = openslide.OpenSlide(self.slide_path)

        x, y = self.coords[idx]
        tile = self._slide.read_region((x, y), 0, (self.tile_size, self.tile_size)).convert("RGB")
        arr = np.asarray(tile, dtype=np.float32) / 255.0

        # Background check
        if (arr.mean(axis=2) > 0.9).mean() > self.bg_thr:
            return torch.empty(0), x, y, False

        chw = ((arr - MEANS) / STDS).transpose(2, 0, 1)

        if self.in_channels == 4:
            gray = np.asarray(tile.convert("L"), dtype=np.uint8)
            mask = (gray < gray.mean()).astype(np.float32)
            if mask.mean() < 0.2:
                mask[:] = 1.0
            chw = np.concatenate([chw, mask[None]], axis=0)

        return torch.from_numpy(chw.copy()), x, y, True


def _collate(batch):
    """Filter out background tiles at collation time."""
    tensors, xs, ys, valids = zip(*batch)
    idx = [i for i, v in enumerate(valids) if v]
    if not idx:
        return torch.empty(0), [], [], 0
    return torch.stack([tensors[i] for i in idx]), \
           [xs[i] for i in idx], [ys[i] for i in idx], len(idx)


# ============================================================
# BUILD MODEL
# ============================================================

def build_model(ckpt_path, ct_ckpt, device):
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    cfg      = ckpt.get('config', {})
    label2id = ckpt.get('label2id', {})
    id2label = ckpt.get('id2label', {v: k for k, v in label2id.items()})
    n_cls    = len(label2id)
    embed    = int(cfg.get('EMBED_DIM', 512))
    in_ch    = 4 if cfg.get('USE_MASK_AS_CHANNEL', True) else 3
    img_sz   = int(cfg.get('IMG_SIZE', 224))
    s        = float(cfg.get('S_SCALE', 30.0))

    print(f"  {n_cls} classes: {list(label2id.keys())}")
    print(f"  embed={embed}, in_ch={in_ch}, img={img_sz}, s={s}")

    backbone = CTransPathBackbone(checkpoint_path=ct_ckpt, in_channels=in_ch)
    proj = nn.Sequential(
        nn.Linear(backbone.out_features, embed),
        nn.LayerNorm(embed), nn.GELU(), nn.Dropout(0.0),
    )
    model = nn.Sequential(backbone, proj)

    raw = ckpt.get('model', ckpt.get('model_state', {}))
    model.load_state_dict({k.replace("module.", ""): v for k, v in raw.items()}, strict=False)

    head = FuzzyArcLossV2Head(embed, n_cls, s=s)
    raw_loss = ckpt.get('loss_fn', ckpt.get('head_state', {}))
    for k, v in raw_loss.items():
        if k.replace("module.", "") in ('head.weight', 'weight'):
            head.weight.data.copy_(v); break

    model.to(device).eval()
    head.to(device).eval()
    if USE_FP16:
        model.half(); head.half()
        print(f"  FP16 enabled")
    print(f"  Model ready on {device}")
    return model, head, label2id, id2label, img_sz, in_ch


# ============================================================
# PROCESS ONE SLIDE
# ============================================================

@torch.no_grad()
def process_slide(slide_path, model, head, device, img_size, in_ch, id2label, out_root):
    out_path = Path(out_root) / f"{slide_path.stem}_tiles_{TILE_SIZE}_v2.csv"
    if out_path.exists():
        return f"[SKIP] {slide_path.name}"

    try:
        s = openslide.OpenSlide(str(slide_path))
        w, h = s.level_dimensions[0]; s.close()
    except Exception as e:
        return f"[ERR] {slide_path.name}: {e}"

    coords = [(x, y) for y in range(0, h, TILE_SIZE) for x in range(0, w, TILE_SIZE)]

    ds = SlideTileDataset(str(slide_path), coords, TILE_SIZE, BACKGROUND_THRESHOLD, in_ch)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False,
                        num_workers=NUM_TILE_WORKERS, pin_memory=True,
                        prefetch_factor=PREFETCH_FACTOR, persistent_workers=True,
                        collate_fn=_collate, drop_last=False)

    ax, ay, ap, aprob = [], [], [], []
    t0 = time.time()

    for imgs, vx, vy, cnt in loader:
        if cnt == 0: continue
        if USE_FP16: imgs = imgs.half()
        imgs = imgs.to(device, non_blocking=True)
        logits = head.infer_logits(model(imgs))
        probs  = torch.softmax(logits.float(), dim=1)
        preds  = logits.argmax(dim=1)
        ax.extend(vx); ay.extend(vy)
        ap.extend(preds.cpu().tolist())
        aprob.append(probs.cpu().numpy())

    elapsed = time.time() - t0
    n = len(ap)
    if n == 0:
        return f"[EMPTY] {slide_path.name}"

    # Save CSV
    probs_arr = np.vstack(aprob)
    n_cls = len(id2label)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', newline='') as f:
        wr = csv.writer(f)
        hdr = ['x', 'y', 'pred_class', 'pred_label']
        for c in range(n_cls):
            hdr.append(f'prob_{id2label.get(c, id2label.get(str(c), str(c)))}')
        wr.writerow(hdr)
        for i in range(n):
            lbl = id2label.get(ap[i], id2label.get(str(ap[i]), str(ap[i])))
            wr.writerow([ax[i], ay[i], ap[i], lbl] + [f"{p:.4f}" for p in probs_arr[i]])

    # Summary
    counts = np.bincount(ap, minlength=n_cls)
    freqs  = counts / max(1, counts.sum())
    dist = " | ".join(f"{id2label.get(c, id2label.get(str(c),''))}:{freqs[c]*100:.0f}%"
                       for c in range(n_cls))
    return f"[OK] {slide_path.name}: {n}/{len(coords)} tiles, {elapsed:.0f}s ({n/max(elapsed,.01):.0f} t/s) | {dist}"


# ============================================================
# GPU WORKER (one per GPU)
# ============================================================

def gpu_worker(gpu_id, slides, out_root, ckpt_path, ct_ckpt):
    device = torch.device(f"cuda:{gpu_id}")
    torch.cuda.set_device(device)
    print(f"\n[GPU {gpu_id}] Loading model...")
    model, head, l2i, i2l, img_sz, in_ch = build_model(ckpt_path, ct_ckpt, device)
    print(f"[GPU {gpu_id}] Processing {len(slides)} slides\n")
    for i, sp in enumerate(slides):
        msg = process_slide(sp, model, head, device, img_sz, in_ch, i2l, out_root)
        print(f"  [GPU {gpu_id}] ({i+1}/{len(slides)}) {msg}")
        sys.stdout.flush()


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  SLIMA TCGA Inference v6 — GPU-Optimized")
    print("  CTransPath + FuzzyArcLoss V2 (94.75% F1)")
    print("=" * 70)

    ng = NUM_GPUS or (torch.cuda.device_count() if torch.cuda.is_available() else 1)
    ng = min(ng, max(1, torch.cuda.device_count()))
    gname = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"\n{ng} × {gname}")
    print(f"bs={BATCH_SIZE}, workers={NUM_TILE_WORKERS}/GPU, prefetch={PREFETCH_FACTOR}, fp16={USE_FP16}")

    if not os.path.exists(MODEL_PATH):
        print(f"\n[ERROR] Checkpoint not found: {MODEL_PATH}")
        print(f"  Run the ablation script (rev 11+) first — it saves best_<loss>.pth")
        print(f"  Look for: best_fuzzyarcloss_v2.pth in your ablation output dir")
        sys.exit(1)

    svs_root = Path(SVS_DIR)
    out_root = Path(OUT_DIR)
    all_svs = sorted(svs_root.rglob("*.svs"))
    if MAX_SLIDES: all_svs = all_svs[:MAX_SLIDES]

    remaining = [s for s in all_svs
                 if not (out_root / f"{s.stem}_tiles_{TILE_SIZE}_v2.csv").exists()]
    print(f"\n{len(all_svs)} slides found, {len(all_svs)-len(remaining)} done, {len(remaining)} remaining")

    if not remaining:
        print("All done!"); return

    t0 = time.time()
    if ng == 1:
        gpu_worker(0, remaining, str(out_root), MODEL_PATH, CTRANSPATH_CKPT)
    else:
        assign = [[] for _ in range(ng)]
        for i, sp in enumerate(remaining):
            assign[i % ng].append(sp)
        print(f"\nDistribution: {[len(a) for a in assign]} slides per GPU")
        ctx = mp.get_context("spawn")
        procs = [ctx.Process(target=gpu_worker, args=(g, assign[g], str(out_root), MODEL_PATH, CTRANSPATH_CKPT))
                 for g in range(ng) if assign[g]]
        for p in procs: p.start()
        for p in procs: p.join()

    elapsed = time.time() - t0
    print(f"\nDONE: {len(remaining)} slides in {elapsed/60:.1f} min ({elapsed/max(1,len(remaining)):.1f}s/slide)")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
