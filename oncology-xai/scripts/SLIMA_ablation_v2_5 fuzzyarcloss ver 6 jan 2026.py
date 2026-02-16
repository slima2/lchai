#!/usr/bin/env python3
"""
FuzzyArcLoss V2.5: Best of V2 + V3
==================================

Combines:
- V2's inverse cosine uncertainty (confident → full margin) - PROVEN BETTER
- V3's sub-centers (K prototypes per class) - +6% GAIN
- Fixed loss scaling
- Class-specific parameters

Key insight from ablation:
- Entropy-based uncertainty UNDERPERFORMED cosine-based (55.9% vs 61.9%)
- Sub-centers gave +6% improvement
- So: Keep V2 uncertainty + Add V3 sub-centers

Author: Servio F. Lima
"""

import os
import sys
import math
import json
import random
import warnings
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime

import numpy as np
import pandas as pd
from PIL import Image
from scipy.io import loadmat
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import torchvision.transforms as T

try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False

warnings.filterwarnings("ignore")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class Config:
    ROOT_DIR: str = "/home/rapids/notebooks/slima/Zenodo_Anorak_original"
    XLS_PATH: str = "/home/rapids/notebooks/slima/overlay_index ver 9 nov 2025.xlsx"
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/ablation_v2_5"
    CTRANSPATH_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/ctranspath.pth"
    
    EMBED_DIM: int = 512
    FREEZE_BACKBONE_LAYERS: int = 2
    
    EPOCHS: int = 175
    BATCH_SIZE: int = 64
    LR: float = 2e-4
    LR_BACKBONE: float = 1e-5
    WEIGHT_DECAY: float = 5e-5
    
    IMG_SIZE: int = 224
    USE_ROI_CROP: bool = True
    ROI_PADDING: int = 24
    MASK_THRESH: float = 0.5
    
    SEED: int = 42
    NUM_WORKERS: int = 0  # Avoid shm issues
    USE_DATAPARALLEL: bool = True
    
    # Print frequency
    PRINT_FREQ: int = 10  # Print every 10 epochs
    
    @property
    def IMAGE_DIR(self):
        return f"{self.ROOT_DIR}/image"
    
    @property
    def MASK_DIR(self):
        return f"{self.ROOT_DIR}/mask"


config = Config()


# ==============================================================================
# LOSS COMPONENTS
# ==============================================================================

class LabelSmoothingCE(nn.Module):
    def __init__(self, smoothing: float = 0.1):
        super().__init__()
        self.smoothing = smoothing
    
    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        n = pred.size(1)
        smooth = torch.full_like(pred, self.smoothing / (n - 1))
        smooth.scatter_(1, target.unsqueeze(1), 1 - self.smoothing)
        return -(smooth * F.log_softmax(pred, dim=1)).sum(dim=1).mean()


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0):
        super().__init__()
        self.gamma = gamma
    
    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce)
        return (((1 - pt) ** self.gamma) * ce).mean()


# ==============================================================================
# BASELINE LOSSES
# ==============================================================================

class SoftmaxLoss(nn.Module):
    """Standard softmax baseline"""
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.fc = nn.Linear(in_features, out_features)
        self.weight = self.fc.weight
        self.s = 1.0
    
    def forward(self, features, labels):
        logits = self.fc(features)
        return F.cross_entropy(logits, labels), logits
    
    def get_weight_for_eval(self):
        return self.weight


