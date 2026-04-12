#!/usr/bin/env python3
"""
SLIMA Optuna Hyperparameter Optimization — FuzzyArcLoss V2 (Feb 2026)
=====================================================================
Searches for optimal s, m, τ (and training hyperparams) for the ablation winner.

CONTEXT:
  - V2 achieved 94.75% macro-F1 with DEFAULT params (s=30, m=0.5, τ=0.5)
  - V3 SubCenters used Optuna-tuned params (s=39, m=0.557, τ=0.454)
  - This script gives V2 a fair Optuna search to find its true optimum

PIPELINE (matches corrected ablation exactly — all 20 fixes):
  ✓ CTransPath backbone (swin_tiny + ConvStem)
  ✓ 4-channel input: RGB + ROI mask
  ✓ FocalCE with class-balanced alpha (not LabelSmoothing+Focal)
  ✓ fp32 training (no mixed precision)
  ✓ Margin-free logits for validation metrics
  ✓ 80/20 train/val split, no separate test
  ✓ No MixUp/CutMix
  ✓ No gradient clipping
  ✓ No WeightedRandomSampler (plain shuffle)
  ✓ Cosine annealing LR with warmup
  ✓ drop_last=True
  ✓ Best model on avgPR = (MacroPrecision + MacroRecall) / 2
  ✓ ROI crop + mask-as-channel

SEARCH SPACE:
  V2-specific:  s ∈ [15, 55], m ∈ [0.1, 0.8], τ ∈ [0.15, 0.85]
  Training:     LR ∈ [1e-5, 5e-4], HEAD_LR_MULT ∈ [2, 15],
                WARMUP ∈ [3, 10], FREEZE ∈ [0, 3]
  Loss type:    FocalCE (class-balanced) vs LabelSmoothing+Focal

OUTPUT:
  - Optuna study with best trial printed
  - Best checkpoint saved as best_fuzzyarcloss_v2_optuna.pth
"""

import os, sys, math, json, random, time
import numpy as np
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple, List, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler

try:
    import optuna
    from optuna.trial import Trial
    HAS_OPTUNA = True
except ImportError:
    print("[ERROR] Optuna required. Run: pip install optuna")
    sys.exit(1)

try:
    import timm
except ImportError:
    print("[ERROR] timm required. Run: pip install timm"); sys.exit(1)

from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score

try:
    import kornia.augmentation as K_aug
    HAS_KORNIA = True
except ImportError:
    HAS_KORNIA = False

import pandas as pd
import scipy.io
try:
    import h5py
except ImportError:
    h5py = None

import re
from PIL import Image
from torchvision import transforms
from torchvision.transforms import functional as TF, InterpolationMode


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class Config:
    # Paths
    ROOT_DIR: str = "/home/rapids/notebooks/slima/Zenodo_Anorak_original"
    IMAGE_DIR = f"{ROOT_DIR}/image"
    MASK_DIR  = f"{ROOT_DIR}/mask"
    XLS_PATH: str = "/home/rapids/notebooks/slima/overlay_index ver 9 nov 2025.xlsx"
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/optuna_v2_search"
    CTRANSPATH_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/ctranspath.pth"

    # Fixed architecture
    EMBED_DIM: int = 512
    IMG_SIZE: int = 224

    # Fixed pipeline settings (from corrected ablation — DO NOT CHANGE)
    BATCH_SIZE: int = 8           # per-GPU
    WEIGHT_DECAY: float = 1e-4
    VAL_SIZE: float = 0.20
    SEED: int = 42
    USE_ROI_CROP: bool = True
    ROI_PADDING: int = 24
    MASK_THRESH: float = 0.5
    USE_MASK_AS_CHANNEL: bool = True
    MIXED_PRECISION: str = "no"   # fp32 only
    USE_MIXUP: bool = False
    USE_CUTMIX: bool = False

    # Optuna settings
    OPTUNA_TRIALS: int = 50
    OPTUNA_PRUNER_WARMUP: int = 15    # Don't prune before epoch 15
    OPTUNA_PRUNER_PATIENCE: int = 5   # Prune if below median for 5 reports
    OPTUNA_EPOCHS: int = 60           # Shorter schedule for HPO (half of full 120)
    OPTUNA_REPORT_FREQ: int = 5       # Report to pruner every 5 epochs

    # Include patterns
    INCLUDE_PATTERNS: str = "lepidic,acinar,papillary,micropapillary,solid,mucinous"

config = Config()
os.makedirs(config.OUT_DIR, exist_ok=True)


# ============================================================
# IMPORTS FROM ABLATION (copy exact implementations)
# ============================================================
# These are copied verbatim from the corrected ablation script to ensure
# exact pipeline parity. In production, import from a shared module.

