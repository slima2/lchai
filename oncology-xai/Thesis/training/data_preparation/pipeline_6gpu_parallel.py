#!/usr/bin/env python3
"""
SLIMA — 6-GPU Parallel Post-Download Pipeline
==============================================
Watches data/slides/ for newly downloaded SVS files and processes them
through the full pipeline on 6 GPUs in parallel:

  Stage 1 — Pattern inference  (FuzzyArcLoss V2 → per-tile probabilities CSV)
  Stage 2 — CSV → NPY          (pattern_probs.npy + pattern_labels.npy)
  Stage 3 — Embedding extract  (CTransPath 512-d → embeddings.npy)

Each newly downloaded SVS is queued automatically.
Resumes from wherever it left off if interrupted.

Usage:
  nohup python3 pipeline_6gpu_parallel.py > output_pipeline_6gpu.txt 2>&1 &
  tail -f output_pipeline_6gpu.txt
"""

# ── Thread safety BEFORE any import ──────────────────────────────────────────
import os
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"]      = "2"
os.environ["OMP_NUM_THREADS"]      = "2"
os.environ["NUMEXPR_NUM_THREADS"]  = "2"

import sys, csv, time, json, math
import numpy as np
import multiprocessing as mp
from pathlib import Path
from typing import List, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

try:
    import timm
except ImportError:
    os.system("pip install timm --break-system-packages"); import timm
try:
    import openslide
    from openslide import OpenSlideError
except ImportError:
    print("[ERROR] openslide-python required."); sys.exit(1)
from PIL import Image

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION  — edit paths here
# ══════════════════════════════════════════════════════════════════════════════
BASE           = Path("/home/rapids/notebooks/slima")
SLIDES_DIR     = BASE / "data" / "slides"          # where SVS folders land
INFERENCE_OUT  = BASE / "outputs" / "inference_pipeline_6gpu"   # tile CSVs
MODEL_PATH     = BASE / "outputs/ablation_study_v16_optuna/best_fuzzyarcloss_v2.pth"
CTRANSPATH_CKPT= BASE / "models/ctranspath.pth"
LOG_FILE       = BASE / "TGCA MAF" / "pipeline_progress.tsv"

NUM_GPUS          = 6
BATCH_SIZE        = 512
NUM_TILE_WORKERS  = 4      # per GPU
PREFETCH_FACTOR   = 4
USE_FP16          = True
TILE_SIZE         = 224
BG_THRESHOLD      = 0.9
POLL_INTERVAL_SEC = 60     # seconds to wait before re-scanning for new SVS

INFERENCE_OUT.mkdir(parents=True, exist_ok=True)
(BASE / "TGCA MAF").mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
#  MODEL ARCHITECTURE  (identical to SLIMA v6)
# ══════════════════════════════════════════════════════════════════════════════
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
    def __init__(self, in_channels=3):
        super().__init__()
        self.model = timm.create_model('swin_tiny_patch4_window7_224',
                                       pretrained=False, num_classes=0)
        self.model.patch_embed = ConvStem(in_chans=3, embed_dim=96)
        self.out_features = self.model.num_features
        # NOTE: do NOT load ctranspath.pth here — architecture may differ from
        # the timm variant. The fine-tuned best_fuzzyarcloss_v2.pth already
        # contains backbone + projection weights; they get loaded in build_model.
        if in_channels != 3:
            old = self.model.patch_embed.proj[0]
            new = nn.Conv2d(in_channels, old.out_channels, old.kernel_size,
                            old.stride, old.padding, bias=False)
            with torch.no_grad():
                new.weight[:, :3] = old.weight
                new.weight[:, 3:] = old.weight.mean(dim=1, keepdim=True)
            self.model.patch_embed.proj[0] = new
    def forward(self, x):
        return self.model(x)

class FuzzyArcLossV2Head(nn.Module):
    def __init__(self, in_features, out_features, s=30.0):
        super().__init__()
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.s = s
    def infer_logits(self, feats):
        return self.s * F.linear(F.normalize(feats.float(), dim=1),
                                 F.normalize(self.weight.float(), dim=1))