class ArcFaceLoss(nn.Module):
    """Standard ArcFace"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.5):
        super().__init__()
        self.s, self.m = s, m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.cos_m, self.sin_m = math.cos(m), math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
    
    def forward(self, features, labels):
        f_norm = F.normalize(features, dim=1)
        w_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(f_norm, w_norm).clamp(-1+1e-7, 1-1e-7)
        sine = torch.sqrt(1 - cosine**2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = self.s * (one_hot * phi + (1 - one_hot) * cosine)
        return F.cross_entropy(output, labels), output
    
    def get_weight_for_eval(self):
        return self.weight


# ==============================================================================
# FUZZYARCLOSS V1 (Original: uncertain → full margin)
# ==============================================================================

class FuzzyArcLossV1(nn.Module):
    """V1: uncertain samples get full margin (original paper)"""
    def __init__(self, in_features: int, out_features: int, s=30.0, m=0.5, tau=0.5):
        super().__init__()
        self.s, self.m, self.tau = s, m, tau
        self.out_features = out_features
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.cos_m, self.sin_m = math.cos(m), math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        self.ce = LabelSmoothingCE(0.05)
        self.focal = FocalLoss(2.0)
    
    def forward(self, features, labels):
        B = features.size(0)
        f_norm = F.normalize(features, dim=1)
        w_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(f_norm, w_norm).clamp(-1+1e-7, 1-1e-7)
        sine = torch.sqrt(1 - cosine**2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        target_cos = cosine[torch.arange(B, device=features.device), labels]
        # V1: uncertain (|cos| < tau) → μ=1 (full margin)
        #     confident (|cos| >= tau) → μ=|cos| (reduced margin)
        mu = torch.where(target_cos.abs() >= self.tau, 
                         target_cos.abs(), 
                         torch.ones_like(target_cos)).clamp(0, 1)
        
        one_hot = F.one_hot(labels, self.out_features).float()
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        output = self.s * (one_hot * target_logits + (1 - one_hot) * cosine)
        
        return 0.7 * self.ce(output, labels) + 0.3 * self.focal(output, labels), output
    
    def get_weight_for_eval(self):
        return self.weight


# ==============================================================================
# FUZZYARCLOSS V2 (Inverse: confident → full margin)
# ==============================================================================

class FuzzyArcLossV2(nn.Module):
    """V2: confident samples get full margin (inverse - histopathology optimized)"""
    def __init__(self, in_features: int, out_features: int, s=30.0, m=0.5, tau=0.5,
                 class_tau=None, class_margin=None, class_scale=None):
        super().__init__()
        self.s, self.m, self.tau = s, m, tau
        self.out_features = out_features
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Class-specific parameters
        self.register_buffer('class_tau', 
            class_tau if class_tau is not None else torch.full((out_features,), tau))
        self.register_buffer('class_margin', 
            class_margin if class_margin is not None else torch.full((out_features,), m))
        self.register_buffer('class_scale', 
            class_scale if class_scale is not None else torch.full((out_features,), s))
        
        self.ce = LabelSmoothingCE(0.1)
        self.focal = FocalLoss(2.0)
    
    def forward(self, features, labels):
        B = features.size(0)
        device = features.device
        f_norm = F.normalize(features, dim=1)
        w_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(f_norm, w_norm).clamp(-1+1e-7, 1-1e-7)
        sine = torch.sqrt(1 - cosine**2 + 1e-7)
        
        target_cos = cosine[torch.arange(B, device=device), labels]
        tau = self.class_tau[labels]
        
        # V2 INVERSE: confident (|cos| >= tau) → HIGH μ (full margin)
        #             uncertain (|cos| < tau) → LOW μ (reduced margin)
        mu = torch.where(target_cos.abs() >= tau, 
                         0.8 + 0.2 * target_cos.abs(),  # Confident: 0.8-1.0
                         0.3 + 0.4 * target_cos.abs()   # Uncertain: 0.3-0.7
                        ).clamp(0.1, 1.0)
        
        # Compute phi with class-specific margins
        margins = self.class_margin[labels]
        phi = cosine.clone()
        for i in range(B):
            m_i = margins[i].item()
            cos_m, sin_m = math.cos(m_i), math.sin(m_i)
            c = labels[i].item()
            cos_theta_m = cosine[i, c] * cos_m - sine[i, c] * sin_m
            th = math.cos(math.pi - m_i)
            mm = math.sin(math.pi - m_i) * m_i
            phi[i, c] = cos_theta_m if cosine[i, c].item() > th else cosine[i, c] - mm
        
        one_hot = F.one_hot(labels, self.out_features).float()
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        # Scale ONCE at the end (fixed from V3)
        scales = self.class_scale[labels].unsqueeze(1)
        output = output * scales
        
        return 0.6 * self.ce(output, labels) + 0.4 * self.focal(output, labels), output
    
    def get_weight_for_eval(self):
        return self.weight


# ==============================================================================
# FUZZYARCLOSS V2.5 (V2 Inverse + V3 SubCenters) - BEST COMBINATION
# ==============================================================================

class FuzzyArcLossV2_5(nn.Module):
    """
    V2.5: Best of both worlds
    - V2's inverse cosine uncertainty (PROVEN BETTER than entropy)
    - V3's sub-centers K prototypes per class (+6% GAIN)
    - Fixed loss scaling
    - Class-specific parameters
    
    This is the recommended loss for histopathology!
    """
    def __init__(self, in_features: int, out_features: int, 
                 K: int = 3,  # Sub-centers per class
                 s: float = 30.0, m: float = 0.5, tau: float = 0.5,
                 class_tau=None, class_margin=None, class_scale=None):
        super().__init__()
        self.s, self.m, self.tau = s, m, tau
        self.K = K
        self.out_features = out_features
        
        # Sub-center weights: (C, K, D)
        self.weight = nn.Parameter(torch.FloatTensor(out_features, K, in_features))
        nn.init.xavier_uniform_(self.weight.view(out_features * K, in_features))
        
        # Class-specific parameters
        self.register_buffer('class_tau', 
            class_tau if class_tau is not None else torch.full((out_features,), tau))
        self.register_buffer('class_margin', 
            class_margin if class_margin is not None else torch.full((out_features,), m))
        self.register_buffer('class_scale', 
            class_scale if class_scale is not None else torch.full((out_features,), s))
        
        self.ce = LabelSmoothingCE(0.1)
        self.focal = FocalLoss(2.0)
    
    def _get_cosine_subcenter(self, features):
        """Compute cosine with sub-centers, return max per class"""
        f_norm = F.normalize(features, dim=1)  # (B, D)
        w_norm = F.normalize(self.weight, dim=2)  # (C, K, D)
        
        # Cosine with all sub-centers: (B, C, K)
        cosine_all = torch.einsum('bd,ckd->bck', f_norm, w_norm)
        
        # Max over sub-centers: (B, C)
        cosine, best_k = cosine_all.max(dim=2)
        return cosine.clamp(-1+1e-7, 1-1e-7), best_k
    
    def forward(self, features, labels):
        B = features.size(0)
        device = features.device
        
        # 1. Get cosine similarity (max over K sub-centers)
        cosine, best_k = self._get_cosine_subcenter(features)
        sine = torch.sqrt(1 - cosine**2 + 1e-7)
        
        # 2. Get target cosine
        target_cos = cosine[torch.arange(B, device=device), labels]
        tau = self.class_tau[labels]
        
        # 3. V2 INVERSE uncertainty (NOT entropy!)
        mu = torch.where(target_cos.abs() >= tau, 
                         0.8 + 0.2 * target_cos.abs(),
                         0.3 + 0.4 * target_cos.abs()
                        ).clamp(0.1, 1.0)
        
        # 4. Compute phi with class-specific margins
        margins = self.class_margin[labels]
        phi = cosine.clone()
        for i in range(B):
            m_i = margins[i].item()
            cos_m, sin_m = math.cos(m_i), math.sin(m_i)
            c = labels[i].item()
            cos_theta_m = cosine[i, c] * cos_m - sine[i, c] * sin_m
            th = math.cos(math.pi - m_i)
            mm = math.sin(math.pi - m_i) * m_i
            phi[i, c] = cos_theta_m if cosine[i, c].item() > th else cosine[i, c] - mm
        
        # 5. Apply fuzzy margin
        one_hot = F.one_hot(labels, self.out_features).float()
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        # 6. Scale ONCE
        scales = self.class_scale[labels].unsqueeze(1)
        output = output * scales
        
        # 7. Combined loss
        loss = 0.6 * self.ce(output, labels) + 0.4 * self.focal(output, labels)
        
        return loss, output
    
    def get_weight_for_eval(self):
        """Return mean of sub-centers for evaluation"""
        return self.weight.mean(dim=1)  # (C, D)


# ==============================================================================
# CLASS PARAMETERS FOR LUNG ADENOCARCINOMA
# ==============================================================================

def get_class_params(num_classes=6):
    """
    Optimized parameters based on per-class difficulty
    
    Hard classes (acinar, micropapillary): gentle (low tau, low margin)
    Easy classes (papillary, solid): aggressive (high tau, high margin)
    """
    return {
        'class_tau': torch.tensor([0.35, 0.45, 0.35, 0.50, 0.60, 0.65])[:num_classes],
        'class_margin': torch.tensor([0.35, 0.45, 0.35, 0.50, 0.55, 0.60])[:num_classes],
        'class_scale': torch.tensor([25.0, 28.0, 25.0, 30.0, 32.0, 35.0])[:num_classes],
    }


# ==============================================================================
# BACKBONE (CTransPath)
# ==============================================================================

class ConvStem(nn.Module):
    def __init__(self, embed_dim=96):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Conv2d(3, embed_dim//8, 3, 2, 1, bias=False), nn.BatchNorm2d(embed_dim//8), nn.GELU(),
            nn.Conv2d(embed_dim//8, embed_dim//4, 3, 2, 1, bias=False), nn.BatchNorm2d(embed_dim//4), nn.GELU(),
            nn.Conv2d(embed_dim//4, embed_dim, 1, 1, 0, bias=False), nn.BatchNorm2d(embed_dim),
        )
        self.norm = nn.LayerNorm(embed_dim)
    
    def forward(self, x):
        x = self.proj(x).permute(0, 2, 3, 1)
        return self.norm(x)


class CTransPathBackbone(nn.Module):
    def __init__(self, ckpt_path, freeze_layers=2):
        super().__init__()
        if HAS_TIMM:
            self.model = timm.create_model('swin_tiny_patch4_window7_224', 
                                           pretrained=False, num_classes=0, global_pool='avg')
            self.model.patch_embed = ConvStem(96)
            self.out_features = 768
            if os.path.exists(ckpt_path):
                sd = torch.load(ckpt_path, map_location='cpu')
                sd = sd.get('model', sd)
                ms = self.model.state_dict()
                self.model.load_state_dict(
                    {k: v for k, v in sd.items() if k in ms and v.shape == ms[k].shape}, 
                    strict=False
                )
                print("  ✓ Loaded CTransPath")
        else:
            from torchvision import models
            self.model = models.resnet50(pretrained=True)
            self.model.fc = nn.Identity()
            self.out_features = 2048
            print("  ✓ Using ResNet50 fallback")
        
        if freeze_layers > 0 and HAS_TIMM:
            for n, p in self.model.named_parameters():
                if any(f'layers.{i}' in n for i in range(freeze_layers)):
                    p.requires_grad = False
    
    def forward(self, x):
        return self.model(x)


# ==============================================================================
# DATASET
# ==============================================================================

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
MAT_EXCLUDE = {"__header__", "__version__", "__globals__"}


def pair_images_masks(img_dir, mask_dir):
    records = []
    for f in os.listdir(img_dir):
        stem, ext = os.path.splitext(f)
        if ext.lower() not in IMG_EXTS:
            continue
        for mext in ['.mat', '.png', '.jpg', '.tif']:
            mp = os.path.join(mask_dir, stem + mext)
            if os.path.exists(mp):
                records.append({
                    'image_path': os.path.join(img_dir, f), 
                    'mask_path': mp, 
                    'stem': stem
                })
                break
    return pd.DataFrame(records)


def load_mask(path, thresh=0.5):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.mat':
        mat = loadmat(path)
        for k in mat:
            if k not in MAT_EXCLUDE:
                arr = mat[k]
                if isinstance(arr, np.ndarray) and arr.ndim >= 2:
                    return (arr > thresh).astype(np.uint8)
    else:
        return (np.array(Image.open(path).convert('L')) / 255 > thresh).astype(np.uint8)
    return None


class HistDataset(Dataset):
    def __init__(self, df, label_col, label2id, img_size=224, aug=True, use_roi=True, pad=24):
        self.df = df.reset_index(drop=True)
        self.label_col, self.label2id = label_col, label2id
        self.use_roi, self.pad = use_roi, pad
        
        if aug:
            self.tfm = T.Compose([
                T.RandomHorizontalFlip(),
                T.RandomVerticalFlip(),
                T.RandomRotation(15),
                T.ColorJitter(0.2, 0.2, 0.1),
                T.Resize((img_size, img_size)),
                T.ToTensor(),
                T.Normalize([.485, .456, .406], [.229, .224, .225])
            ])
        else:
            self.tfm = T.Compose([
                T.Resize((img_size, img_size)),
                T.ToTensor(),
                T.Normalize([.485, .456, .406], [.229, .224, .225])
            ])
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = Image.open(row['image_path']).convert('RGB')
        
        if self.use_roi and 'mask_path' in row:
            m = load_mask(row['mask_path'])
            if m is not None:
                coords = np.argwhere(m > 0)
                if len(coords):
                    y0, x0 = coords.min(0)
                    y1, x1 = coords.max(0) + 1
                    img = img.crop((
                        max(0, x0 - self.pad),
                        max(0, y0 - self.pad),
                        min(m.shape[1], x1 + self.pad),
                        min(m.shape[0], y1 + self.pad)
                    ))
        
        return self.tfm(img), self.label2id[str(row[self.label_col])]


# ==============================================================================
# TRAINING
# ==============================================================================

def train_experiment(name, model, loss_fn, train_ld, val_ld, test_ld, id2label, device, epochs):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    sys.stdout.flush()
    
    num_gpus = torch.cuda.device_count()
    if config.USE_DATAPARALLEL and num_gpus > 1:
        print(f"  Using {num_gpus} GPUs")
        model = nn.DataParallel(model)
    
    model, loss_fn = model.to(device), loss_fn.to(device)
    base = model.module if hasattr(model, 'module') else model
    
    opt = torch.optim.AdamW([
        {'params': base[0].parameters(), 'lr': config.LR_BACKBONE},
        {'params': base[1].parameters(), 'lr': config.LR},
        {'params': loss_fn.parameters(), 'lr': config.LR},
    ], weight_decay=config.WEIGHT_DECAY)
    
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs, 1e-6)
    scaler = torch.cuda.amp.GradScaler()
    
    best_f1, best_ep, best_state = 0, 0, None
    
    for ep in range(epochs):
        # Training
        model.train()
        loss_fn.train()
        total_loss = 0
        
        for imgs, lbls in train_ld:
            imgs, lbls = imgs.to(device), lbls.to(device)
            opt.zero_grad()
            
            with torch.cuda.amp.autocast():
                feats = model(imgs)
                loss, _ = loss_fn(feats, lbls)
            
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            torch.nn.utils.clip_grad_norm_(loss_fn.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            
            total_loss += loss.item()
        
        # Validation
        model.eval()
        preds, gt = [], []
        
        with torch.no_grad():
            for imgs, lbls in val_ld:
                feats = model(imgs.to(device))
                w = loss_fn.get_weight_for_eval()
                w_norm = F.normalize(w, dim=1)
                f_norm = F.normalize(feats, dim=1)
                logits = f_norm @ w_norm.t()
                preds.extend(logits.argmax(1).cpu().numpy())
                gt.extend(lbls.numpy())
        
        val_f1 = f1_score(gt, preds, average='macro')
        
        if val_f1 > best_f1:
            best_f1, best_ep = val_f1, ep
            base = model.module if hasattr(model, 'module') else model
            best_state = {
                'model': {k: v.cpu().clone() for k, v in base.state_dict().items()},
                'loss': {k: v.cpu().clone() for k, v in loss_fn.state_dict().items()}
            }
        
        # Print progress
        if (ep + 1) % config.PRINT_FREQ == 0:
            avg_loss = total_loss / len(train_ld)
            print(f"  Ep {ep+1:3d}/{epochs} | Loss {avg_loss:.4f} | Val-F1 {val_f1:.4f} | Best {best_f1:.4f}@{best_ep+1}")
            sys.stdout.flush()
        
        sched.step()
    
    # Load best model and test
    if best_state:
        base = model.module if hasattr(model, 'module') else model
        base.load_state_dict({k: v.to(device) for k, v in best_state['model'].items()})
        loss_fn.load_state_dict({k: v.to(device) for k, v in best_state['loss'].items()})
    
    model.eval()
    preds, gt = [], []
    
    with torch.no_grad():
        for imgs, lbls in test_ld:
            feats = model(imgs.to(device))
            w = loss_fn.get_weight_for_eval()
            w_norm = F.normalize(w, dim=1)
            f_norm = F.normalize(feats, dim=1)
            logits = f_norm @ w_norm.t()
            preds.extend(logits.argmax(1).cpu().numpy())
            gt.extend(lbls.numpy())
    
    preds, gt = np.array(preds), np.array(gt)
    acc = accuracy_score(gt, preds)
    f1 = f1_score(gt, preds, average='macro')
    f1_cls = f1_score(gt, preds, average=None)
    
    print(f"\n  TEST: Acc={acc*100:.2f}% | Macro-F1={f1*100:.2f}%")
    for i, v in enumerate(f1_cls):
        print(f"    {id2label[i]}: {v*100:.1f}%")
    sys.stdout.flush()
    
    return {
        'name': name,
        'acc': acc,
        'f1': f1,
        'f1_cls': f1_cls.tolist(),
        'best_ep': best_ep + 1
    }


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("  COMPLETE ABLATION: V1 vs V2 vs V2.5 (V2+SubCenters)")
    print("=" * 60)
    sys.stdout.flush()
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPUs: {torch.cuda.device_count()} x {torch.cuda.get_device_name(0)}")
    sys.stdout.flush()
    
    # Seed
    random.seed(config.SEED)
    np.random.seed(config.SEED)
    torch.manual_seed(config.SEED)
    torch.cuda.manual_seed_all(config.SEED)
    
    # Data loading
    print("\n[1/3] Loading data...")
    sys.stdout.flush()
    
    df = pair_images_masks(config.IMAGE_DIR, config.MASK_DIR)
    xls = pd.read_excel(config.XLS_PATH)
    xls['stem'] = xls['tile_id'].astype(str)
    xls = xls[xls['pattern'].str.lower() != 'none']
    df = df.merge(xls[['stem', 'pattern']], on='stem', how='inner').dropna(subset=['pattern'])
    
    labels = sorted(df['pattern'].astype(str).unique())
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    nc = len(labels)
    
    print(f"  Samples: {len(df)}, Classes: {nc}")
    print(f"  Labels: {labels}")
    
    # Split
    train_df, temp = train_test_split(df, test_size=0.3, stratify=df['pattern'], random_state=config.SEED)
    val_df, test_df = train_test_split(temp, test_size=0.5, stratify=temp['pattern'], random_state=config.SEED)
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # Class counts
    train_lbls = [label2id[str(l)] for l in train_df['pattern']]
    cc = [train_lbls.count(i) for i in range(nc)]
    print(f"  Class counts: {dict(zip(labels, cc))}")
    sys.stdout.flush()
    
    # Datasets
    train_ds = HistDataset(train_df, 'pattern', label2id, config.IMG_SIZE, True, config.USE_ROI_CROP)
    val_ds = HistDataset(val_df, 'pattern', label2id, config.IMG_SIZE, False, config.USE_ROI_CROP)
    test_ds = HistDataset(test_df, 'pattern', label2id, config.IMG_SIZE, False, config.USE_ROI_CROP)
    
    # Weighted sampler
    sampler = WeightedRandomSampler([1.0 / cc[l] for l in train_lbls], len(train_lbls), True)
    
    train_ld = DataLoader(train_ds, config.BATCH_SIZE, sampler=sampler, 
                          num_workers=config.NUM_WORKERS, pin_memory=True)
    val_ld = DataLoader(val_ds, config.BATCH_SIZE, 
                        num_workers=config.NUM_WORKERS, pin_memory=True)
    test_ld = DataLoader(test_ds, config.BATCH_SIZE, 
                         num_workers=config.NUM_WORKERS, pin_memory=True)
    
    # Model builder
    def build_model():
        bb = CTransPathBackbone(config.CTRANSPATH_CHECKPOINT, config.FREEZE_BACKBONE_LAYERS)
        head = nn.Sequential(
            nn.Linear(bb.out_features, config.EMBED_DIM),
            nn.LayerNorm(config.EMBED_DIM),
            nn.GELU(),
            nn.Dropout(0.15)
        )
        return nn.Sequential(bb, head)
    
    # ========================================
    # EXPERIMENTS
    # ========================================
    print("\n" + "=" * 60)
    print("[2/3] Running 8 Experiments")
    print("=" * 60)
    sys.stdout.flush()
    
    results = []
    cp = get_class_params(nc)
    
    # 1. Softmax (baseline)
    # print("\n--- BASELINE ---")
    # r = train_experiment("1. Softmax", build_model(), 
    #                      SoftmaxLoss(config.EMBED_DIM, nc),
    #                      train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 2. ArcFace
    # print("\n--- ARCFACE ---")
    # r = train_experiment("2. ArcFace", build_model(),
    #                      ArcFaceLoss(config.EMBED_DIM, nc),
    #                      train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 3. FuzzyArcLoss V1 (original)
    # print("\n--- FUZZYARCLOSS V1 (uncertain → full margin) ---")
    # r = train_experiment("3. FuzzyArcLoss V1", build_model(),
    #                      FuzzyArcLossV1(config.EMBED_DIM, nc),
    #                      train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 4. FuzzyArcLoss V2 (inverse)
    # print("\n--- FUZZYARCLOSS V2 (confident → full margin) ---")
    # r = train_experiment("4. FuzzyArcLoss V2", build_model(),
    #                      FuzzyArcLossV2(config.EMBED_DIM, nc),
    #                      train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 5. FuzzyArcLoss V2 + ClassParams
    # print("\n--- FUZZYARCLOSS V2 + CLASS PARAMS ---")
    # r = train_experiment("5. V2 + ClassParams", build_model(),
    #                      FuzzyArcLossV2(config.EMBED_DIM, nc,
    #                                    class_tau=cp['class_tau'],
    #                                    class_margin=cp['class_margin'],
    #                                    class_scale=cp['class_scale']),
    #                      train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # 6. FuzzyArcLoss V2.5 (V2 + SubCenters K=3)
    print("\n--- FUZZYARCLOSS V2.5 (V2 + SUBCENTERS K=3) ---")
    r = train_experiment("6. V2.5 SubCenters(K=3)", build_model(),
                         FuzzyArcLossV2_5(config.EMBED_DIM, nc, K=3),
                         train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # 7. FuzzyArcLoss V2.5 + ClassParams
    print("\n--- FUZZYARCLOSS V2.5 + CLASS PARAMS ---")
    r = train_experiment("7. V2.5 + ClassParams", build_model(),
                         FuzzyArcLossV2_5(config.EMBED_DIM, nc, K=3,
                                         class_tau=cp['class_tau'],
                                         class_margin=cp['class_margin'],
                                         class_scale=cp['class_scale']),
                         train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # 8. FuzzyArcLoss V2.5 K=5 + ClassParams
    print("\n--- FUZZYARCLOSS V2.5 K=5 + CLASS PARAMS ---")
    r = train_experiment("8. V2.5 K=5 + ClassParams", build_model(),
                         FuzzyArcLossV2_5(config.EMBED_DIM, nc, K=5,
                                         class_tau=cp['class_tau'],
                                         class_margin=cp['class_margin'],
                                         class_scale=cp['class_scale']),
                         train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # ========================================
    # FINAL RESULTS
    # ========================================
    print("\n" + "=" * 60)
    print("[3/3] FINAL RESULTS")
    print("=" * 60)
    
    print(f"\n{'#':<4} {'Method':<30} {'Acc':>8} {'Macro-F1':>10} {'Epoch':>8}")
    print("-" * 65)
    for i, r in enumerate(sorted(results, key=lambda x: x['f1'], reverse=True), 1):
        print(f"{i:<4} {r['name']:<30} {r['acc']*100:>7.2f}% {r['f1']*100:>9.2f}% {r['best_ep']:>8}")
    
    print(f"\n\nPER-CLASS F1 COMPARISON:")
    print("-" * 100)
    hdr = f"{'Method':<30}" + "".join(f"{l[:10]:>12}" for l in labels)
    print(hdr)
    print("-" * 100)
    for r in sorted(results, key=lambda x: x['f1'], reverse=True):
        row = f"{r['name']:<30}" + "".join(f"{v*100:>12.1f}" for v in r['f1_cls'])
        print(row)
    
    # Save results
    os.makedirs(config.OUT_DIR, exist_ok=True)
    results_path = os.path.join(config.OUT_DIR, 'results_v2_5.json')
    with open(results_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'config': {
                'epochs': config.EPOCHS,
                'batch_size': config.BATCH_SIZE,
                'seed': config.SEED,
            },
            'labels': labels,
            'results': results
        }, f, indent=2)
    print(f"\n✓ Results saved to: {results_path}")
    
    # Winner
    best = max(results, key=lambda x: x['f1'])
    print(f"\n{'='*60}")
    print(f"  🏆 WINNER: {best['name']}")
    print(f"     Macro-F1: {best['f1']*100:.2f}%")
    print(f"     Accuracy: {best['acc']*100:.2f}%")
    print(f"     Best Epoch: {best['best_ep']}")
    print(f"{'='*60}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
