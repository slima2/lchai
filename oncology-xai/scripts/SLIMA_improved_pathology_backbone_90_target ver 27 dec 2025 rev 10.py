#!/usr/bin/env python3
"""
SLIMA Improved Training Pipeline - Pathology Foundation Models + Advanced Augmentation
=======================================================================================

TARGET: 90% Accuracy (from current 76%)

GAP ANALYSIS SOLUTIONS:
-----------------------
ISSUE 1 (~10% potential gain): ImageNet backbone not optimal for histology
  - Solution: Use pathology-pretrained foundation models (UNI, CTransPath)
  
ISSUE 2 (~3-5% potential gain): Limited training data with class imbalance
  - Solution: CutMix, MixUp, Stain Augmentation, Class-weighted sampling

Key Improvements:
1. UNI backbone (Harvard/MGH) - trained on 100k+ pathology slides
2. CTransPath backbone - trained on 15M pathology patches
3. Fallback to ResNet-101 ImageNet if pathology models unavailable
4. CutMix augmentation for data efficiency
5. MixUp augmentation for regularization
6. Stain augmentation (H&E color jitter, Macenko-style)
7. Class-weighted sampling for imbalanced classes
8. All original optimizations preserved

Usage:
    # As standalone script:
    accelerate launch --num_processes=6 SLIMA_improved_pathology_backbone_90_target.py
    
    # Or with nohup:
    nohup accelerate launch --num_processes=6 SLIMA_improved_pathology_backbone_90_target.py > train.log 2>&1 &
"""

import os
import re
import sys
import json
import time
import random
import math
import warnings
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from PIL import Image

# Set multiprocessing start method before importing torch
import torch.multiprocessing as mp
try:
    mp.set_start_method('spawn', force=True)
except RuntimeError:
    pass  # Already set

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributed
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler

# Prevent CUDA init issues
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '0,1,2,3,4,5')

from torchvision import models, transforms
from torchvision.transforms import functional as TF
from torchvision.transforms import InterpolationMode

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report,
    precision_score, recall_score, confusion_matrix
)

try:
    from scipy.io import loadmat
except Exception:
    loadmat = None
try:
    import h5py
except Exception:
    h5py = None

from accelerate import Accelerator

# Optional: timm for advanced architectures
try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False
    print("Note: timm not installed, some backbones may be unavailable")

# Optional: huggingface_hub for downloading models
try:
    from huggingface_hub import hf_hub_download, login as hf_login
    HAS_HF_HUB = True
except ImportError:
    HAS_HF_HUB = False
    print("Note: huggingface_hub not installed. Install with: pip install huggingface_hub")

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)


def download_uni_model(save_path: str, verbose: bool = True) -> bool:
    """
    Download UNI2-h model from HuggingFace Hub.
    
    UNI2-h requires access approval from https://huggingface.co/MahmoodLab/UNI2-h
    You must:
    1. Create a HuggingFace account
    2. Request access at https://huggingface.co/MahmoodLab/UNI2-h
    3. Create an access token at https://huggingface.co/settings/tokens
    4. Set HF_TOKEN environment variable or login via `huggingface-cli login`
    
    Returns True if download successful, False otherwise.
    """
    if not HAS_HF_HUB:
        if verbose:
            print("[UNI2-h] huggingface_hub not installed. Install with: pip install huggingface_hub")
        return False
    
    # Check if already exists
    if os.path.exists(save_path):
        if verbose:
            print(f"[UNI2-h] Model already exists at {save_path}")
        return True
    
    # Create directory if needed
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    try:
        if verbose:
            print("[UNI2-h] Attempting to download UNI2-h from HuggingFace Hub...")
            print("[UNI2-h] Note: This requires access approval from https://huggingface.co/MahmoodLab/UNI2-h")
        
        # Try to download - UNI2-h uses safetensors format
        # First try model.safetensors, then pytorch_model.bin
        try:
            downloaded_path = hf_hub_download(
                repo_id="MahmoodLab/UNI2-h",
                filename="model.safetensors",
                local_dir=os.path.dirname(save_path),
                local_dir_use_symlinks=False,
            )
            # Save path should reflect actual format
            actual_path = os.path.join(os.path.dirname(save_path), "model.safetensors")
            if verbose:
                print(f"[UNI2-h] Successfully downloaded to {actual_path}")
            return True
        except Exception:
            # Try pytorch_model.bin as fallback
            downloaded_path = hf_hub_download(
                repo_id="MahmoodLab/UNI2-h",
                filename="pytorch_model.bin",
                local_dir=os.path.dirname(save_path),
                local_dir_use_symlinks=False,
            )
            if verbose:
                print(f"[UNI2-h] Successfully downloaded to {downloaded_path}")
            return True
        
    except Exception as e:
        if verbose:
            print(f"[UNI2-h] Download failed: {e}")
            print("[UNI2-h] To download UNI2-h, you need to:")
            print("  1. Request access at https://huggingface.co/MahmoodLab/UNI2-h")
            print("  2. Create access token at https://huggingface.co/settings/tokens")
            print("  3. Run: huggingface-cli login")
            print("  4. Or set environment variable: export HF_TOKEN=your_token")
        return False


def download_ctranspath_model(save_path: str, verbose: bool = True) -> bool:
    """
    Download CTransPath model.
    
    CTransPath is available from the TransPath GitHub repo.
    Uses gdown for reliable Google Drive downloads.
    
    Returns True if download successful, False otherwise.
    """
    if os.path.exists(save_path):
        if verbose:
            print(f"[CTransPath] Model already exists at {save_path}")
        return True
    
    # Create directory if needed
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Google Drive file ID for CTransPath
    file_id = "1DoDx_70_TLj98gTf6YTXnu4tFhsFocDX"
    
    # Try gdown first (most reliable for Google Drive)
    try:
        import gdown
        if verbose:
            print("[CTransPath] Downloading using gdown...")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, save_path, quiet=not verbose)
        if os.path.exists(save_path):
            if verbose:
                print(f"[CTransPath] Successfully downloaded to {save_path}")
            return True
    except ImportError:
        if verbose:
            print("[CTransPath] gdown not installed, trying alternative method...")
            print("[CTransPath] For best results: pip install gdown")
    except Exception as e:
        if verbose:
            print(f"[CTransPath] gdown failed: {e}")
    
    # Try HuggingFace mirror if available
    if HAS_HF_HUB:
        try:
            if verbose:
                print("[CTransPath] Trying HuggingFace mirror...")
            # Some users have uploaded CTransPath to HuggingFace
            downloaded_path = hf_hub_download(
                repo_id="xiyuez/ctranspath",
                filename="ctranspath.pth",
                local_dir=os.path.dirname(save_path),
                local_dir_use_symlinks=False,
            )
            if os.path.exists(downloaded_path):
                if downloaded_path != save_path:
                    import shutil
                    shutil.move(downloaded_path, save_path)
                if verbose:
                    print(f"[CTransPath] Successfully downloaded to {save_path}")
                return True
        except Exception as e:
            if verbose:
                print(f"[CTransPath] HuggingFace mirror failed: {e}")
    
    # Manual download instructions
    if verbose:
        print("\n[CTransPath] Automatic download failed.")
        print("[CTransPath] Please download manually:")
        print("  Option 1 (recommended): pip install gdown && gdown 1DoDx_70_TLj98gTf6YTXnu4tFhsFocDX")
        print("  Option 2: Download from https://drive.google.com/u/0/uc?id=1DoDx_70_TLj98gTf6YTXnu4tFhsFocDX")
        print(f"  Then move to: {save_path}")
    return False


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class Config:
    """Optimized configuration for 90% target accuracy with pathology backbones."""
    
    # Data paths
    ROOT_DIR: str = "/home/rapids/notebooks/slima/Zenodo_Anorak_original"
    IMAGE_DIR: str = None
    MASK_DIR: str = None
    XLS_PATH: str = "/home/rapids/notebooks/slima/overlay_index ver 9 nov 2025.xlsx"
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/pathology_backbone_90_target"
    
    # Pathology model paths
    # CTransPath: Swin-Tiny trained on 15M pathology patches (768-dim output)
    # Download from: https://github.com/Xiyue-Wang/TransPath
    # UNI2-h: ViT-H/14 trained on millions of patches (1280-dim output)  
    # Download from: https://huggingface.co/MahmoodLab/UNI2-h
    UNI_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/uni2_h_pytorch_model.bin"
    CTRANSPATH_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/ctranspath.pth"
    
    # Classes
    INCLUDE_PATTERNS: str = "lepidic,acinar,papillary,micropapillary,solid,mucinous"
    
    # Model - Backbone options: "uni", "ctranspath", "resnet101", "resnet50", "ensemble"
    # CTransPath: Swin-Tiny trained on 15M pathology patches (768-dim output)
    # Ensemble: Combines CTransPath + ResNet101 predictions
    BACKBONE: str = "ensemble"  # Use ensemble for best results
    EMBED_DIM: int = 512
    FREEZE_BACKBONE_LAYERS: int = 2  # Freeze first 2 Swin stages to preserve pathology features
    
    # Training - OPTIMIZED FOR 90% TARGET v2
    EPOCHS: int = 400  # Even more epochs for full convergence
    BATCH_SIZE: int = 16  # Standard batch size
    LR: float = 2e-4  # Head LR
    LR_BACKBONE: float = 1e-5  # Backbone LR
    WEIGHT_DECAY: float = 5e-5
    WARMUP_EPOCHS: int = 20  # Longer warmup
    
    # Image - Keep 224 for Swin compatibility (window_size=7 needs 224/4/7=8)
    # Higher resolution would require architecture changes
    IMG_SIZE: int = 224
    
    # FuzzyArcLoss - Tuned for better discrimination
    S_SCALE: float = 32.0  # Slightly higher scale
    M_MARGIN: float = 0.40  # Higher margin for better separation
    TAU: float = 0.45  # Adjusted fuzzy threshold
    
    # ROI settings
    USE_MASK_AS_CHANNEL: bool = False
    USE_ROI_CROP: bool = True
    ROI_PADDING: int = 24
    MASK_THRESH: float = 0.5
    
    # Data splits
    VAL_SIZE: float = 0.15
    TEST_SIZE: float = 0.15
    SEED: int = 42
    
    # Distributed
    NUM_WORKERS: int = 0
    PIN_MEMORY: bool = False
    PERSISTENT_WORKERS: bool = False
    MIXED_PRECISION: str = "fp16"
    GRAD_ACCUM_STEPS: int = 2
    
    # Regularization
    LABEL_SMOOTHING: float = 0.05
    DROPOUT: float = 0.15
    
    # Advanced augmentation
    USE_CUTMIX: bool = True
    CUTMIX_ALPHA: float = 1.0
    CUTMIX_PROB: float = 0.4
    
    USE_MIXUP: bool = True
    MIXUP_ALPHA: float = 0.2
    MIXUP_PROB: float = 0.2
    
    USE_STAIN_AUG: bool = True
    STAIN_AUG_PROB: float = 0.5  # Increased for better generalization
    
    # Class-weighted sampling - ENHANCED for minority classes
    USE_WEIGHTED_SAMPLER: bool = True
    SOLID_CLASS_BOOST: float = 1.5  # Boost solid class
    LEPIDIC_CLASS_BOOST: float = 2.0  # Boost lepidic class (smallest, worst performing)
    ACINAR_CLASS_BOOST: float = 1.3  # Slight boost for acinar
    
    # Test-Time Augmentation
    USE_TTA: bool = True
    TTA_AUGMENTATIONS: int = 7  # More TTA for better predictions
    
    # Focal Loss
    USE_FOCAL_LOSS: bool = True
    FOCAL_GAMMA: float = 2.5  # Slightly higher gamma for harder focus
    
    # Ensemble settings
    ENSEMBLE_WEIGHTS: dict = None  # Will be set in __post_init__
    
    def __post_init__(self):
        if self.IMAGE_DIR is None:
            self.IMAGE_DIR = f"{self.ROOT_DIR}/image"
        if self.MASK_DIR is None:
            self.MASK_DIR = f"{self.ROOT_DIR}/mask"
        if self.ENSEMBLE_WEIGHTS is None:
            # Default ensemble weights: CTransPath gets higher weight (pathology-specific)
            self.ENSEMBLE_WEIGHTS = {"ctranspath": 0.6, "resnet101": 0.4}