def build_model(device):
    ckpt     = torch.load(MODEL_PATH, map_location='cpu', weights_only=False)
    cfg      = ckpt.get('config', {})
    label2id = ckpt.get('label2id', {})
    id2label = ckpt.get('id2label', {v: k for k, v in label2id.items()})
    n_cls    = len(label2id)
    embed    = int(cfg.get('EMBED_DIM', 512))
    in_ch    = 4 if cfg.get('USE_MASK_AS_CHANNEL', True) else 3
    img_sz   = int(cfg.get('IMG_SIZE', 224))
    s        = float(cfg.get('S_SCALE', 30.0))

    # Build architecture — weights come entirely from fine-tuned checkpoint below
    backbone = CTransPathBackbone(in_channels=in_ch)
    proj = nn.Sequential(
        nn.Linear(backbone.out_features, embed),
        nn.LayerNorm(embed), nn.GELU(), nn.Dropout(0.0),
    )
    full_model = nn.Sequential(backbone, proj)

    # Load backbone + projection weights from fine-tuned ablation checkpoint
    raw = ckpt.get('model', ckpt.get('model_state', {}))
    missing, unexpected = full_model.load_state_dict(
        {k.replace("module.", ""): v for k, v in raw.items()}, strict=False)
    if missing:
        print(f"  [INFO] {len(missing)} keys not in checkpoint (normal if head is separate)")
    if unexpected:
        print(f"  [WARN] {len(unexpected)} unexpected keys ignored")

    # Load classification head weights
    head = FuzzyArcLossV2Head(embed, n_cls, s=s)
    for k, v in ckpt.get('loss_fn', ckpt.get('head_state', {})).items():
        if k.replace("module.", "") in ('head.weight', 'weight'):
            head.weight.data.copy_(v); break

    full_model.to(device).eval()
    head.to(device).eval()
    if USE_FP16:
        full_model.half(); head.half()

    print(f"  {n_cls} classes: {list(label2id.keys())}")
    print(f"  embed={embed}, in_ch={in_ch}, img={img_sz}, s={s}, fp16={USE_FP16}")
    return full_model, head, label2id, id2label, img_sz, in_ch, embed

# ══════════════════════════════════════════════════════════════════════════════
#  TILE DATASET
# ══════════════════════════════════════════════════════════════════════════════
class SlideTileDataset(Dataset):
    def __init__(self, slide_path, coords, tile_size, bg_thr, in_channels):
        self.path = str(slide_path)
        self.coords = coords
        self.tile_size = tile_size
        self.bg_thr = bg_thr
        self.in_ch = in_channels
        self._slide = None

    def _open(self):
        if self._slide is None:
            self._slide = openslide.OpenSlide(self.path)

    def __len__(self): return len(self.coords)

    def __getitem__(self, idx):
        self._open()
        x, y = self.coords[idx]
        try:
            img = self._slide.read_region((x, y), 0,
                                          (self.tile_size, self.tile_size)).convert("RGB")
            arr = np.array(img, dtype=np.float32) / 255.0
            gray = arr.mean(axis=2)
            if gray.mean() > self.bg_thr:
                return None
            t = torch.from_numpy(arr.transpose(2, 0, 1))
            if self.in_ch == 4:
                mask = torch.from_numpy((gray < self.bg_thr).astype(np.float32)).unsqueeze(0)
                t = torch.cat([t, mask], dim=0)
            return t, x, y
        except Exception:
            return None

def _collate(batch):
    batch = [b for b in batch if b is not None]
    if not batch:
        return torch.empty(0), [], [], 0
    imgs, xs, ys = zip(*batch)
    return torch.stack(imgs), list(xs), list(ys), len(imgs)

# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 1: PATTERN INFERENCE → CSV
# ══════════════════════════════════════════════════════════════════════════════
@torch.no_grad()
def stage1_pattern_inference(svs_path: Path, model, head, device,
                              img_sz, in_ch, id2label):
    """Run FuzzyArcLoss V2 on all tiles. Save per-tile probabilities CSV."""
    csv_path = INFERENCE_OUT / f"{svs_path.stem}_tiles.csv"
    if csv_path.exists():
        return f"[S1-SKIP] {svs_path.name}"

    try:
        sl = openslide.OpenSlide(str(svs_path))
        w, h = sl.level_dimensions[0]; sl.close()
    except Exception as e:
        return f"[S1-ERR] {svs_path.name}: {e}"

    coords = [(x, y) for y in range(0, h, TILE_SIZE) for x in range(0, w, TILE_SIZE)]
    ds = SlideTileDataset(str(svs_path), coords, TILE_SIZE, BG_THRESHOLD, in_ch)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False,
                        num_workers=NUM_TILE_WORKERS, pin_memory=True,
                        prefetch_factor=PREFETCH_FACTOR,
                        persistent_workers=True, collate_fn=_collate)

    all_x, all_y, all_pred, all_prob = [], [], [], []
    t0 = time.time()
    for imgs, vx, vy, cnt in loader:
        if cnt == 0: continue
        if USE_FP16: imgs = imgs.half()
        imgs = imgs.to(device, non_blocking=True)
        feats  = model(imgs)
        logits = head.infer_logits(feats)
        probs  = torch.softmax(logits.float(), dim=1)
        preds  = logits.argmax(dim=1)
        all_x.extend(vx); all_y.extend(vy)
        all_pred.extend(preds.cpu().tolist())
        all_prob.append(probs.cpu().numpy())

    if not all_pred:
        return f"[S1-EMPTY] {svs_path.name}"

    probs_arr = np.vstack(all_prob)
    n_cls = len(id2label)
    with open(csv_path, 'w', newline='') as f:
        wr = csv.writer(f)
        hdr = ['x', 'y', 'pred_class'] + [f'prob_{id2label.get(c, str(c))}' for c in range(n_cls)]
        wr.writerow(hdr)
        for i in range(len(all_pred)):
            wr.writerow([all_x[i], all_y[i], all_pred[i]] + [f"{p:.4f}" for p in probs_arr[i]])

    elapsed = time.time() - t0
    return f"[S1-OK] {svs_path.name}: {len(all_pred)} tiles in {elapsed:.0f}s"

# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 2: CSV → pattern_probs.npy + pattern_labels.npy
# ══════════════════════════════════════════════════════════════════════════════
def stage2_csv_to_npy(svs_path: Path, slide_dir: Path, id2label: dict):
    """Aggregate tile CSV → slide-level pattern_probs.npy and pattern_labels.npy."""
    probs_npy  = slide_dir / "pattern_probs.npy"
    labels_npy = slide_dir / "pattern_labels.npy"
    if probs_npy.exists() and labels_npy.exists():
        return f"[S2-SKIP] {svs_path.stem}"

    csv_path = INFERENCE_OUT / f"{svs_path.stem}_tiles.csv"
    if not csv_path.exists():
        return f"[S2-WAIT] {svs_path.stem}: CSV not ready"

    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        prob_cols = [c for c in df.columns if c.startswith('prob_')]
        if not prob_cols:
            return f"[S2-ERR] No prob columns in {csv_path.name}"

        probs  = df[prob_cols].values.astype(np.float32)   # (N_tiles, n_classes)
        labels = df['pred_class'].values.astype(np.int32)  # (N_tiles,)

        slide_dir.mkdir(parents=True, exist_ok=True)
        np.save(probs_npy,  probs)
        np.save(labels_npy, labels)
        return f"[S2-OK] {svs_path.stem}: {len(probs)} tiles, {probs.shape[1]} classes"
    except Exception as e:
        return f"[S2-ERR] {svs_path.stem}: {e}"