# --- ConvStem ---
class ConvStem(nn.Module):
    def __init__(self, img_size=224, patch_size=4, in_chans=3, embed_dim=96):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.grid_size = (img_size // patch_size, img_size // patch_size)
        self.num_patches = self.grid_size[0] * self.grid_size[1]
        stem_dim1, stem_dim2 = embed_dim // 8, embed_dim // 4
        self.proj = nn.Sequential(
            nn.Conv2d(in_chans, stem_dim1, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(stem_dim1), nn.GELU(),
            nn.Conv2d(stem_dim1, stem_dim2, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(stem_dim2), nn.GELU(),
            nn.Conv2d(stem_dim2, embed_dim, 1, bias=False), nn.BatchNorm2d(embed_dim),
        )
        self.norm = nn.LayerNorm(embed_dim)
    def forward(self, x):
        return self.norm(self.proj(x).permute(0, 2, 3, 1))


class CTransPathBackbone(nn.Module):
    def __init__(self, checkpoint_path=None, freeze_layers=0, in_channels=3):
        super().__init__()
        self.model = timm.create_model('swin_tiny_patch4_window7_224', pretrained=False, num_classes=0)
        self.model.patch_embed = ConvStem(img_size=224, patch_size=4, in_chans=3, embed_dim=96)
        self.out_features = self.model.num_features
        if checkpoint_path and os.path.exists(checkpoint_path):
            self._load_checkpoint(checkpoint_path)
        if in_channels != 3:
            old = self.model.patch_embed.proj[0]
            new = nn.Conv2d(in_channels, old.out_channels, old.kernel_size, old.stride, old.padding, bias=False)
            with torch.no_grad():
                new.weight[:, :3] = old.weight
                new.weight[:, 3:] = old.weight.mean(dim=1, keepdim=True)
            self.model.patch_embed.proj[0] = new
        if freeze_layers > 0:
            for i, layer in enumerate(self.model.layers):
                if i < freeze_layers:
                    for p in layer.parameters():
                        p.requires_grad = False

    def _load_checkpoint(self, path):
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
        if len(filt) >= 100:
            self.model.load_state_dict(filt, strict=False)
    def forward(self, x):
        return self.model(x)


# --- FuzzyArcMarginProductV2 ---
class FuzzyArcMarginProductV2(nn.Module):
    """V2 Inverse: confident → full margin, uncertain → gentle margin."""
    def __init__(self, in_features, out_features, s=30.0, m=0.50, tau=0.5, easy_margin=False):
        super().__init__()
        self.in_features, self.out_features = in_features, out_features
        self.s, self.m, self.tau = s, m, tau
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m

    def forward(self, features, labels):
        fn = F.normalize(features, dim=1)
        wn = F.normalize(self.weight, dim=1)
        cosine = F.linear(fn, wn).clamp(-1+1e-7, 1-1e-7)
        sine = torch.sqrt(1.0 - cosine**2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        bs = features.size(0)
        tc = cosine[torch.arange(bs, device=features.device), labels]
        mu = torch.where(
            torch.abs(tc) >= self.tau,
            0.8 + 0.2 * torch.abs(tc),
            0.3 + 0.4 * torch.abs(tc)
        ).clamp(0, 1)
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        return self.s * (one_hot * target_logits + (1 - one_hot) * cosine)


# --- FocalCE (from notebook, matches V3 SubCenters that achieved 93.39%) ---
class FocalCE(nn.Module):
    """Focal Cross-Entropy with class-balanced alpha."""
    def __init__(self, alpha=None, gamma=2.0):
        super().__init__()
        self.gamma = gamma
        self.register_buffer("alpha", None if alpha is None else torch.tensor(alpha, dtype=torch.float32))
    def forward(self, logits, target):
        logp = F.log_softmax(logits, dim=1)
        idx = torch.arange(logits.size(0), device=logits.device)
        pt = logp.exp()[idx, target]
        loss = -(1 - pt).pow(self.gamma) * logp[idx, target]
        if self.alpha is not None:
            loss = loss * self.alpha.to(logits.device)[target]
        return loss.mean()


# --- LabelSmoothingCE + FocalLoss (the original V2 combo) ---
class LabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, smoothing=0.1, weight=None):
        super().__init__()
        self.smoothing = smoothing
        self.weight = weight
    def forward(self, logits, target):
        log_probs = F.log_softmax(logits, dim=1)
        nll = F.nll_loss(log_probs, target, weight=self.weight)
        smooth = -log_probs.mean(dim=1).mean()
        return (1 - self.smoothing) * nll + self.smoothing * smooth


class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None):
        super().__init__()
        self.gamma = gamma
        self.weight = weight
    def forward(self, logits, target):
        ce = F.cross_entropy(logits, target, weight=self.weight, reduction='none')
        pt = torch.exp(-ce)
        return ((1 - pt) ** self.gamma * ce).mean()


# --- V2 Loss Wrapper (supports both FocalCE and LabelSmoothing+Focal) ---
class FuzzyArcLossV2Optuna(nn.Module):
    """V2 loss with configurable CE backend for Optuna search."""
    def __init__(self, in_features, out_features, s, m, tau,
                 use_focal_ce=True, class_counts=None,
                 focal_gamma=2.0, label_smoothing=0.1, ce_weight=None):
        super().__init__()
        self.head = FuzzyArcMarginProductV2(in_features, out_features, s=s, m=m, tau=tau)
        self.s = s
        self.weight = self.head.weight

        if use_focal_ce:
            # FocalCE with class-balanced alpha (same as V3 SubCenters)
            if class_counts is not None:
                alpha = [1.0 / max(c, 1) for c in class_counts]
                alpha_sum = sum(alpha)
                alpha = [a / alpha_sum for a in alpha]
            else:
                alpha = None
            self.criterion = FocalCE(alpha=alpha, gamma=focal_gamma)
            self._mode = 'focal_ce'
        else:
            # Original V2 combo: LabelSmoothing * 0.6 + Focal * 0.4
            self._ls = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
            self._fl = FocalLoss(gamma=focal_gamma, weight=ce_weight)
            self._mode = 'ls_focal'

    def forward(self, features, labels):
        logits = self.head(features, labels)
        if self._mode == 'focal_ce':
            loss = self.criterion(logits, labels)
        else:
            loss = 0.6 * self._ls(logits, labels) + 0.4 * self._fl(logits, labels)
        return loss, logits


# --- Margin-free logits (critical for correct evaluation) ---
def _logits_nomargin(feats, loss_fn):
    """Margin-free cosine logits for evaluation."""
    if hasattr(loss_fn, 'head') and hasattr(loss_fn.head, 'weight'):
        weight = loss_fn.head.weight
        s = getattr(loss_fn, 's', getattr(loss_fn.head, 's', 30.0))
    elif hasattr(loss_fn, 'weight'):
        weight = loss_fn.weight
        s = getattr(loss_fn, 's', 30.0)
    else:
        return None
    fn = F.normalize(feats, dim=1)
    wn = F.normalize(weight, dim=1)
    return (fn @ wn.t()) * s


# ============================================================
# DATA LOADING (exact match of corrected ablation)
# ============================================================

def normalize_key(s):
    """Normalize a filename key (from notebook)."""
    s = str(s)
    s = re.sub(r'[_\-\s]+', '_', s)
    s = re.sub(r'(?i)_?(mask|seg|roi|overlay|label|annot|gt)[_]?', '', s)
    s = s.strip('_').lower()
    return s


def list_images(root):
    exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp'}
    return sorted(p for p in Path(root).rglob('*') if p.suffix.lower() in exts)


def list_mats(root):
    return sorted(p for p in Path(root).rglob('*') if p.suffix.lower() in ('.mat', '.png', '.jpg', '.tif'))


def build_mat_index(mat_paths):
    idx = {}
    for p in mat_paths:
        stem = p.stem
        idx[stem] = p
        idx[stem.lower()] = p
        idx[normalize_key(stem)] = p
    return idx


def load_mask_from_mat(mat_path):
    """Load mask from .mat or image file."""
    p = Path(mat_path)
    if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        return Image.open(p).convert('L')
    try:
        d = scipy.io.loadmat(str(p))
        for key in ['mask', 'BW', 'roi', 'seg', 'inst_map', 'type_map']:
            if key in d and isinstance(d[key], np.ndarray) and d[key].ndim == 2:
                return Image.fromarray((d[key] > 0).astype(np.uint8) * 255, mode='L')
        for v in d.values():
            if isinstance(v, np.ndarray) and v.ndim == 2 and v.size > 100:
                return Image.fromarray((v > 0).astype(np.uint8) * 255, mode='L')
    except Exception:
        pass
    if h5py is not None:
        try:
            with h5py.File(str(p), 'r') as f:
                for k in f.keys():
                    arr = np.array(f[k])
                    if arr.ndim == 2 and arr.size > 100:
                        return Image.fromarray((arr > 0).astype(np.uint8) * 255, mode='L')
        except Exception:
            pass
    return Image.new('L', (224, 224), 0)


def pair_images_with_masks(image_dir, mask_dir):
    """Pair images with masks using flexible key matching."""
    images = list_images(image_dir)
    mats = list_mats(mask_dir)
    mat_idx = build_mat_index(mats)

    rows = []
    for img_p in images:
        stem = img_p.stem
        mask_p = mat_idx.get(stem) or mat_idx.get(stem.lower()) or mat_idx.get(normalize_key(stem))
        rows.append({
            'image_path': str(img_p), 'mask_path': str(mask_p) if mask_p else '',
            'stem': stem, 'base': stem, 'base_norm': normalize_key(stem)
        })

    matched = sum(1 for r in rows if r['mask_path'])
    unmatched = len(rows) - matched
    print(f"  [PAIRING] matched={matched}  unmatched={unmatched}")
    return pd.DataFrame(rows)


class HistMaskDataset(torch.utils.data.Dataset):
    """CPU dataset with joint image+mask augmentation (matches notebook)."""
    def __init__(self, df, label_col, label2id, img_size=224, aug=False,
                 use_mask_as_channel=True, use_roi_crop=True,
                 roi_padding=24, mask_thresh=0.5):
        self.df = df.reset_index(drop=True)
        self.label_col = label_col
        self.label2id = label2id
        self.img_size = img_size
        self.aug = aug
        self.use_mask = use_mask_as_channel
        self.use_roi_crop = use_roi_crop
        self.roi_padding = roi_padding
        self.mask_thresh = mask_thresh
        self.normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = Image.open(row['image_path']).convert('RGB')
        label = self.label2id[str(row[self.label_col])]

        if self.use_mask and row.get('mask_path', ''):
            mask = load_mask_from_mat(row['mask_path'])
        else:
            mask = Image.new('L', img.size, 255)

        # ROI crop
        if self.use_roi_crop:
            mask_arr = np.array(mask)
            ys, xs = np.where(mask_arr > self.mask_thresh * 255)
            if len(xs) > 0:
                x1, x2 = max(0, xs.min() - self.roi_padding), min(img.width, xs.max() + self.roi_padding)
                y1, y2 = max(0, ys.min() - self.roi_padding), min(img.height, ys.max() + self.roi_padding)
                img = img.crop((x1, y1, x2, y2))
                mask = mask.crop((x1, y1, x2, y2))

        # Resize
        img = img.resize((self.img_size, self.img_size), Image.BILINEAR)
        mask = mask.resize((self.img_size, self.img_size), Image.NEAREST)

        if self.aug:
            # Geometric (applied to both)
            if random.random() > 0.5:
                img = TF.hflip(img); mask = TF.hflip(mask)
            if random.random() > 0.5:
                img = TF.vflip(img); mask = TF.vflip(mask)
            angle = random.uniform(-15, 15)
            img = TF.rotate(img, angle)
            mask = TF.rotate(mask, angle)
            # Color (image only)
            img = transforms.ColorJitter(0.2, 0.2, 0.2, 0.05)(img)
            if random.random() < 0.3:
                img = TF.gaussian_blur(img, kernel_size=3)

        img_t = self.normalize(TF.to_tensor(img))
        msk_t = TF.to_tensor(mask)

        if self.use_mask:
            return torch.cat([img_t, msk_t], dim=0), label
        return img_t, label


# --- GPU-cached dataset (if kornia available) ---
class GPUCachedMaskDataset(torch.utils.data.Dataset):
    """Pre-loads all images+masks to CPU memory (zero disk I/O during training)."""
    def __init__(self, df, label_col, label2id, img_size=224,
                 use_mask_as_channel=True, use_roi_crop=True,
                 roi_padding=24, mask_thresh=0.5):
        self.labels = []
        self.tensors = []
        normalize = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

        for _, row in df.iterrows():
            self.labels.append(label2id[str(row[label_col])])
            img = Image.open(row['image_path']).convert('RGB')
            mask_path = row.get('mask_path', '')
            mask = load_mask_from_mat(mask_path) if mask_path else Image.new('L', img.size, 255)

            if use_roi_crop:
                ma = np.array(mask)
                ys, xs = np.where(ma > mask_thresh * 255)
                if len(xs) > 0:
                    x1 = max(0, xs.min() - roi_padding)
                    x2 = min(img.width, xs.max() + roi_padding)
                    y1 = max(0, ys.min() - roi_padding)
                    y2 = min(img.height, ys.max() + roi_padding)
                    img = img.crop((x1, y1, x2, y2))
                    mask = mask.crop((x1, y1, x2, y2))

            img = img.resize((img_size, img_size), Image.BILINEAR)
            mask = mask.resize((img_size, img_size), Image.NEAREST)
            t = torch.cat([normalize(TF.to_tensor(img)), TF.to_tensor(mask)], dim=0) \
                if use_mask_as_channel else normalize(TF.to_tensor(img))
            self.tensors.append(t)

        print(f"    Pre-caching {len(self.tensors)} images+masks to memory... done!")

    def __len__(self):
        return len(self.tensors)

    def __getitem__(self, idx):
        return self.tensors[idx], self.labels[idx]


# --- GPU Augmentation ---
class GPUAugmentation(nn.Module):
    """Kornia GPU augmentation matching notebook exactly."""
    def __init__(self, img_size=224, training=True):
        super().__init__()
        if not HAS_KORNIA:
            self.aug = nn.Identity()
            return
        if training:
            self.aug = nn.Sequential(
                K_aug.RandomHorizontalFlip(p=0.5),
                K_aug.RandomVerticalFlip(p=0.5),
                K_aug.RandomRotation(degrees=15, p=0.5),
                K_aug.ColorJitter(0.2, 0.2, 0.2, 0.05, p=0.8),
                K_aug.RandomGaussianBlur((3, 3), (0.1, 2.0), p=0.3),
            )
        else:
            self.aug = nn.Identity()

    def forward(self, x):
        # Apply geometric to all channels, color to RGB only
        if isinstance(self.aug, nn.Identity):
            return x
        if x.shape[1] == 4:
            rgb, mask = x[:, :3], x[:, 3:]
            # Geometric
            all_ch = torch.cat([rgb, mask], dim=1)
            all_ch = self.aug[:3](all_ch)  # flip + rotate
            rgb, mask = all_ch[:, :3], all_ch[:, 3:]
            # Color on RGB only
            rgb = self.aug[3:](rgb)  # ColorJitter + Blur
            return torch.cat([rgb, mask], dim=1)
        return self.aug(x)


# ============================================================
# DATA LOADING PIPELINE
# ============================================================

def load_data():
    """Load and prepare data exactly as in corrected ablation."""
    print("[1/3] Loading data...")

    # Find image and mask directories
    root = Path(config.ROOT_DIR)
    image_dir = config.IMAGE_DIR or str(root)
    mask_dir = config.MASK_DIR or str(root)

    # Auto-discover subdirs
    for d in root.iterdir():
        if d.is_dir():
            dl = d.name.lower()
            if 'image' in dl or 'tile' in dl or 'patch' in dl:
                image_dir = str(d)
            if 'mask' in dl or 'mat' in dl or 'annot' in dl or 'overlay' in dl:
                mask_dir = str(d)

    df = pair_images_with_masks(image_dir, mask_dir)

    # Label mapping (exact match of corrected ablation script)
    xls = pd.read_excel(config.XLS_PATH)

    # Auto-detect columns using ordered candidate lists (same as ablation)
    label_candidates = ["pattern","label","class","type","luad_pattern","histologic_pattern","pattern_type"]
    file_candidates = ["tile_id","overlay_file","image_file","file","path","filepath","filename","name","base","stem","image_id","tile"]
    label_col = next((c for c in label_candidates if c in xls.columns), None)
    file_col = next((c for c in file_candidates if c in xls.columns), None)

    if label_col is None or file_col is None:
        # Fallback: try case-insensitive partial match
        for c in xls.columns:
            cl = c.lower()
            if label_col is None and any(k in cl for k in ('label', 'class', 'pattern', 'type')):
                label_col = c
            if file_col is None and any(k in cl for k in ('file', 'name', 'image', 'tile', 'overlay')):
                file_col = c

    if label_col is None or file_col is None:
        raise ValueError(f"Could not find label/file columns. Available: {xls.columns.tolist()}")

    print(f"  XLS columns: label_col='{label_col}', file_col='{file_col}'")

    # Build label map with 3 key variants per entry (stem, stem.lower(), normalize_key)
    label_map = {}
    for _, r in xls.iterrows():
        f = str(r[file_col])
        stem = Path(f).stem
        lbl = str(r[label_col]).strip()
        label_map[stem] = lbl
        label_map[normalize_key(stem)] = lbl
        label_map[stem.lower()] = lbl

    # Map labels to df using base + base_norm fallback (same as ablation)
    df[label_col] = df["base"].map(label_map)
    miss = df[label_col].isna()
    if miss.any():
        df.loc[miss, label_col] = df.loc[miss, "base_norm"].map(label_map)
    df = df[~df[label_col].isna()].copy()
    print(f"  After label join: {len(df)} rows")

    # Filter to included patterns only
    inc = {p.strip().lower() for p in config.INCLUDE_PATTERNS.split(",") if p.strip()}
    df[label_col] = df[label_col].astype(str)
    df = df[df[label_col].str.lower().isin(inc)].copy()

    if df.empty:
        raise RuntimeError("After filtering, dataset is empty. Check XLS and INCLUDE_PATTERNS.")

    labels = sorted(df[label_col].str.lower().unique().tolist())
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    df['label'] = df[label_col].str.lower()
    print(f"  After filter: {len(df)} rows, classes={labels}")

    # Split
    train_df, val_df = train_test_split(
        df, test_size=config.VAL_SIZE, stratify=df['label'], random_state=config.SEED
    )
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}")

    # Class counts
    train_labels = [label2id[str(l)] for l in train_df['label']]
    class_counts = [train_labels.count(i) for i in range(len(labels))]
    print(f"  Class counts: {dict(zip(labels, class_counts))}")

    return train_df, val_df, labels, label2id, id2label, class_counts


# ============================================================
# OPTUNA OBJECTIVE
# ============================================================

def create_objective(train_df, val_df, labels, label2id, id2label, class_counts, device):
    """Create the Optuna objective function."""

    num_classes = len(labels)
    in_channels = 4 if config.USE_MASK_AS_CHANNEL else 3

    # Pre-build datasets (reused across trials)
    if HAS_KORNIA:
        print("  [GPU MODE] Pre-caching datasets...")
        train_ds = GPUCachedMaskDataset(train_df, 'label', label2id, config.IMG_SIZE,
                                         config.USE_MASK_AS_CHANNEL, config.USE_ROI_CROP,
                                         config.ROI_PADDING, config.MASK_THRESH)
        val_ds = GPUCachedMaskDataset(val_df, 'label', label2id, config.IMG_SIZE,
                                       config.USE_MASK_AS_CHANNEL, config.USE_ROI_CROP,
                                       config.ROI_PADDING, config.MASK_THRESH)
        gpu_train_aug = GPUAugmentation(config.IMG_SIZE, training=True).to(device)
        gpu_val_aug = GPUAugmentation(config.IMG_SIZE, training=False).to(device)
        num_workers = 0
    else:
        print("  [CPU MODE] Using HistMaskDataset...")
        train_ds = HistMaskDataset(train_df, 'label', label2id, config.IMG_SIZE, aug=True,
                                    use_mask_as_channel=config.USE_MASK_AS_CHANNEL,
                                    use_roi_crop=config.USE_ROI_CROP)
        val_ds = HistMaskDataset(val_df, 'label', label2id, config.IMG_SIZE, aug=False,
                                  use_mask_as_channel=config.USE_MASK_AS_CHANNEL,
                                  use_roi_crop=config.USE_ROI_CROP)
        gpu_train_aug = None
        gpu_val_aug = None
        num_workers = 4

    batch_size = config.BATCH_SIZE * max(1, torch.cuda.device_count())

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                               num_workers=num_workers, pin_memory=not HAS_KORNIA, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                             num_workers=num_workers, pin_memory=not HAS_KORNIA)

    # CE weights
    total_samples = sum(class_counts)
    ce_weights = torch.tensor([total_samples / (num_classes * c) for c in class_counts])
    ce_weights = (ce_weights / ce_weights.sum() * num_classes).to(device)

    best_global_state = {'avg_pr': 0.0, 'state': None, 'params': None}

    def objective(trial: Trial) -> float:
        # ── SEARCH SPACE ──
        s = trial.suggest_float('S_SCALE', 15.0, 55.0)
        m = trial.suggest_float('M_MARGIN', 0.1, 0.8)
        tau = trial.suggest_float('TAU', 0.15, 0.85)
        lr = trial.suggest_float('BACKBONE_LR', 1e-5, 5e-4, log=True)
        head_lr_mult = trial.suggest_float('HEAD_LR_MULT', 2.0, 15.0)
        freeze_layers = trial.suggest_int('FREEZE_LAYERS', 0, 3)
        warmup = trial.suggest_int('WARMUP_EPOCHS', 3, 10)
        use_focal_ce = trial.suggest_categorical('USE_FOCAL_CE', [True, False])
        focal_gamma = trial.suggest_float('FOCAL_GAMMA', 1.0, 3.0)

        # ── BUILD MODEL ──
        backbone = CTransPathBackbone(
            config.CTRANSPATH_CHECKPOINT, freeze_layers, in_channels
        )
        proj = nn.Sequential(
            nn.Linear(backbone.out_features, config.EMBED_DIM),
            nn.LayerNorm(config.EMBED_DIM), nn.GELU(), nn.Dropout(0.15),
        )
        model = nn.Sequential(backbone, proj)

        loss_fn = FuzzyArcLossV2Optuna(
            config.EMBED_DIM, num_classes, s=s, m=m, tau=tau,
            use_focal_ce=use_focal_ce, class_counts=class_counts,
            focal_gamma=focal_gamma, ce_weight=ce_weights,
        )

        # Multi-GPU
        if torch.cuda.device_count() > 1:
            model = nn.DataParallel(model)
        model.to(device)
        loss_fn.to(device)

        # ── OPTIMIZER (differential LR, same as ablation) ──
        if isinstance(model, nn.DataParallel):
            backbone_params = list(model.module[0].parameters())
            head_params = list(model.module[1].parameters()) + list(loss_fn.parameters())
        else:
            backbone_params = list(model[0].parameters())
            head_params = list(model[1].parameters()) + list(loss_fn.parameters())

        optimizer = torch.optim.AdamW([
            {'params': backbone_params, 'lr': lr},
            {'params': head_params, 'lr': lr * head_lr_mult},
        ], weight_decay=config.WEIGHT_DECAY)

        # Scheduler (warmup + cosine, matches ablation)
        epochs = config.OPTUNA_EPOCHS
        def lr_lambda(epoch):
            if epoch < warmup:
                return (epoch + 1) / warmup
            progress = (epoch - warmup) / max(1, epochs - warmup)
            return 0.5 * (1 + math.cos(math.pi * progress))
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

        # ── TRAINING LOOP ──
        best_avg_pr = 0.0
        best_epoch = 0
        best_state = None

        for epoch in range(epochs):
            model.train(); loss_fn.train()
            for images, lbl in train_loader:
                images = images.to(device, non_blocking=True)
                lbl = lbl.to(device, non_blocking=True)
                if gpu_train_aug is not None:
                    images = gpu_train_aug(images)
                features = model(images)
                loss, _ = loss_fn(features, lbl)
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
            scheduler.step()

            # ── VALIDATION (margin-free logits!) ──
            if (epoch + 1) % config.OPTUNA_REPORT_FREQ == 0 or epoch == epochs - 1:
                model.eval(); loss_fn.eval()
                all_preds, all_labels = [], []
                with torch.no_grad():
                    for images, lbl in val_loader:
                        images = images.to(device, non_blocking=True)
                        if gpu_val_aug is not None:
                            images = gpu_val_aug(images)
                        features = model(images)
                        logits = _logits_nomargin(features, loss_fn)
                        if logits is None:
                            _, logits = loss_fn(features, lbl.to(device))
                        preds = logits.argmax(dim=1).cpu().numpy()
                        all_preds.extend(preds)
                        all_labels.extend(lbl.numpy())

                val_prec = precision_score(all_labels, all_preds, average='macro', zero_division=0)
                val_rec = recall_score(all_labels, all_preds, average='macro', zero_division=0)
                val_avg_pr = (val_prec + val_rec) / 2

                # Report to pruner
                trial.report(val_avg_pr, epoch)
                if trial.should_prune():
                    raise optuna.TrialPruned()

                if val_avg_pr > best_avg_pr:
                    best_avg_pr = val_avg_pr
                    best_epoch = epoch
                    if isinstance(model, nn.DataParallel):
                        ms = {k: v.cpu().clone() for k, v in model.module.state_dict().items()}
                    else:
                        ms = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                    best_state = {
                        'model': ms,
                        'loss_fn': {k: v.cpu().clone() for k, v in loss_fn.state_dict().items()},
                    }

        # Save if global best
        if best_avg_pr > best_global_state['avg_pr']:
            best_global_state['avg_pr'] = best_avg_pr
            best_global_state['state'] = best_state
            best_global_state['params'] = {
                'S_SCALE': s, 'M_MARGIN': m, 'TAU': tau,
                'BACKBONE_LR': lr, 'HEAD_LR_MULT': head_lr_mult,
                'FREEZE_LAYERS': freeze_layers, 'WARMUP_EPOCHS': warmup,
                'USE_FOCAL_CE': use_focal_ce, 'FOCAL_GAMMA': focal_gamma,
                'best_epoch': best_epoch, 'avg_pr': best_avg_pr,
            }
            # Save checkpoint
            ckpt_path = os.path.join(config.OUT_DIR, 'best_fuzzyarcloss_v2_optuna.pth')
            torch.save({
                'model': best_state['model'],
                'loss_fn': best_state['loss_fn'],
                'config': {
                    'EMBED_DIM': config.EMBED_DIM, 'IMG_SIZE': config.IMG_SIZE,
                    'USE_MASK_AS_CHANNEL': config.USE_MASK_AS_CHANNEL,
                    'S_SCALE': s, 'M_MARGIN': m, 'TAU': tau,
                    'FREEZE_BACKBONE_LAYERS': freeze_layers,
                    'loss_type': 'fuzzyarcloss_v2',
                    'USE_FOCAL_CE': use_focal_ce, 'FOCAL_GAMMA': focal_gamma,
                },
                'label2id': label2id, 'id2label': id2label,
                'optuna_params': best_global_state['params'],
            }, ckpt_path)
            print(f"  ✓ New best! avgPR={best_avg_pr:.4f} → saved checkpoint")

        # Clean up GPU memory
        del model, loss_fn, optimizer, scheduler
        torch.cuda.empty_cache()

        return best_avg_pr

    return objective, best_global_state


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  OPTUNA HPO: FuzzyArcLoss V2 (CTransPath)")
    print("  Searching for optimal s, m, τ + training hyperparameters")
    print("=" * 70)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cuda':
        print(f"  GPUs: {torch.cuda.device_count()} x {torch.cuda.get_device_name(0)}")

    random.seed(config.SEED)
    np.random.seed(config.SEED)
    torch.manual_seed(config.SEED)

    # Load data
    train_df, val_df, labels, label2id, id2label, class_counts = load_data()

    # Create objective
    objective, best_state = create_objective(
        train_df, val_df, labels, label2id, id2label, class_counts, device
    )

    # Create study with pruner
    pruner = optuna.pruners.MedianPruner(
        n_startup_trials=5,
        n_warmup_steps=config.OPTUNA_PRUNER_WARMUP,
        n_min_trials=5,
    )

    study = optuna.create_study(
        direction='maximize',
        pruner=pruner,
        study_name='fuzzyarcloss_v2_ctranspath',
    )

    print(f"\n[2/3] Running {config.OPTUNA_TRIALS} trials ({config.OPTUNA_EPOCHS} epochs each)")
    print(f"  Search space: s∈[15,55], m∈[0.1,0.8], τ∈[0.15,0.85]")
    print(f"  + LR, HEAD_LR_MULT, FREEZE, WARMUP, USE_FOCAL_CE, FOCAL_GAMMA")
    print("=" * 70)

    study.optimize(objective, n_trials=config.OPTUNA_TRIALS)

    # ============================================================
    # RESULTS
    # ============================================================
    print("\n" + "=" * 70)
    print("[3/3] OPTUNA RESULTS")
    print("=" * 70)

    print(f"\nCompleted: {len(study.trials)} trials")
    print(f"  Completed: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
    print(f"  Pruned:    {len([t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED])}")

    best = study.best_trial
    print(f"\n{'='*70}")
    print(f"  BEST TRIAL: #{best.number}")
    print(f"  avgPR = {best.value:.4f}")
    print(f"{'='*70}")
    print(f"  Parameters:")
    for k, v in best.params.items():
        print(f"    {k}: {v}")

    # Save summary
    summary = {
        'best_trial': best.number,
        'best_avg_pr': best.value,
        'best_params': best.params,
        'all_trials': [
            {'number': t.number, 'value': t.value, 'params': t.params, 'state': str(t.state)}
            for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE
        ]
    }
    summary_path = os.path.join(config.OUT_DIR, 'optuna_v2_results.json')
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\n✓ Results: {summary_path}")

    # Top 5 trials
    top5 = sorted([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE],
                   key=lambda t: t.value, reverse=True)[:5]
    print(f"\nTop 5 trials:")
    print(f"{'#':>4} {'avgPR':>8} {'s':>7} {'m':>6} {'τ':>6} {'LR':>10} {'HLR×':>6} {'FRZ':>4} {'WU':>3} {'FCE':>5} {'γ':>5}")
    for t in top5:
        p = t.params
        print(f"{t.number:4d} {t.value:8.4f} {p['S_SCALE']:7.2f} {p['M_MARGIN']:6.3f} "
              f"{p['TAU']:6.3f} {p['BACKBONE_LR']:10.2e} {p['HEAD_LR_MULT']:6.2f} "
              f"{p['FREEZE_LAYERS']:4d} {p['WARMUP_EPOCHS']:3d} "
              f"{'Y' if p['USE_FOCAL_CE'] else 'N':>5} {p['FOCAL_GAMMA']:5.2f}")

    ckpt = os.path.join(config.OUT_DIR, 'best_fuzzyarcloss_v2_optuna.pth')
    if os.path.exists(ckpt):
        print(f"\n✓ Best checkpoint: {ckpt}")
        print(f"  Use this in the ablation script and inference pipeline")

    return study


if __name__ == "__main__":
    main()