# Global config instance
config = Config()


# ==============================================================================
# UTILITIES
# ==============================================================================

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
MAT_EXCLUDE = {"__header__", "__version__", "__globals__"}
MAT_PRIOR = ["mask", "Mask", "BW", "bw", "label", "Label", "roi", "ROI", "seg", "Seg"]


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def list_images(d: str) -> List[Path]:
    out = []
    base = Path(d)
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            out.append(p)
    return sorted(out)


def list_mats(d: str) -> List[Path]:
    return sorted([p for p in Path(d).rglob("*.mat") if p.is_file()])


def normalize_key(stem: str) -> str:
    s = stem.lower()
    s = re.sub(r"([_-])(mask|seg|roi|label|overlay)([_-]?\d+)?$", "", s)
    s = re.sub(r"[ \t\-_]+", "_", s).strip("_")
    return s


def build_mat_index(mask_dir: str) -> Dict[str, str]:
    idx = {}
    for p in list_mats(mask_dir):
        stem = p.stem
        for key in (stem, stem.lower(), normalize_key(stem)):
            if key not in idx or p.stat().st_size > Path(idx[key]).stat().st_size:
                idx[key] = str(p)
    return idx


def pair_images_with_masks(image_dir: str, mask_dir: str) -> pd.DataFrame:
    imgs = list_images(image_dir)
    mat_index = build_mat_index(mask_dir)
    
    rows, unmatched = [], []
    for ip in imgs:
        stem = ip.stem
        key_norm = normalize_key(stem)
        mp = mat_index.get(stem) or mat_index.get(stem.lower()) or mat_index.get(key_norm)
        if mp:
            rows.append({
                "image_path": str(ip),
                "mask_path": mp,
                "base": stem,
                "base_norm": key_norm
            })
        else:
            unmatched.append(ip.name)
    
    print(f"[PAIRING] matched={len(rows)} unmatched={len(unmatched)}")
    return pd.DataFrame(rows)


def read_labels_from_xls(xls_path: str) -> Tuple[Dict[str, str], str]:
    df = pd.read_excel(xls_path)
    label_candidates = ["pattern", "label", "class", "type", "histologic_pattern"]
    file_candidates = ["tile_id", "overlay_file", "image_file", "file", "filename"]
    
    label_col = next((c for c in label_candidates if c in df.columns), None)
    if label_col is None:
        raise ValueError(f"No label column found in {xls_path}")
    
    file_col = next((c for c in file_candidates if c in df.columns), None)
    if file_col is None:
        raise ValueError(f"No file column found in {xls_path}")
    
    m = {}
    for _, r in df.iterrows():
        f = str(r[file_col])
        stem = Path(f).stem
        lbl = str(r[label_col]).strip()
        m[stem] = lbl
        m[normalize_key(stem)] = lbl
        m[stem.lower()] = lbl
    
    return m, label_col


def _load_mat_any(path: str) -> np.ndarray:
    if loadmat is not None:
        try:
            d = loadmat(path)
            for k in MAT_PRIOR:
                if k in d and isinstance(d[k], np.ndarray) and d[k].ndim >= 2:
                    return d[k]
            best, sz = None, -1
            for k, v in d.items():
                if k in MAT_EXCLUDE:
                    continue
                if isinstance(v, np.ndarray) and v.ndim >= 2:
                    s = np.prod(v.shape[:2])
                    if s > sz:
                        best, sz = v, s
            if best is not None:
                return best
        except Exception:
            pass
    
    if h5py is not None:
        try:
            with h5py.File(path, "r") as f:
                for k in MAT_PRIOR:
                    if k in f and f[k].ndim >= 2:
                        return np.array(f[k])
                for k in f.keys():
                    if k not in MAT_EXCLUDE and f[k].ndim >= 2:
                        return np.array(f[k])
        except Exception:
            pass
    
    return np.ones((224, 224), dtype=np.uint8)


def load_mask_from_mat(path: str) -> Image.Image:
    arr = _load_mat_any(path)
    if arr.ndim == 3 and arr.shape[0] in (1, 2, 3, 4):
        arr = arr[0]
    elif arr.ndim == 3 and arr.shape[-1] in (1, 2, 3, 4):
        arr = arr[..., 0]
    if arr.ndim > 2:
        arr = arr[..., 0] if arr.shape[-1] <= 4 else np.argmax(arr, axis=-1)
    mask = (arr.astype(np.float32) > 0).astype(np.uint8) * 255
    return Image.fromarray(mask, mode="L")


# ==============================================================================
# STAIN AUGMENTATION - Histology-specific color augmentation
# ==============================================================================

class StainAugmentation:
    """
    H&E stain augmentation for histology images.
    Simulates variations in staining intensity and hue that occur across different labs.
    """
    
    def __init__(self, 
                 brightness_range=(0.8, 1.2),
                 contrast_range=(0.8, 1.2),
                 hue_shift_range=(-0.02, 0.02),
                 saturation_range=(0.8, 1.3),
                 he_ratio_range=(0.9, 1.1)):
        self.brightness_range = brightness_range
        self.contrast_range = contrast_range
        self.hue_shift_range = hue_shift_range
        self.saturation_range = saturation_range
        self.he_ratio_range = he_ratio_range
    
    def __call__(self, img: Image.Image) -> Image.Image:
        """Apply stain augmentation to PIL image."""
        img_array = np.array(img).astype(np.float32) / 255.0
        
        # Convert to HSV for targeted modifications
        # Simple RGB -> HSV approximation
        r, g, b = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2]
        
        # Brightness augmentation
        brightness = random.uniform(*self.brightness_range)
        img_array = np.clip(img_array * brightness, 0, 1)
        
        # Contrast augmentation
        contrast = random.uniform(*self.contrast_range)
        mean = img_array.mean()
        img_array = np.clip((img_array - mean) * contrast + mean, 0, 1)
        
        # H&E specific: Modify pink/purple (Eosin) and blue (Hematoxylin) channels
        # Eosin is primarily in red channel, Hematoxylin in blue
        he_ratio = random.uniform(*self.he_ratio_range)
        
        # Slight shift in R/B balance to simulate stain variation
        img_array[:,:,0] = np.clip(img_array[:,:,0] * he_ratio, 0, 1)  # Red (Eosin)
        img_array[:,:,2] = np.clip(img_array[:,:,2] / he_ratio, 0, 1)  # Blue (Hematoxylin)
        
        # Saturation adjustment
        saturation = random.uniform(*self.saturation_range)
        gray = 0.299 * img_array[:,:,0] + 0.587 * img_array[:,:,1] + 0.114 * img_array[:,:,2]
        gray = gray[:,:,np.newaxis]
        img_array = np.clip(gray + (img_array - gray) * saturation, 0, 1)
        
        # Convert back to uint8 PIL
        img_array = (img_array * 255).astype(np.uint8)
        return Image.fromarray(img_array)