# ══════════════════════════════════════════════════════════════════════════════
#  STAGE 3: EMBEDDING EXTRACTION → embeddings.npy
# ══════════════════════════════════════════════════════════════════════════════
@torch.no_grad()
def stage3_extract_embeddings(svs_path: Path, slide_dir: Path,
                               model, device, img_sz, in_ch, embed_dim):
    """Extract CTransPath 512-d embeddings for all tissue tiles. Save embeddings.npy"""
    emb_npy = slide_dir / "embeddings.npy"
    if emb_npy.exists():
        return f"[S3-SKIP] {svs_path.name}"

    try:
        sl = openslide.OpenSlide(str(svs_path))
        w, h = sl.level_dimensions[0]; sl.close()
    except Exception as e:
        return f"[S3-ERR] {svs_path.name}: {e}"

    coords = [(x, y) for y in range(0, h, TILE_SIZE) for x in range(0, w, TILE_SIZE)]
    ds = SlideTileDataset(str(svs_path), coords, TILE_SIZE, BG_THRESHOLD, in_ch)
    loader = DataLoader(ds, batch_size=BATCH_SIZE, shuffle=False,
                        num_workers=NUM_TILE_WORKERS, pin_memory=True,
                        prefetch_factor=PREFETCH_FACTOR,
                        persistent_workers=True, collate_fn=_collate)

    all_emb = []
    t0 = time.time()
    for imgs, vx, vy, cnt in loader:
        if cnt == 0: continue
        if USE_FP16: imgs = imgs.half()
        imgs = imgs.to(device, non_blocking=True)
        emb = model(imgs)  # (B, 512) — output of backbone + projection head
        all_emb.append(emb.float().cpu().numpy())

    if not all_emb:
        return f"[S3-EMPTY] {svs_path.name}"

    embeddings = np.vstack(all_emb).astype(np.float32)  # (N_tiles, 512)
    slide_dir.mkdir(parents=True, exist_ok=True)
    np.save(emb_npy, embeddings)

    elapsed = time.time() - t0
    return (f"[S3-OK] {svs_path.name}: {embeddings.shape} in {elapsed:.0f}s")

# ══════════════════════════════════════════════════════════════════════════════
#  GPU WORKER  — processes its assigned slides through all 3 stages
# ══════════════════════════════════════════════════════════════════════════════
def gpu_worker(gpu_id: int, svs_list: List[Path], log_queue):
    """One process per GPU. Runs Stage1 → Stage2 → Stage3 for each slide."""
    device = torch.device(f"cuda:{gpu_id}")
    torch.cuda.set_device(device)
    print(f"\n[GPU {gpu_id}] Loading model on {device}...", flush=True)

    model, head, label2id, id2label, img_sz, in_ch, embed_dim = build_model(device)
    n_cls = len(id2label)
    print(f"[GPU {gpu_id}] Ready — {len(svs_list)} slides, {n_cls} pattern classes", flush=True)

    for i, svs_path in enumerate(svs_list):
        slide_id  = svs_path.stem
        slide_dir = SLIDES_DIR / slide_id
        tag = f"[GPU {gpu_id}] ({i+1}/{len(svs_list)}) {slide_id}"

        # ── Stage 1: pattern inference ──
        msg1 = stage1_pattern_inference(svs_path, model, head, device,
                                         img_sz, in_ch, id2label)
        print(f"  {tag} | {msg1}", flush=True)

        # ── Stage 2: CSV → npy ──
        msg2 = stage2_csv_to_npy(svs_path, slide_dir, id2label)
        print(f"  {tag} | {msg2}", flush=True)

        # ── Stage 3: embeddings ──
        msg3 = stage3_extract_embeddings(svs_path, slide_dir, model,
                                          device, img_sz, in_ch, embed_dim)
        print(f"  {tag} | {msg3}", flush=True)

        # Check completion
        done = (slide_dir / "pattern_probs.npy").exists() and \
               (slide_dir / "embeddings.npy").exists()
        status = "COMPLETE" if done else "PARTIAL"
        log_queue.put((slide_id, str(svs_path), status,
                       msg1[:60], msg2[:60], msg3[:60]))
        print(f"  {tag} | STATUS={status}\n", flush=True)