# ==============================================================================
# CUTMIX AND MIXUP UTILITIES
# ==============================================================================

def rand_bbox(size, lam):
    """Generate random bounding box for CutMix."""
    W, H = size[2], size[3]
    cut_rat = np.sqrt(1. - lam)
    cut_w = int(W * cut_rat)
    cut_h = int(H * cut_rat)
    
    cx = np.random.randint(W)
    cy = np.random.randint(H)
    
    bbx1 = np.clip(cx - cut_w // 2, 0, W)
    bby1 = np.clip(cy - cut_h // 2, 0, H)
    bbx2 = np.clip(cx + cut_w // 2, 0, W)
    bby2 = np.clip(cy + cut_h // 2, 0, H)
    
    return bbx1, bby1, bbx2, bby2


def cutmix_data(x, y, alpha=1.0):
    """Apply CutMix augmentation."""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    
    batch_size = x.size(0)
    index = torch.randperm(batch_size).to(x.device)
    
    bbx1, bby1, bbx2, bby2 = rand_bbox(x.size(), lam)
    x[:, :, bbx1:bbx2, bby1:bby2] = x[index, :, bbx1:bbx2, bby1:bby2]
    
    # Adjust lambda based on actual box area
    lam = 1 - ((bbx2 - bbx1) * (bby2 - bby1) / (x.size(-1) * x.size(-2)))
    
    return x, y, y[index], lam


def mixup_data(x, y, alpha=0.2):
    """Apply MixUp augmentation."""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    
    batch_size = x.size(0)
    index = torch.randperm(batch_size).to(x.device)
    
    mixed_x = lam * x + (1 - lam) * x[index, :]
    
    return mixed_x, y, y[index], lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Compute MixUp/CutMix loss."""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


# ==============================================================================
# DATASET WITH ADVANCED AUGMENTATION
# ==============================================================================

class HistMaskDatasetAdvanced(Dataset):
    """Dataset with stain augmentation and pathology-specific preprocessing."""
    
    def __init__(
        self,
        rows: pd.DataFrame,
        label_col: str,
        label2id: Dict[str, int],
        img_size: int = 224,
        aug: bool = True,
        use_mask_as_channel: bool = False,
        use_roi_crop: bool = True,
        roi_padding: int = 24,
        mask_thresh: float = 0.5,
        strong_aug: bool = True,
        use_stain_aug: bool = True,
        backbone_type: str = "uni",
    ):
        self.rows = rows.reset_index(drop=True)
        self.label_col = label_col
        self.label2id = label2id
        self.img_size = img_size
        self.aug = aug
        self.use_mask_as_channel = use_mask_as_channel
        self.use_roi_crop = use_roi_crop
        self.roi_padding = roi_padding
        self.mask_thresh = mask_thresh
        self.strong_aug = strong_aug and aug
        self.use_stain_aug = use_stain_aug and aug
        self.backbone_type = backbone_type
        
        # Stain augmentation
        self.stain_aug = StainAugmentation() if self.use_stain_aug else None
        
        # Color jitter for basic augmentation
        self.cj = transforms.ColorJitter(0.3, 0.3, 0.3, 0.1)
        
        # Normalization based on backbone type
        if backbone_type in ["uni", "ctranspath"]:
            # Pathology models typically use ImageNet normalization
            self.normalize_mean = [0.485, 0.456, 0.406]
            self.normalize_std = [0.229, 0.224, 0.225]
        else:
            self.normalize_mean = [0.485, 0.456, 0.406]
            self.normalize_std = [0.229, 0.224, 0.225]
    
    def __len__(self):
        return len(self.rows)
    
    def _roi_crop(self, img: Image.Image, msk: Image.Image):
        m = np.array(msk) > 0
        if not m.any():
            return img, msk
        ys, xs = np.where(m)
        y0 = max(0, ys.min() - self.roi_padding)
        y1 = min(m.shape[0], ys.max() + 1 + self.roi_padding)
        x0 = max(0, xs.min() - self.roi_padding)
        x1 = min(m.shape[1], xs.max() + 1 + self.roi_padding)
        return img.crop((x0, y0, x1, y1)), msk.crop((x0, y0, x1, y1))
    
    def _joint_transform(self, img: Image.Image, msk: Image.Image):
        """Apply synchronized transforms to image and mask."""
        if self.aug:
            # Random resized crop
            i, j, h, w = transforms.RandomResizedCrop.get_params(
                img, scale=(0.6, 1.0), ratio=(0.9, 1.1)
            )
            img = TF.resized_crop(img, i, j, h, w, 
                                  size=[self.img_size, self.img_size],
                                  interpolation=InterpolationMode.BILINEAR)
            msk = TF.resized_crop(msk, i, j, h, w,
                                  size=[self.img_size, self.img_size],
                                  interpolation=InterpolationMode.NEAREST)
            
            # Flips
            if random.random() < 0.5:
                img = TF.hflip(img)
                msk = TF.hflip(msk)
            if random.random() < 0.5:
                img = TF.vflip(img)
                msk = TF.vflip(msk)
            
            # Rotation (90 degree increments for pathology)
            if random.random() < 0.5:
                k = random.choice([1, 2, 3])
                img = TF.rotate(img, k * 90, interpolation=InterpolationMode.BILINEAR)
                msk = TF.rotate(msk, k * 90, interpolation=InterpolationMode.NEAREST)
            
            # Strong augmentation
            if self.strong_aug:
                # Gaussian blur
                if random.random() < 0.3:
                    img = TF.gaussian_blur(img, kernel_size=random.choice([3, 5]))
                
                # Adjust sharpness
                if random.random() < 0.2:
                    img = TF.adjust_sharpness(img, sharpness_factor=random.uniform(1.5, 2.5))
        else:
            img = img.resize((self.img_size, self.img_size), resample=Image.BILINEAR)
            msk = msk.resize((self.img_size, self.img_size), resample=Image.NEAREST)
        
        return img, msk
    
    def __getitem__(self, idx: int):
        r = self.rows.iloc[idx]
        img = Image.open(r["image_path"]).convert("RGB")
        msk = load_mask_from_mat(r["mask_path"])
        
        # ROI crop
        if self.use_roi_crop:
            img, msk = self._roi_crop(img, msk)
        
        # Joint transforms
        img, msk = self._joint_transform(img, msk)
        
        # Stain augmentation (histology-specific)
        if self.use_stain_aug and self.stain_aug and random.random() < config.STAIN_AUG_PROB:
            img = self.stain_aug(img)
        
        # Color augmentation
        if self.aug:
            img = self.cj(img)
        
        # To tensor and normalize
        img_t = TF.to_tensor(img)
        img_t = TF.normalize(img_t, mean=self.normalize_mean, std=self.normalize_std)
        
        if self.use_mask_as_channel:
            msk_t = (TF.to_tensor(msk) > self.mask_thresh).float()
            x = torch.cat([img_t, msk_t], dim=0)
        else:
            x = img_t
        
        y = self.label2id[str(r[self.label_col])]
        
        return x, y, r["image_path"]


# ==============================================================================
# PATHOLOGY FOUNDATION MODELS
# ==============================================================================

class UNIBackbone(nn.Module):
    """
    UNI2-h - Harvard/MGH Pathology Foundation Model (Latest Version)
    HuggingFace: https://huggingface.co/MahmoodLab/UNI2-h
    
    Based on ViT-H/14 (huge), trained on millions of pathology patches.
    Output dimension: 1280 (ViT-H hidden dim)
    
    Also supports original UNI (ViT-L/16, 1024 dim) for backward compatibility.
    """
    
    def __init__(self, checkpoint_path: str = None, freeze_layers: int = 0, model_variant: str = "uni2_h"):
        super().__init__()
        
        if HAS_TIMM:
            # Determine model variant based on checkpoint path or explicit variant
            if checkpoint_path and "uni2" in checkpoint_path.lower():
                model_variant = "uni2_h"
            elif checkpoint_path and "uni_pytorch" in checkpoint_path.lower():
                model_variant = "uni"
            
            if model_variant == "uni2_h":
                # UNI2-h uses ViT-H/14 (huge) - 1280 dim output
                # vit_huge_patch14_224 has: patch_size=14, embed_dim=1280, depth=32, num_heads=16
                self.model = timm.create_model(
                    'vit_huge_patch14_clip_224',  # CLIP-pretrained ViT-H/14 architecture
                    pretrained=False,
                    num_classes=0,  # Remove classification head
                )
                self.out_features = 1280
                print(f"[UNI2-h] Using ViT-H/14 architecture, output dim: {self.out_features}")
            else:
                # Original UNI uses ViT-L/16 - 1024 dim output
                self.model = timm.create_model(
                    'vit_large_patch16_224',
                    pretrained=False,
                    num_classes=0,
                )
                self.out_features = 1024
                print(f"[UNI] Using ViT-L/16 architecture, output dim: {self.out_features}")
            
            # Load weights if available
            if checkpoint_path:
                self._load_checkpoint(checkpoint_path)
            else:
                print(f"[UNI] No checkpoint provided, using random initialization")
                print("[UNI] Download from: https://huggingface.co/MahmoodLab/UNI2-h")
            
            # Freeze early layers for transfer learning
            if freeze_layers > 0:
                for i, block in enumerate(self.model.blocks):
                    if i < freeze_layers:
                        for param in block.parameters():
                            param.requires_grad = False
        else:
            raise ImportError("timm is required for UNI backbone. Install with: pip install timm")
    
    def _load_checkpoint(self, checkpoint_path: str):
        """Load checkpoint from .bin or .safetensors format."""
        
        # Check for safetensors in same directory
        checkpoint_dir = os.path.dirname(checkpoint_path)
        safetensor_path = os.path.join(checkpoint_dir, "model.safetensors")
        
        if os.path.exists(safetensor_path):
            print(f"[UNI2-h] Loading safetensors checkpoint from {safetensor_path}")
            try:
                from safetensors.torch import load_file
                state_dict = load_file(safetensor_path)
                self._apply_state_dict(state_dict)
                print("[UNI2-h] Safetensors checkpoint loaded successfully")
                return
            except ImportError:
                print("[UNI2-h] safetensors not installed, trying .bin format")
                print("[UNI2-h] Install with: pip install safetensors")
        
        if os.path.exists(checkpoint_path):
            print(f"[UNI] Loading checkpoint from {checkpoint_path}")
            state_dict = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
            self._apply_state_dict(state_dict)
            print("[UNI] Checkpoint loaded successfully")
        else:
            print(f"[UNI] Checkpoint not found at {checkpoint_path}")
    
    def _apply_state_dict(self, state_dict: dict):
        """Apply state dict with format handling."""
        # Handle different checkpoint formats
        if 'model' in state_dict:
            state_dict = state_dict['model']
        if 'state_dict' in state_dict:
            state_dict = state_dict['state_dict']
        
        # Remove common prefixes
        clean_dict = {}
        for k, v in state_dict.items():
            new_k = k
            for prefix in ['model.', 'backbone.', 'encoder.', 'visual.']:
                if new_k.startswith(prefix):
                    new_k = new_k[len(prefix):]
            clean_dict[new_k] = v
        
        # Load with strict=False to handle minor mismatches
        missing, unexpected = self.model.load_state_dict(clean_dict, strict=False)
        if missing:
            print(f"[UNI] Missing keys: {len(missing)} (may be expected for head)")
        if unexpected:
            print(f"[UNI] Unexpected keys: {len(unexpected)}")
    
    def forward(self, x):
        return self.model(x)


class ConvStem(nn.Module):
    """
    CTransPath's ConvStem patch embedding - EXACT architecture from the paper.
    
    Architecture (for embed_dim=96):
    - proj.0: Conv2d(3, 12, k=3, s=2, p=1)   # embed_dim // 8 = 12
    - proj.1: BatchNorm2d(12)
    - proj.2: GELU
    - proj.3: Conv2d(12, 24, k=3, s=2, p=1)  # embed_dim // 4 = 24
    - proj.4: BatchNorm2d(24)
    - proj.5: GELU
    - proj.6: Conv2d(24, 96, k=1, s=1, p=0)  # 1x1 conv to expand
    - proj.7: BatchNorm2d(96)
    
    Total stride = 4 (same as patch_size=4)
    Output format: (B, H, W, C) to match timm's Swin expectations
    """
    
    def __init__(self, img_size=224, patch_size=4, in_chans=3, embed_dim=96):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.grid_size = (img_size // patch_size, img_size // patch_size)
        self.num_patches = self.grid_size[0] * self.grid_size[1]
        
        # CTransPath ConvStem: 3 -> embed_dim//8 -> embed_dim//4 -> embed_dim
        # For embed_dim=96: 3 -> 12 -> 24 -> 96
        stem_dim1 = embed_dim // 8  # = 12
        stem_dim2 = embed_dim // 4  # = 24
        
        self.proj = nn.Sequential(
            # Stage 1: 3 -> 12, stride 2
            nn.Conv2d(in_chans, stem_dim1, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(stem_dim1),
            nn.GELU(),
            # Stage 2: 12 -> 24, stride 2
            nn.Conv2d(stem_dim1, stem_dim2, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(stem_dim2),
            nn.GELU(),
            # Stage 3: 24 -> 96, 1x1 conv (no stride)
            nn.Conv2d(stem_dim2, embed_dim, kernel_size=1, stride=1, padding=0, bias=False),
            nn.BatchNorm2d(embed_dim),
        )
        self.norm = nn.LayerNorm(embed_dim)
    
    def forward(self, x):
        # x: (B, C, H, W)
        x = self.proj(x)  # (B, embed_dim, H/4, W/4)
        
        # timm's Swin expects (B, H, W, C) format
        x = x.permute(0, 2, 3, 1)  # (B, H/4, W/4, embed_dim)
        x = self.norm(x)
        return x


class CTransPathBackbone(nn.Module):
    """
    CTransPath - Pathology Foundation Model
    GitHub: https://github.com/Xiyue-Wang/TransPath
    
    CTransPath uses Swin-Tiny architecture with a custom ConvStem patch embedding.
    The ConvStem uses Conv-BN-ReLU-Conv-BN instead of a single Conv, which provides
    better local feature extraction for pathology images.
    
    Output dimension: 768
    """
    
    def __init__(self, checkpoint_path: str = None, freeze_layers: int = 0):
        super().__init__()
        
        if HAS_TIMM:
            print("[CTransPath] Building Swin-Tiny with ConvStem for CTransPath...")
            
            # Create base Swin-Tiny
            self.model = timm.create_model(
                'swin_tiny_patch4_window7_224',
                pretrained=False,
                num_classes=0,
            )
            
            # Replace patch_embed with ConvStem
            embed_dim = 96  # Swin-Tiny embed_dim
            self.model.patch_embed = ConvStem(
                img_size=224,
                patch_size=4,
                in_chans=3,
                embed_dim=embed_dim
            )
            
            self.out_features = self.model.num_features  # 768
            print(f"[CTransPath] Model with ConvStem created, output dim: {self.out_features}")
            
            # Load CTransPath weights
            if checkpoint_path and os.path.exists(checkpoint_path):
                print(f"[CTransPath] Loading checkpoint from {checkpoint_path}")
                try:
                    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
                    
                    # Extract state dict
                    if isinstance(checkpoint, dict):
                        if 'model' in checkpoint:
                            state_dict = checkpoint['model']
                        elif 'state_dict' in checkpoint:
                            state_dict = checkpoint['state_dict']
                        else:
                            state_dict = checkpoint
                    else:
                        state_dict = checkpoint
                    
                    print(f"[CTransPath] Checkpoint has {len(state_dict)} keys")
                    
                    # Remap keys for downsample placement difference
                    remapped = self._remap_ctranspath_keys(state_dict)
                    print(f"[CTransPath] After remapping: {len(remapped)} keys")
                    
                    # Get model state
                    model_state = self.model.state_dict()
                    
                    # Filter to matching keys with correct shapes
                    filtered = {}
                    mismatches = []
                    missing_in_ckpt = []
                    
                    for key in model_state.keys():
                        if key in remapped:
                            if remapped[key].shape == model_state[key].shape:
                                filtered[key] = remapped[key]
                            else:
                                mismatches.append((key, remapped[key].shape, model_state[key].shape))
                        else:
                            missing_in_ckpt.append(key)
                    
                    print(f"[CTransPath] Matched keys: {len(filtered)}/{len(model_state)}")
                    
                    if mismatches:
                        print(f"[CTransPath] Shape mismatches: {len(mismatches)}")
                        for k, cs, ms in mismatches[:3]:
                            print(f"  - {k}: ckpt={cs} vs model={ms}")
                    
                    if missing_in_ckpt:
                        print(f"[CTransPath] Keys not in checkpoint: {len(missing_in_ckpt)}")
                        for k in missing_in_ckpt[:5]:
                            print(f"  - {k}")
                    
                    # Load weights
                    if len(filtered) >= 150:  # Most keys should match
                        self.model.load_state_dict(filtered, strict=False)
                        loaded_pct = 100 * len(filtered) / len(model_state)
                        print(f"[CTransPath] ✓ Loaded {len(filtered)} keys ({loaded_pct:.1f}%)")
                        
                        # Check if patch_embed was loaded
                        patch_keys = [k for k in filtered if 'patch_embed' in k]
                        print(f"[CTransPath] ✓ Patch embedding keys loaded: {len(patch_keys)}")
                    else:
                        print("[CTransPath] WARNING: Too few keys matched!")
                        print("[CTransPath] Falling back to ImageNet pretrained Swin-Tiny")
                        self._fallback_to_imagenet()
                        
                except Exception as e:
                    print(f"[CTransPath] Error loading checkpoint: {e}")
                    import traceback
                    traceback.print_exc()
                    print("[CTransPath] Falling back to ImageNet pretrained")
                    self._fallback_to_imagenet()
            else:
                print("[CTransPath] No checkpoint found, using ImageNet pretrained")
                self._fallback_to_imagenet()
            
            # Freeze early layers if requested
            if freeze_layers > 0:
                for i, layer in enumerate(self.model.layers):
                    if i < freeze_layers:
                        for param in layer.parameters():
                            param.requires_grad = False
        else:
            raise ImportError("timm is required. Install with: pip install timm")
    
    def _fallback_to_imagenet(self):
        """Fall back to ImageNet pretrained Swin-Tiny (standard patch_embed)."""
        self.model = timm.create_model(
            'swin_tiny_patch4_window7_224',
            pretrained=True,
            num_classes=0,
        )
        self.out_features = self.model.num_features
    
    def _remap_ctranspath_keys(self, state_dict: dict) -> dict:
        """
        Remap CTransPath checkpoint keys to our model format.
        
        Key differences:
        1. CTransPath: downsample at END of stage (layers.X.downsample)
           timm: downsample at START of next stage (layers.X+1.downsample) 
        2. Skip attn_mask and relative_position_index (computed dynamically)
        """
        remapped = {}
        
        for key, value in state_dict.items():
            # Skip head/fc layers
            if key.startswith('head.') or key.startswith('fc.'):
                continue
            
            # Skip buffers that are computed dynamically
            if 'attn_mask' in key or 'relative_position_index' in key:
                continue
            
            new_key = key
            
            # Remap downsample: CTransPath layers.X.downsample -> timm layers.X+1.downsample
            if '.downsample.' in key:
                for i in range(3):  # Stages 0, 1, 2 have downsamples
                    if f'layers.{i}.downsample.' in key:
                        new_key = key.replace(f'layers.{i}.downsample.', f'layers.{i+1}.downsample.')
                        break
            
            remapped[new_key] = value
        
        return remapped
    
    def forward(self, x):
        return self.model(x)


class EnsembleBackbone(nn.Module):
    """
    Ensemble of CTransPath + ResNet101 for improved performance.
    Combines pathology-specific features from CTransPath with robust
    features from ImageNet-pretrained ResNet.
    """
    
    def __init__(self, ctranspath_checkpoint: str = None, freeze_layers: int = 0,
                 img_size: int = 384, weights: dict = None):
        super().__init__()
        
        self.weights = weights or {"ctranspath": 0.6, "resnet101": 0.4}
        
        print(f"[ENSEMBLE] Building CTransPath + ResNet101 ensemble...")
        print(f"[ENSEMBLE] Weights: CTransPath={self.weights['ctranspath']}, ResNet={self.weights['resnet101']}")
        
        # Build CTransPath backbone
        self.ctranspath = CTransPathBackbone(
            checkpoint_path=ctranspath_checkpoint,
            freeze_layers=freeze_layers
        )
        self.ctranspath_dim = self.ctranspath.out_features  # 768
        
        # Build ResNet101 backbone
        if HAS_TIMM:
            self.resnet = timm.create_model(
                'resnet101',
                pretrained=True,
                num_classes=0,
                global_pool='avg'
            )
            self.resnet_dim = self.resnet.num_features  # 2048
        else:
            self.resnet = models.resnet101(weights=models.ResNet101_Weights.IMAGENET1K_V2)
            self.resnet.fc = nn.Identity()
            self.resnet_dim = 2048
        
        # Project both to same dimension
        self.proj_dim = 512
        self.ctranspath_proj = nn.Sequential(
            nn.Linear(self.ctranspath_dim, self.proj_dim),
            nn.LayerNorm(self.proj_dim),
            nn.GELU()
        )
        self.resnet_proj = nn.Sequential(
            nn.Linear(self.resnet_dim, self.proj_dim),
            nn.LayerNorm(self.proj_dim),
            nn.GELU()
        )
        
        # Combined output dimension
        self.out_features = self.proj_dim
        
        print(f"[ENSEMBLE] CTransPath: {self.ctranspath_dim}d → {self.proj_dim}d")
        print(f"[ENSEMBLE] ResNet101: {self.resnet_dim}d → {self.proj_dim}d")
        print(f"[ENSEMBLE] Final output: {self.out_features}d")
    
    def forward(self, x):
        # Get features from both backbones
        feat_ctp = self.ctranspath(x)  # (B, 768)
        feat_res = self.resnet(x)       # (B, 2048)
        
        # Project to same dimension
        feat_ctp = self.ctranspath_proj(feat_ctp)  # (B, 512)
        feat_res = self.resnet_proj(feat_res)       # (B, 512)
        
        # Weighted combination
        w_ctp = self.weights['ctranspath']
        w_res = self.weights['resnet101']
        
        combined = w_ctp * feat_ctp + w_res * feat_res  # (B, 512)
        
        return combined


def build_backbone_pathology(
    backbone_type: str = "uni",
    pretrained: bool = True,
    embed_dim: int = 512,
    in_channels: int = 3,
    dropout: float = 0.2,
    uni_checkpoint: str = None,
    ctranspath_checkpoint: str = None,
    freeze_backbone_layers: int = 0,
    img_size: int = 224,
    ensemble_weights: dict = None,
    verbose: bool = True,
) -> Tuple[nn.Module, int]:
    """Build pathology-specific backbone with embedding head."""
    
    if verbose:
        print(f"[BACKBONE] Building {backbone_type} backbone...")
        if freeze_backbone_layers > 0:
            print(f"[BACKBONE] Freezing first {freeze_backbone_layers} transformer layers")
    
    if backbone_type == "ensemble":
        # Ensemble of CTransPath + ResNet101
        try:
            backbone = EnsembleBackbone(
                ctranspath_checkpoint=ctranspath_checkpoint,
                freeze_layers=freeze_backbone_layers,
                img_size=img_size,
                weights=ensemble_weights
            )
            backbone_dim = backbone.out_features  # Already 512
            if verbose:
                print(f"[BACKBONE] Ensemble backbone ready, output dim: {backbone_dim}")
            
            # For ensemble, backbone already outputs embed_dim, so minimal head
            head = nn.Sequential(
                nn.Dropout(dropout),
            )
            model = nn.Sequential(backbone, head)
            return model, embed_dim
            
        except Exception as e:
            if verbose:
                print(f"[BACKBONE] Failed to build ensemble: {e}")
                import traceback
                traceback.print_exc()
                print("[BACKBONE] Falling back to CTransPath only")
            backbone_type = "ctranspath"
    
    if backbone_type == "uni":
        # Check for UNI2-h checkpoint (safetensors or bin)
        checkpoint_dir = os.path.dirname(uni_checkpoint) if uni_checkpoint else ""
        safetensor_path = os.path.join(checkpoint_dir, "model.safetensors") if checkpoint_dir else ""
        
        checkpoint_exists = (
            (uni_checkpoint and os.path.exists(uni_checkpoint)) or
            (safetensor_path and os.path.exists(safetensor_path))
        )
        
        if not checkpoint_exists:
            if verbose:
                print(f"[BACKBONE] UNI2-h checkpoint not found at: {uni_checkpoint}")
                print("[BACKBONE] Attempting to download UNI2-h from HuggingFace...")
            
            # Try to download
            if download_uni_model(uni_checkpoint, verbose=verbose):
                # Re-check after download
                checkpoint_exists = (
                    (uni_checkpoint and os.path.exists(uni_checkpoint)) or
                    (safetensor_path and os.path.exists(safetensor_path))
                )
            
            if not checkpoint_exists:
                if verbose:
                    print("[BACKBONE] UNI2-h download failed, falling back to ResNet-101")
                backbone_type = "resnet101"
        
        # Now try to load UNI2-h if we have the checkpoint
        if backbone_type == "uni" and checkpoint_exists:
            try:
                backbone = UNIBackbone(checkpoint_path=uni_checkpoint)
                backbone_dim = backbone.out_features
                if verbose:
                    print(f"[BACKBONE] UNI2-h backbone loaded, output dim: {backbone_dim}")
            except Exception as e:
                if verbose:
                    print(f"[BACKBONE] Failed to load UNI2-h: {e}")
                    import traceback
                    traceback.print_exc()
                    print("[BACKBONE] Falling back to ResNet-101")
                backbone_type = "resnet101"
    
    elif backbone_type == "ctranspath":
        # CTransPath - Swin transformer trained on pathology
        try:
            backbone = CTransPathBackbone(
                checkpoint_path=ctranspath_checkpoint,
                freeze_layers=freeze_backbone_layers
            )
            backbone_dim = backbone.out_features
            if verbose:
                print(f"[BACKBONE] CTransPath/Swin backbone ready, output dim: {backbone_dim}")
        except Exception as e:
            if verbose:
                print(f"[BACKBONE] Failed to load CTransPath: {e}")
                print("[BACKBONE] Falling back to ResNet-101")
            backbone_type = "resnet101"
    
    if backbone_type in ["resnet50", "resnet101"]:
        # Fallback to ImageNet pretrained ResNet
        if backbone_type == "resnet50":
            m = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None)
        else:
            m = models.resnet101(weights=models.ResNet101_Weights.IMAGENET1K_V2 if pretrained else None)
        
        # Modify first conv for 4-channel input if needed
        if in_channels != 3:
            old = m.conv1
            m.conv1 = nn.Conv2d(
                in_channels, old.out_channels,
                kernel_size=old.kernel_size,
                stride=old.stride,
                padding=old.padding,
                bias=False
            )
            with torch.no_grad():
                m.conv1.weight[:, :3] = old.weight
                if in_channels > 3:
                    mean_rgb = old.weight.mean(dim=1, keepdim=True)
                    m.conv1.weight[:, 3:in_channels] = mean_rgb.repeat(1, in_channels - 3, 1, 1)
        
        backbone_dim = m.fc.in_features
        m.fc = nn.Identity()
        backbone = m
        if verbose:
            print(f"[BACKBONE] {backbone_type} backbone loaded, output dim: {backbone_dim}")
    
    # Embedding head with dropout
    head = nn.Sequential(
        nn.BatchNorm1d(backbone_dim),
        nn.Dropout(dropout),
        nn.Linear(backbone_dim, embed_dim, bias=False),
        nn.BatchNorm1d(embed_dim),
    )
    
    net = nn.Sequential(backbone, head)
    return net, embed_dim


# ==============================================================================
# MODEL COMPONENTS
# ==============================================================================

class LabelSmoothingCrossEntropy(nn.Module):
    """Cross entropy with label smoothing."""
    
    def __init__(self, smoothing: float = 0.1, weight: torch.Tensor = None):
        super().__init__()
        self.smoothing = smoothing
        self.register_buffer("weight", weight)
    
    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        n_classes = pred.size(-1)
        log_preds = F.log_softmax(pred, dim=-1)
        
        with torch.no_grad():
            true_dist = torch.zeros_like(pred)
            true_dist.fill_(self.smoothing / (n_classes - 1))
            true_dist.scatter_(1, target.unsqueeze(1), 1.0 - self.smoothing)
        
        loss = (-true_dist * log_preds).sum(dim=-1)
        
        if self.weight is not None:
            loss = loss * self.weight[target]
        
        return loss.mean()


class FuzzyArcMarginProduct(nn.Module):
    """Fuzzy Arc Margin Product for angular margin loss."""
    
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.10):
        super().__init__()
        self.s = float(s)
        self.m = float(m)
        self.tau = float(tau)
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # Store input dtype for fp16 compatibility
        input_dtype = features.dtype
        
        x = F.normalize(features, dim=1)
        W = F.normalize(self.weight, dim=1)
        cos = (x @ W.t()).clamp(-1, 1)
        
        idx = torch.arange(x.size(0), device=x.device)
        cos_y = cos[idx, labels]
        
        # Fuzzy membership
        mu = torch.where(
            torch.abs(cos_y) >= self.tau,
            torch.abs(cos_y),
            torch.ones_like(cos_y)
        )
        m_eff = self.m * mu
        
        # Angular margin
        cos_m = torch.cos(m_eff)
        sin_m = torch.sin(m_eff)
        sin_t = torch.sqrt((1 - cos_y ** 2).clamp(0, 1))
        cos_theta_m = cos_y * cos_m - sin_t * sin_m
        
        logits = cos * self.s
        # Cast to same dtype as logits for fp16 compatibility
        logits[idx, labels] = (cos_theta_m * self.s).to(logits.dtype)
        
        return logits


class FocalLoss(nn.Module):
    """Focal Loss for handling hard examples."""
    
    def __init__(self, alpha: float = 1.0, gamma: float = 2.0, reduction: str = 'mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction
    
    def forward(self, inputs: torch.Tensor, targets: torch.Tensor):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        return focal_loss


class FuzzyArcLoss(nn.Module):
    """Complete FuzzyArcLoss module with optional focal loss component."""
    
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.10,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0):
        super().__init__()
        self.head = FuzzyArcMarginProduct(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(alpha=1.0, gamma=focal_gamma)
    
    def forward(self, feats: torch.Tensor, labels: torch.Tensor):
        logits = self.head(feats, labels)
        ce_loss = self.ce(logits, labels)
        
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            # Combine CE with focal (focal helps with hard examples)
            loss = 0.7 * ce_loss + 0.3 * focal_loss
        else:
            loss = ce_loss
        
        return loss, logits


# ==============================================================================
# LEARNING RATE SCHEDULE
# ==============================================================================

def get_cosine_schedule_with_warmup(optimizer, warmup_epochs: int, total_epochs: int,
                                    min_lr_ratio: float = 0.01):
    """Cosine annealing with linear warmup."""
    
    def lr_lambda(epoch):
        if epoch < warmup_epochs:
            return float(epoch) / float(max(1, warmup_epochs))
        progress = float(epoch - warmup_epochs) / float(max(1, total_epochs - warmup_epochs))
        return max(min_lr_ratio, 0.5 * (1.0 + math.cos(math.pi * progress)))
    
    return torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)


# ==============================================================================
# TEST-TIME AUGMENTATION
# ==============================================================================

def apply_tta(model, loss_head, x, device, n_augmentations=7):
    """Apply test-time augmentation and average predictions."""
    
    all_probs = []
    
    # Original
    with torch.no_grad():
        feats = model(x)
        W = F.normalize(loss_head.head.weight, dim=1)
        feats_norm = F.normalize(feats, dim=1)
        logits = (feats_norm @ W.t()) * loss_head.head.s
        probs = F.softmax(logits, dim=-1)
        all_probs.append(probs)
    
    # Augmented versions (up to 7 total including original)
    augmentations = [
        lambda t: torch.flip(t, dims=[-1]),           # 1. Horizontal flip
        lambda t: torch.flip(t, dims=[-2]),           # 2. Vertical flip
        lambda t: torch.flip(t, dims=[-1, -2]),       # 3. Both flips
        lambda t: torch.rot90(t, k=1, dims=[-2, -1]), # 4. 90° rotation
        lambda t: torch.rot90(t, k=2, dims=[-2, -1]), # 5. 180° rotation
        lambda t: torch.rot90(t, k=3, dims=[-2, -1]), # 6. 270° rotation
    ]
    
    for aug_fn in augmentations[:n_augmentations - 1]:
        with torch.no_grad():
            x_aug = aug_fn(x)
            feats = model(x_aug)
            feats_norm = F.normalize(feats, dim=1)
            logits = (feats_norm @ W.t()) * loss_head.head.s
            probs = F.softmax(logits, dim=-1)
            all_probs.append(probs)
    
    # Average
    avg_probs = torch.stack(all_probs).mean(dim=0)
    return avg_probs


# ==============================================================================
# MAIN TRAINING FUNCTION
# ==============================================================================

def training_function():
    """Main training function with pathology backbones and advanced augmentation."""
    
    accelerator = Accelerator(
        mixed_precision=config.MIXED_PRECISION,
        gradient_accumulation_steps=config.GRAD_ACCUM_STEPS
    )

    set_seed(config.SEED)
    if accelerator.device.type == "cuda":
        torch.cuda.manual_seed_all(config.SEED)
    
    if accelerator.is_main_process:
        ensure_dir(config.OUT_DIR)
    
    accelerator.print("=" * 80)
    accelerator.print("SLIMA IMPROVED TRAINING - PATHOLOGY BACKBONE + ADVANCED AUGMENTATION")
    accelerator.print("=" * 80)
    accelerator.print(f"Running on {accelerator.state.num_processes} GPUs")
    accelerator.print(f"Mixed precision: {accelerator.mixed_precision}")
    accelerator.print(f"Backbone: {config.BACKBONE}")
    accelerator.print(f"Freeze layers: {getattr(config, 'FREEZE_BACKBONE_LAYERS', 0)}")
    accelerator.print(f"CutMix: {config.USE_CUTMIX}, MixUp: {config.USE_MIXUP}, Stain Aug: {config.USE_STAIN_AUG}")
    accelerator.print(f"Epochs: {config.EPOCHS}, LR: {config.LR}, LR_backbone: {config.LR_BACKBONE}")
    
    # ==== 1. Load and pair data ====
    accelerator.print(f"\n[1/7] Loading data...")
    
    # Only main process does initial data loading/printing
    if accelerator.is_main_process:
        df = pair_images_with_masks(config.IMAGE_DIR, config.MASK_DIR)
        if df.empty:
            raise RuntimeError("No image-mask pairs found!")
    accelerator.wait_for_everyone()
    
    # All processes load data (but prints only happen once above)
    if not accelerator.is_main_process:
        # Suppress prints on non-main processes
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        df = pair_images_with_masks(config.IMAGE_DIR, config.MASK_DIR)
        sys.stdout = old_stdout
    
    # ==== 2. Map labels ====
    label_map, label_col = read_labels_from_xls(config.XLS_PATH)
    df[label_col] = df["base"].map(label_map)
    miss = df[label_col].isna()
    if miss.any():
        df.loc[miss, label_col] = df.loc[miss, "base_norm"].map(label_map)
    df = df[~df[label_col].isna()].copy()
    accelerator.print(f"[LABELS] after XLS join: {len(df)} rows")
    
    # ==== 3. Filter classes ====
    inc = {p.strip().lower() for p in config.INCLUDE_PATTERNS.split(",") if p.strip()}
    df[label_col] = df[label_col].astype(str)
    df = df[df[label_col].str.lower().isin(inc)].copy()
    accelerator.print(f"[FILTER] kept={len(df)} over classes={sorted(list(inc))}")
    
    if df.empty:
        raise RuntimeError("Dataset empty after filtering!")
    
    # ==== 4. Label mappings ====
    classes = sorted(df[label_col].unique().tolist())
    label2id = {c: i for i, c in enumerate(classes)}
    id2label = {v: k for k, v in label2id.items()}
    n_classes = len(classes)
    
    if accelerator.is_main_process:
        print(f"[CLASSES] {label2id}")
    
    # ==== 5. Train/Val/Test split ====
    accelerator.print(f"\n[2/7] Splitting data (train/val/test)...")
    
    train_val_df, test_df = train_test_split(
        df, test_size=config.TEST_SIZE,
        random_state=config.SEED, stratify=df[label_col]
    )
    
    adjusted_val_size = config.VAL_SIZE / (1 - config.TEST_SIZE)
    train_df, val_df = train_test_split(
        train_val_df, test_size=adjusted_val_size,
        random_state=config.SEED, stratify=train_val_df[label_col]
    )
    
    accelerator.print(f"  Train: {len(train_df)} samples")
    accelerator.print(f"  Val:   {len(val_df)} samples")
    accelerator.print(f"  Test:  {len(test_df)} samples")
    
    # Class distribution
    if accelerator.is_main_process:
        print("\nClass distribution:")
        for split_name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
            counts = Counter(split_df[label_col])
            print(f"  {split_name}: {dict(counts)}")
    
    # ==== 6. Compute class weights ====
    counts = Counter(train_df[label_col])
    ce_weights = torch.tensor(
        [1.0 / counts[id2label[i]] for i in range(n_classes)],
        dtype=torch.float32
    )
    ce_weights = ce_weights / ce_weights.sum() * n_classes
    
    # ==== 7. Create datasets ====
    accelerator.print(f"\n[3/7] Creating datasets...")
    in_ch = 4 if config.USE_MASK_AS_CHANNEL else 3
    
    train_ds = HistMaskDatasetAdvanced(
        train_df, label_col, label2id, config.IMG_SIZE,
        aug=True, use_mask_as_channel=config.USE_MASK_AS_CHANNEL,
        use_roi_crop=config.USE_ROI_CROP, roi_padding=config.ROI_PADDING,
        mask_thresh=config.MASK_THRESH, strong_aug=True,
        use_stain_aug=config.USE_STAIN_AUG, backbone_type=config.BACKBONE
    )
    
    val_ds = HistMaskDatasetAdvanced(
        val_df, label_col, label2id, config.IMG_SIZE,
        aug=False, use_mask_as_channel=config.USE_MASK_AS_CHANNEL,
        use_roi_crop=config.USE_ROI_CROP, roi_padding=config.ROI_PADDING,
        mask_thresh=config.MASK_THRESH, strong_aug=False,
        use_stain_aug=False, backbone_type=config.BACKBONE
    )
    
    test_ds = HistMaskDatasetAdvanced(
        test_df, label_col, label2id, config.IMG_SIZE,
        aug=False, use_mask_as_channel=config.USE_MASK_AS_CHANNEL,
        use_roi_crop=config.USE_ROI_CROP, roi_padding=config.ROI_PADDING,
        mask_thresh=config.MASK_THRESH, strong_aug=False,
        use_stain_aug=False, backbone_type=config.BACKBONE
    )
    
    # Class-weighted sampling for imbalanced data
    if config.USE_WEIGHTED_SAMPLER:
        train_labels = [label2id[str(r[label_col])] for _, r in train_df.iterrows()]
        class_counts = Counter(train_labels)
        
        # Get class IDs and boost values
        class_boosts = {
            'solid': getattr(config, 'SOLID_CLASS_BOOST', 1.0),
            'lepidic': getattr(config, 'LEPIDIC_CLASS_BOOST', 1.0),
            'acinar': getattr(config, 'ACINAR_CLASS_BOOST', 1.0),
        }
        
        # Map class names to IDs
        class_id_boosts = {}
        for class_name, boost in class_boosts.items():
            class_id = label2id.get(class_name, -1)
            if class_id >= 0 and boost > 1.0:
                class_id_boosts[class_id] = boost
                accelerator.print(f"[SAMPLER] {class_name} class (id={class_id}) boosted by {boost}x")
        
        # Create weights with class-specific boosts
        weights = []
        for l in train_labels:
            w = 1.0 / class_counts[l]
            if l in class_id_boosts:
                w *= class_id_boosts[l]
            weights.append(w)
        
        sampler = WeightedRandomSampler(weights, len(weights), replacement=True)
        
        train_ld = DataLoader(
            train_ds,
            batch_size=config.BATCH_SIZE,
            sampler=sampler,
            num_workers=config.NUM_WORKERS,
            pin_memory=config.PIN_MEMORY,
            persistent_workers=False,
            drop_last=True
        )
    else:
        train_ld = DataLoader(
            train_ds,
            batch_size=config.BATCH_SIZE,
            shuffle=True,
            num_workers=config.NUM_WORKERS,
            pin_memory=config.PIN_MEMORY,
            persistent_workers=False,
            drop_last=True
        )
    
    val_ld = DataLoader(
        val_ds, batch_size=config.BATCH_SIZE, shuffle=False,
        num_workers=config.NUM_WORKERS, pin_memory=config.PIN_MEMORY,
        persistent_workers=False
    )
    test_ld = DataLoader(
        test_ds, batch_size=config.BATCH_SIZE, shuffle=False,
        num_workers=config.NUM_WORKERS, pin_memory=config.PIN_MEMORY,
        persistent_workers=False
    )
    
    # ==== 8. Build model ====
    accelerator.print(f"\n[4/7] Building model...")
    
    # Only main process builds model first (downloads weights if needed)
    # Others wait to avoid multiple simultaneous downloads
    if accelerator.is_main_process:
        model, _ = build_backbone_pathology(
            backbone_type=config.BACKBONE,
            pretrained=True,
            embed_dim=config.EMBED_DIM,
            in_channels=in_ch,
            dropout=config.DROPOUT,
            uni_checkpoint=config.UNI_CHECKPOINT,
            ctranspath_checkpoint=config.CTRANSPATH_CHECKPOINT,
            freeze_backbone_layers=getattr(config, 'FREEZE_BACKBONE_LAYERS', 0),
            img_size=config.IMG_SIZE,
            ensemble_weights=getattr(config, 'ENSEMBLE_WEIGHTS', None),
            verbose=True,
        )
    accelerator.wait_for_everyone()
    
    # Now other processes build (weights already cached, no prints)
    if not accelerator.is_main_process:
        model, _ = build_backbone_pathology(
            backbone_type=config.BACKBONE,
            pretrained=True,
            embed_dim=config.EMBED_DIM,
            in_channels=in_ch,
            dropout=config.DROPOUT,
            uni_checkpoint=config.UNI_CHECKPOINT,
            ctranspath_checkpoint=config.CTRANSPATH_CHECKPOINT,
            freeze_backbone_layers=getattr(config, 'FREEZE_BACKBONE_LAYERS', 0),
            img_size=config.IMG_SIZE,
            ensemble_weights=getattr(config, 'ENSEMBLE_WEIGHTS', None),
            verbose=False,
        )
    
    loss_head = FuzzyArcLoss(
        config.EMBED_DIM, n_classes,
        s=config.S_SCALE, m=config.M_MARGIN, tau=config.TAU,
        label_smoothing=config.LABEL_SMOOTHING,
        ce_weight=ce_weights.to(accelerator.device),
        use_focal=getattr(config, 'USE_FOCAL_LOSS', True),
        focal_gamma=getattr(config, 'FOCAL_GAMMA', 2.0)
    )
    
    if getattr(config, 'USE_FOCAL_LOSS', True):
        accelerator.print(f"[LOSS] Using Focal Loss (gamma={getattr(config, 'FOCAL_GAMMA', 2.0)})")
    
    # ==== 9. Optimizer with differential LR ====
    backbone_params = list(model[0].parameters())
    head_params = list(model[1].parameters()) + list(loss_head.parameters())
    
    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": config.LR_BACKBONE},
        {"params": head_params, "lr": config.LR},
    ], weight_decay=config.WEIGHT_DECAY)
    
    scheduler = get_cosine_schedule_with_warmup(
        optimizer, config.WARMUP_EPOCHS, config.EPOCHS
    )
    
    # ==== 10. Prepare for distributed ====
    model, loss_head, optimizer, train_ld, val_ld, test_ld = accelerator.prepare(
        model, loss_head, optimizer, train_ld, val_ld, test_ld
    )
    
    # ==== 11. Training loop ====
    accelerator.print(f"\n[5/7] Starting training for {config.EPOCHS} epochs...")
    
    best_metric = -1.0
    best_epoch = 0
    best_path = os.path.join(config.OUT_DIR, "best_model_pathology.pth")
    history = {"train_loss": [], "val_loss": [], "val_acc": [], "val_f1": [], "lr": []}
    
    # Simple CE for CutMix/MixUp
    ce_criterion = nn.CrossEntropyLoss(weight=ce_weights.to(accelerator.device))
    
    for epoch in range(1, config.EPOCHS + 1):
        t0 = time.time()
        
        # ---- Training ----
        model.train()
        loss_head.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for x, y, _ in train_ld:
            with accelerator.accumulate(model):
                # Apply CutMix or MixUp
                use_cutmix = config.USE_CUTMIX and random.random() < config.CUTMIX_PROB
                use_mixup = config.USE_MIXUP and random.random() < config.MIXUP_PROB and not use_cutmix
                
                # Get unwrapped loss_head for accessing .head attribute (DDP wraps modules)
                unwrapped_loss_head = accelerator.unwrap_model(loss_head)
                
                if use_cutmix:
                    x, y_a, y_b, lam = cutmix_data(x, y, alpha=config.CUTMIX_ALPHA)
                    feats = model(x)
                    logits = unwrapped_loss_head.head(feats, y_a)  # Use y_a for margin
                    loss = mixup_criterion(ce_criterion, logits, y_a, y_b, lam)
                elif use_mixup:
                    x, y_a, y_b, lam = mixup_data(x, y, alpha=config.MIXUP_ALPHA)
                    feats = model(x)
                    logits = unwrapped_loss_head.head(feats, y_a)
                    loss = mixup_criterion(ce_criterion, logits, y_a, y_b, lam)
                else:
                    feats = model(x)
                    loss, logits = loss_head(feats, y)
                
                accelerator.backward(loss)
                
                # Note: Gradient clipping disabled for fp16 compatibility
                # AdamW with weight_decay provides sufficient regularization
                
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
            
            train_loss += loss.detach().float() * x.size(0)
            
            # For accuracy calculation, use original labels if no mixing
            if not use_cutmix and not use_mixup:
                pred = torch.argmax(logits.detach(), dim=1)
                train_correct += (pred == y).sum().item()
            train_total += x.size(0)
        
        train_loss = train_loss.item() / train_total
        train_acc = train_correct / train_total if train_total > 0 else 0
        
        # ---- Validation ----
        model.eval()
        loss_head.eval()
        val_loss = 0.0
        val_preds, val_labels = [], []
        
        with torch.no_grad():
            for x, y, _ in val_ld:
                feats = model(x)
                loss, logits = loss_head(feats, y)
                val_loss += loss.detach().float() * x.size(0)
                pred = torch.argmax(logits, dim=1)
                val_preds.append(accelerator.gather(pred).cpu())
                val_labels.append(accelerator.gather(y).cpu())
        
        val_preds = torch.cat(val_preds).numpy()
        val_labels = torch.cat(val_labels).numpy()
        val_acc = accuracy_score(val_labels, val_preds)
        val_f1 = f1_score(val_labels, val_preds, average="macro")
        val_precision = precision_score(val_labels, val_preds, average="macro", zero_division=0)
        val_recall = recall_score(val_labels, val_preds, average="macro", zero_division=0)
        val_loss = val_loss.item() / len(val_ds)
        
        val_metric = (val_precision + val_recall) / 2
        
        # Update scheduler
        scheduler.step()
        current_lr = optimizer.param_groups[0]["lr"]
        
        # Log
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        history["val_f1"].append(val_f1)
        history["lr"].append(current_lr)
        
        accelerator.print(
            f"[{epoch:03d}/{config.EPOCHS}] "
            f"tr_loss={train_loss:.4f} tr_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} val_f1={val_f1:.4f} | "
            f"P={val_precision:.4f} R={val_recall:.4f} avg={val_metric:.4f} | "
            f"lr={current_lr:.2e} | {time.time()-t0:.1f}s"
        )
        
        # Save best model
        if accelerator.is_main_process and val_metric > best_metric:
            best_metric = val_metric
            best_epoch = epoch
            state = {
                "epoch": epoch,
                "model_state": accelerator.unwrap_model(model).state_dict(),
                "head_state": accelerator.unwrap_model(loss_head).state_dict(),
                "optimizer_state": optimizer.state_dict(),
                "scheduler_state": scheduler.state_dict(),
                "label2id": label2id,
                "id2label": id2label,
                "best_metric": best_metric,
                "config": {k: v for k, v in config.__dict__.items() if not k.startswith('_')},
                "history": history,
            }
            torch.save(state, best_path)
            accelerator.print(f"  --> Saved best model (avg_P_R={best_metric:.4f})")
    
    accelerator.print(f"\n[6/7] Training complete! Best epoch: {best_epoch} with metric: {best_metric:.4f}")
    
    # ==== 12. Final Test Evaluation ====
    accelerator.print(f"\n[7/7] Evaluating on TEST set...")
    
    # Load best model
    if accelerator.is_main_process and os.path.exists(best_path):
        checkpoint = torch.load(best_path, map_location=accelerator.device, weights_only=False)
        accelerator.unwrap_model(model).load_state_dict(checkpoint["model_state"])
        accelerator.unwrap_model(loss_head).load_state_dict(checkpoint["head_state"])
    accelerator.wait_for_everyone()
    
    model.eval()
    loss_head.eval()
    test_preds, test_labels, test_probs = [], [], []
    
    with torch.no_grad():
        for x, y, _ in test_ld:
            if config.USE_TTA:
                probs = apply_tta(
                    model, accelerator.unwrap_model(loss_head),
                    x, accelerator.device, n_augmentations=config.TTA_AUGMENTATIONS
                )
                pred = probs.argmax(dim=1)
            else:
                feats = model(x)
                _, logits = loss_head(feats, y)
                pred = torch.argmax(logits, dim=1)
                probs = F.softmax(logits, dim=-1)
            
            test_preds.append(accelerator.gather(pred).cpu())
            test_labels.append(accelerator.gather(y).cpu())
            test_probs.append(accelerator.gather(probs).cpu())
    
    test_preds = torch.cat(test_preds).numpy()
    test_labels = torch.cat(test_labels).numpy()
    
    # Final metrics
    test_acc = accuracy_score(test_labels, test_preds)
    test_f1 = f1_score(test_labels, test_preds, average="macro")
    test_precision = precision_score(test_labels, test_preds, average="macro", zero_division=0)
    test_recall = recall_score(test_labels, test_preds, average="macro", zero_division=0)
    
    accelerator.print("\n" + "=" * 80)
    accelerator.print("FINAL TEST RESULTS")
    accelerator.print("=" * 80)
    accelerator.print(f"  Backbone:  {config.BACKBONE}")
    accelerator.print(f"  Accuracy:  {test_acc*100:.2f}%")
    accelerator.print(f"  F1-Score:  {test_f1*100:.2f}%")
    accelerator.print(f"  Precision: {test_precision*100:.2f}%")
    accelerator.print(f"  Recall:    {test_recall*100:.2f}%")
    accelerator.print(f"  Avg(P,R):  {(test_precision+test_recall)/2*100:.2f}%")
    
    if accelerator.is_main_process:
        print("\n=== Test Classification Report ===")
        print(classification_report(
            test_labels, test_preds,
            target_names=[id2label[i] for i in range(n_classes)]
        ))
        
        # Save final results
        results = {
            "backbone": config.BACKBONE,
            "test_accuracy": float(test_acc),
            "test_f1": float(test_f1),
            "test_precision": float(test_precision),
            "test_recall": float(test_recall),
            "best_epoch": best_epoch,
            "best_val_metric": float(best_metric),
            "history": history,
            "improvements": {
                "pathology_backbone": config.BACKBONE,
                "cutmix": config.USE_CUTMIX,
                "mixup": config.USE_MIXUP,
                "stain_augmentation": config.USE_STAIN_AUG,
                "weighted_sampling": config.USE_WEIGHTED_SAMPLER,
            }
        }
        
        with open(os.path.join(config.OUT_DIR, "results_pathology.json"), "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to {config.OUT_DIR}")
    
    # Cleanup distributed process group
    accelerator.wait_for_everyone()
    if torch.distributed.is_initialized():
        torch.distributed.destroy_process_group()
    
    return test_acc, test_f1


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

def main():
    """Entry point for accelerate launch."""
    training_function()


if __name__ == "__main__":
    main()