# ══════════════════════════════════════════════════════════════════════════════
#  LOG WRITER  — dedicated process to avoid file contention
# ══════════════════════════════════════════════════════════════════════════════
def log_writer(log_queue, log_file: Path):
    """Receive log entries from workers and write to TSV."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_file.exists()
    with open(log_file, 'a') as f:
        if write_header:
            f.write("slide_id\tsvs_path\tstatus\tstage1\tstage2\tstage3\ttimestamp\n")
        while True:
            item = log_queue.get()
            if item is None:
                break
            slide_id, svs_path, status, m1, m2, m3 = item
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{slide_id}\t{svs_path}\t{status}\t{m1}\t{m2}\t{m3}\t{ts}\n")
            f.flush()

# ══════════════════════════════════════════════════════════════════════════════
#  SLIDE SCANNER  — finds SVS files ready for processing
# ══════════════════════════════════════════════════════════════════════════════
def find_pending_svs():
    """
    Find SVS files that:
    - Exist in SLIDES_DIR/<slide_id>/<slide_id>.svs
    - Do NOT have both pattern_probs.npy AND embeddings.npy yet
    - Are fully downloaded (not still being written — check size stability)
    """
    pending = []
    for slide_dir in sorted(SLIDES_DIR.iterdir()):
        if not slide_dir.is_dir():
            continue
        # Look for SVS file inside the slide folder
        svs_files = list(slide_dir.glob("*.svs")) + list(slide_dir.glob("*.SVS"))
        if not svs_files:
            continue
        svs_path = svs_files[0]

        # Skip if already fully processed
        has_probs = (slide_dir / "pattern_probs.npy").exists()
        has_embs  = (slide_dir / "embeddings.npy").exists()
        if has_probs and has_embs:
            continue

        # Check file is not still being downloaded (size stable over 5 sec)
        try:
            sz1 = svs_path.stat().st_size
            time.sleep(5)
            sz2 = svs_path.stat().st_size
            if sz1 != sz2 or sz1 < 1_000_000:  # skip if still writing or tiny
                continue
        except Exception:
            continue

        pending.append(svs_path)
    return pending

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  SLIMA — 6-GPU Parallel Post-Download Pipeline")
    print("  Stage 1: FuzzyArcLoss pattern inference (per-tile CSV)")
    print("  Stage 2: CSV → pattern_probs.npy + pattern_labels.npy")
    print("  Stage 3: CTransPath embedding extraction → embeddings.npy")
    print("=" * 70)

    n_gpus = min(NUM_GPUS, torch.cuda.device_count())
    if n_gpus == 0:
        print("[ERROR] No GPUs available."); sys.exit(1)
    print(f"\n{n_gpus} GPUs available:")
    for g in range(n_gpus):
        print(f"  GPU {g}: {torch.cuda.get_device_name(g)}")

    print(f"\nSlides dir     : {SLIDES_DIR}")
    print(f"Inference out  : {INFERENCE_OUT}")
    print(f"Log file       : {LOG_FILE}")
    print(f"Poll interval  : {POLL_INTERVAL_SEC}s (scans for new SVS every {POLL_INTERVAL_SEC}s)\n")

    ctx = mp.get_context("spawn")

    # Start log writer process
    log_queue = ctx.Queue()
    log_proc  = ctx.Process(target=log_writer, args=(log_queue, LOG_FILE), daemon=True)
    log_proc.start()

    total_processed = 0
    round_n = 0

    while True:
        round_n += 1
        pending = find_pending_svs()

        if not pending:
            print(f"[Round {round_n}] No pending slides. Waiting {POLL_INTERVAL_SEC}s for new downloads...",
                  flush=True)
            time.sleep(POLL_INTERVAL_SEC)
            continue

        print(f"\n[Round {round_n}] Found {len(pending)} slides to process", flush=True)
        for p in pending[:5]:
            print(f"  • {p.parent.name}", flush=True)
        if len(pending) > 5:
            print(f"  ... and {len(pending)-5} more", flush=True)

        # Distribute slides across GPUs (round-robin)
        assign = [[] for _ in range(n_gpus)]
        for i, svs in enumerate(pending):
            assign[i % n_gpus].append(svs)

        print(f"\n  Distribution: {[len(a) for a in assign]} slides per GPU", flush=True)

        procs = []
        for g in range(n_gpus):
            if assign[g]:
                p = ctx.Process(
                    target=gpu_worker,
                    args=(g, assign[g], log_queue),
                    daemon=False
                )
                p.start()
                procs.append(p)

        # Wait for all GPU workers to finish this round
        for p in procs:
            p.join()

        total_processed += len(pending)

        # Print summary
        done_count = sum(
            1 for d in SLIDES_DIR.iterdir()
            if d.is_dir()
            and (d / "pattern_probs.npy").exists()
            and (d / "embeddings.npy").exists()
        )
        print(f"\n[Round {round_n}] Complete. Total slides with both NPY: {done_count}", flush=True)
        print(f"  Waiting {POLL_INTERVAL_SEC}s before next scan...\n", flush=True)
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main()
