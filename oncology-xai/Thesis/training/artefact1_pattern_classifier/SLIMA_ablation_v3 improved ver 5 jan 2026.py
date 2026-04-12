#!/usr/bin/env python3
"""
Complete Ablation Study: FuzzyArcLoss V1 vs V2 vs V3
====================================================

V3 Innovations (addressing GPT-5.2 feedback):
1. Sub-center architecture (K prototypes per class)
2. Entropy-based uncertainty (non-self-referential)
3. Learnable class parameters with constraints
4. Top-1 vs Top-2 gap uncertainty option

Loss Functions Compared:
------------------------
1. Softmax (baseline)
2. ArcFace
3. FuzzyArcLoss V1 (original)
4. FuzzyArcLoss V2 (inverse fuzzy)
5. FuzzyArcLoss V2 + ClassParams
6. FuzzyArcLoss V3 + Entropy
7. FuzzyArcLoss V3 + TopGap
8. FuzzyArcLoss V3 + SubCenters (K=3)
9. FuzzyArcLoss V3 + SubCenters + Entropy
10. FuzzyArcLoss V3 + SubCenters + Learnable

Multi-GPU with DataParallel, NUM_WORKERS=0 to avoid shm issues.

Usage:
    python SLIMA_ablation_v3.py

Author: Servio F. Lima
"""

import os
import sys
import math
import json
import random
import warnings
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
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
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/ablation_v3"
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
    
    VAL_SIZE: float = 0.15
    TEST_SIZE: float = 0.15
    SEED: int = 42
    
    NUM_WORKERS: int = 0  # Avoid shared memory issues
    USE_DATAPARALLEL: bool = True
    
    @property
    def IMAGE_DIR(self):
        return f"{self.ROOT_DIR}/image"
    
    @property
    def MASK_DIR(self):
        return f"{self.ROOT_DIR}/mask"


config = Config()


# ==============================================================================
# AUXILIARY COMPONENTS
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
# LOSS FUNCTIONS
# ==============================================================================

class SoftmaxLoss(nn.Module):
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.head = nn.Linear(in_features, out_features)
        self.weight = self.head.weight
    
    def forward(self, features, labels):
        logits = self.head(features)
        return F.cross_entropy(logits, labels), logits


class ArcFaceLoss(nn.Module):
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


# ==============================================================================
# FUZZYARCLOSS V1 (Original)
# ==============================================================================

class FuzzyArcLossV1(nn.Module):
    """V1: uncertain → full margin"""
    def __init__(self, in_features: int, out_features: int, s=30.0, m=0.5, tau=0.5):
        super().__init__()
        self.s, self.m, self.tau = s, m, tau
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
        # V1: uncertain (low cos) → μ=1 (full margin)
        mu = torch.where(target_cos.abs() >= self.tau, target_cos.abs(), torch.ones_like(target_cos)).clamp(0,1)
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        output = self.s * (one_hot * target_logits + (1 - one_hot) * cosine)
        
        return 0.7 * self.ce(output, labels) + 0.3 * self.focal(output, labels), output


# ==============================================================================
# FUZZYARCLOSS V2 (Inverse)
# ==============================================================================

class FuzzyArcLossV2(nn.Module):
    """V2: confident → full margin (inverse)"""
    def __init__(self, in_features: int, out_features: int, s=30.0, m=0.5, tau=0.5,
                 class_tau=None, class_margin=None, class_scale=None):
        super().__init__()
        self.s, self.m, self.tau = s, m, tau
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        self.register_buffer('class_tau', class_tau if class_tau is not None else torch.full((out_features,), tau))
        self.register_buffer('class_margin', class_margin if class_margin is not None else torch.full((out_features,), m))
        self.register_buffer('class_scale', class_scale if class_scale is not None else torch.full((out_features,), s))
        
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
        
        # V2: confident → high μ (full margin)
        mu = torch.where(target_cos.abs() >= tau, 
                         0.8 + 0.2 * target_cos.abs(),
                         0.3 + 0.4 * target_cos.abs()).clamp(0.1, 1.0)
        
        margins = self.class_margin[labels]
        phi = cosine.clone()
        for i in range(B):
            m_i = margins[i].item()
            cos_m, sin_m = math.cos(m_i), math.sin(m_i)
            c = labels[i].item()
            cos_theta_m = cosine[i,c] * cos_m - sine[i,c] * sin_m
            th = math.cos(math.pi - m_i)
            phi[i,c] = cos_theta_m if cosine[i,c].item() > th else cosine[i,c] - math.sin(math.pi-m_i)*m_i
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        output = output * self.class_scale[labels].unsqueeze(1)
        
        return 0.6 * self.ce(output, labels) + 0.4 * self.focal(output, labels), output


# ==============================================================================
# FUZZYARCLOSS V3 (Entropy-based + Optional SubCenters)
# ==============================================================================

class FuzzyArcLossV3(nn.Module):
    """
    V3: Non-self-referential uncertainty + optional sub-centers + learnable params
    
    Key improvements:
    - Uncertainty from entropy/top-gap (not circular cosine dependency)
    - K sub-centers per class for multi-modal patterns
    - Learnable tau/margin/scale with diversity regularization
    """
    def __init__(self, in_features: int, out_features: int, 
                 s=30.0, m=0.5, tau=0.5,
                 K: int = 1,  # 1 = no subcenters, >1 = subcenters
                 uncertainty: str = 'entropy',  # 'entropy', 'top_gap', 'cosine'
                 learn_params: bool = False,
                 class_tau=None, class_margin=None, class_scale=None):
        super().__init__()
        self.s, self.m, self.tau = s, m, tau
        self.K = K
        self.uncertainty = uncertainty
        self.learn_params = learn_params
        self.out_features = out_features
        
        # Weights: (C, K, D) if K>1, else (C, D)
        if K > 1:
            self.weight = nn.Parameter(torch.FloatTensor(out_features, K, in_features))
            nn.init.xavier_uniform_(self.weight.view(out_features * K, in_features))
        else:
            self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
            nn.init.xavier_uniform_(self.weight)
        
        # Class params
        tau_init = class_tau if class_tau is not None else torch.full((out_features,), tau)
        m_init = class_margin if class_margin is not None else torch.full((out_features,), m)
        s_init = class_scale if class_scale is not None else torch.full((out_features,), s)
        
        if learn_params:
            self.class_tau = nn.Parameter(tau_init.clone())
            self.class_margin = nn.Parameter(m_init.clone())
            self.class_scale = nn.Parameter(s_init.clone())
        else:
            self.register_buffer('class_tau', tau_init)
            self.register_buffer('class_margin', m_init)
            self.register_buffer('class_scale', s_init)
        
        self.ce = LabelSmoothingCE(0.1)
        self.focal = FocalLoss(2.0)
    
    def _get_cosine(self, features):
        """Compute cosine, handling sub-centers"""
        f_norm = F.normalize(features, dim=1)
        
        if self.K > 1:
            w_norm = F.normalize(self.weight, dim=2)  # (C, K, D)
            cosine_all = torch.einsum('bd,ckd->bck', f_norm, w_norm)  # (B, C, K)
            cosine, _ = cosine_all.max(dim=2)  # Max over sub-centers
        else:
            w_norm = F.normalize(self.weight, dim=1)
            cosine = F.linear(f_norm, w_norm)
        
        return cosine.clamp(-1+1e-7, 1-1e-7)
    
    def _compute_uncertainty(self, cosine, target_cos, tau):
        """Compute μ based on uncertainty method"""
        if self.uncertainty == 'entropy':
            probs = F.softmax(cosine * 10, dim=1)
            entropy = -(probs * (probs + 1e-8).log()).sum(dim=1)
            max_ent = math.log(cosine.size(1))
            norm_ent = entropy / max_ent
            mu = 1.0 - 0.7 * norm_ent  # High entropy → low μ
        elif self.uncertainty == 'top_gap':
            top2, _ = cosine.topk(2, dim=1)
            gap = (top2[:,0] - top2[:,1]) / (top2[:,0].abs() + 1e-8)
            mu = 0.3 + 0.7 * gap.clamp(0, 1)  # Large gap → high μ
        else:  # cosine (V2 style)
            mu = torch.where(target_cos.abs() >= tau,
                             0.8 + 0.2 * target_cos.abs(),
                             0.3 + 0.4 * target_cos.abs())
        return mu.clamp(0.2, 1.0)
    
    def get_weight_for_eval(self):
        """Return weights for evaluation (mean of sub-centers if K>1)"""
        if self.K > 1:
            return self.weight.mean(dim=1)  # (C, D)
        return self.weight
    
    def forward(self, features, labels):
        B = features.size(0)
        device = features.device
        
        cosine = self._get_cosine(features)
        sine = torch.sqrt(1 - cosine**2 + 1e-7)
        target_cos = cosine[torch.arange(B, device=device), labels]
        
        # Constrained params
        tau = self.class_tau[labels].clamp(0.2, 0.8)
        margins = self.class_margin[labels].clamp(0.1, 0.7)
        scales = self.class_scale[labels].clamp(15.0, 50.0)
        
        # Non-self-referential uncertainty
        mu = self._compute_uncertainty(cosine, target_cos, tau)
        
        # Angular margin
        phi = cosine.clone()
        for i in range(B):
            m_i = margins[i].item()
            cos_m, sin_m = math.cos(m_i), math.sin(m_i)
            c = labels[i].item()
            cos_theta_m = cosine[i,c] * cos_m - sine[i,c] * sin_m
            th = math.cos(math.pi - m_i)
            phi[i,c] = cos_theta_m if cosine[i,c].item() > th else cosine[i,c] - math.sin(math.pi-m_i)*m_i
        
        one_hot = F.one_hot(labels, self.out_features).float()
        mu_exp = mu.unsqueeze(1)
        target_logits = mu_exp * phi + (1 - mu_exp) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        output = output * scales.unsqueeze(1)
        
        loss = 0.6 * self.ce(output, labels) + 0.4 * self.focal(output, labels)
        
        # Diversity regularization for learnable params
        if self.learn_params:
            loss = loss - 0.01 * (self.class_tau.var() + self.class_margin.var())
        
        return loss, output


def get_class_params():
    """Lung adenocarcinoma class-specific parameters"""
    return {
        'class_tau': torch.tensor([0.35, 0.45, 0.35, 0.50, 0.60, 0.65]),
        'class_margin': torch.tensor([0.35, 0.45, 0.35, 0.50, 0.55, 0.60]),
        'class_scale': torch.tensor([25.0, 28.0, 25.0, 30.0, 32.0, 35.0]),
    }


# ==============================================================================
# BACKBONE
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
            self.model = timm.create_model('swin_tiny_patch4_window7_224', pretrained=False, num_classes=0, global_pool='avg')
            self.model.patch_embed = ConvStem(96)
            self.out_features = 768
            if os.path.exists(ckpt_path):
                sd = torch.load(ckpt_path, map_location='cpu')
                sd = sd.get('model', sd)
                ms = self.model.state_dict()
                self.model.load_state_dict({k:v for k,v in sd.items() if k in ms and v.shape==ms[k].shape}, strict=False)
                print("  ✓ Loaded CTransPath")
        else:
            from torchvision import models
            self.model = models.resnet50(pretrained=True)
            self.model.fc = nn.Identity()
            self.out_features = 2048
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
        if ext.lower() not in IMG_EXTS: continue
        for mext in ['.mat','.png','.jpg','.tif']:
            mp = os.path.join(mask_dir, stem+mext)
            if os.path.exists(mp):
                records.append({'image_path': os.path.join(img_dir,f), 'mask_path': mp, 'stem': stem})
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
        return (np.array(Image.open(path).convert('L'))/255 > thresh).astype(np.uint8)
    return None

class HistDataset(Dataset):
    def __init__(self, df, label_col, label2id, img_size=224, aug=True, use_roi=True, pad=24):
        self.df = df.reset_index(drop=True)
        self.label_col, self.label2id = label_col, label2id
        self.use_roi, self.pad = use_roi, pad
        if aug:
            self.tfm = T.Compose([T.RandomHorizontalFlip(), T.RandomVerticalFlip(), T.RandomRotation(15),
                                  T.ColorJitter(0.2,0.2,0.1), T.Resize((img_size,img_size)), T.ToTensor(),
                                  T.Normalize([.485,.456,.406],[.229,.224,.225])])
        else:
            self.tfm = T.Compose([T.Resize((img_size,img_size)), T.ToTensor(), T.Normalize([.485,.456,.406],[.229,.224,.225])])
    
    def __len__(self): return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = Image.open(row['image_path']).convert('RGB')
        if self.use_roi and 'mask_path' in row:
            m = load_mask(row['mask_path'])
            if m is not None:
                coords = np.argwhere(m > 0)
                if len(coords):
                    y0,x0 = coords.min(0); y1,x1 = coords.max(0)+1
                    img = img.crop((max(0,x0-self.pad), max(0,y0-self.pad), min(m.shape[1],x1+self.pad), min(m.shape[0],y1+self.pad)))
        return self.tfm(img), self.label2id[str(row[self.label_col])]


# ==============================================================================
# TRAINING
# ==============================================================================

def train_exp(name, model, loss_fn, train_ld, val_ld, test_ld, id2label, device, epochs=175):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")
    
    if config.USE_DATAPARALLEL and torch.cuda.device_count() > 1:
        print(f"  Using {torch.cuda.device_count()} GPUs")
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
        model.train(); loss_fn.train()
        tot_loss = 0
        for imgs, lbls in train_ld:
            imgs, lbls = imgs.to(device), lbls.to(device)
            opt.zero_grad()
            with torch.cuda.amp.autocast():
                loss, _ = loss_fn(model(imgs), lbls)
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            torch.nn.utils.clip_grad_norm_(loss_fn.parameters(), 1.0)
            scaler.step(opt); scaler.update()
            tot_loss += loss.item()
        
        model.eval()
        preds, gt = [], []
        with torch.no_grad():
            for imgs, lbls in val_ld:
                feats = model(imgs.to(device))
                w = loss_fn.get_weight_for_eval() if hasattr(loss_fn, 'get_weight_for_eval') else loss_fn.weight
                w = F.normalize(w, dim=1)
                logits = F.normalize(feats, dim=1) @ w.t()
                preds.extend(logits.argmax(1).cpu().numpy())
                gt.extend(lbls.numpy())
        
        vf1 = f1_score(gt, preds, average='macro')
        if vf1 > best_f1:
            best_f1, best_ep = vf1, ep
            base = model.module if hasattr(model, 'module') else model
            best_state = {'model': {k:v.cpu().clone() for k,v in base.state_dict().items()},
                          'loss': {k:v.cpu().clone() for k,v in loss_fn.state_dict().items()}}
        
        if (ep+1) % 20 == 0:
            print(f"  Ep {ep+1:3d} | Loss {tot_loss/len(train_ld):.4f} | Val F1 {vf1:.4f} | Best {best_f1:.4f}@{best_ep+1}")
        sched.step()
    
    # Load best & test
    if best_state:
        base = model.module if hasattr(model, 'module') else model
        base.load_state_dict({k:v.to(device) for k,v in best_state['model'].items()})
        loss_fn.load_state_dict({k:v.to(device) for k,v in best_state['loss'].items()})
    
    model.eval()
    preds, gt = [], []
    with torch.no_grad():
        for imgs, lbls in test_ld:
            feats = model(imgs.to(device))
            w = loss_fn.get_weight_for_eval() if hasattr(loss_fn, 'get_weight_for_eval') else loss_fn.weight
            w = F.normalize(w, dim=1)
            logits = F.normalize(feats, dim=1) @ w.t()
            preds.extend(logits.argmax(1).cpu().numpy())
            gt.extend(lbls.numpy())
    
    preds, gt = np.array(preds), np.array(gt)
    acc = accuracy_score(gt, preds)
    f1 = f1_score(gt, preds, average='macro')
    f1_cls = f1_score(gt, preds, average=None)
    
    print(f"\n  TEST: Acc={acc*100:.2f}% | Macro-F1={f1*100:.2f}%")
    for i, v in enumerate(f1_cls):
        print(f"    {id2label[i]}: {v*100:.1f}%")
    
    return {'name': name, 'acc': acc, 'f1': f1, 'f1_cls': f1_cls.tolist(), 'best_ep': best_ep+1}


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("="*60)
    print("  ABLATION: FuzzyArcLoss V1 vs V2 vs V3")
    print("="*60)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPUs: {torch.cuda.device_count()} x {torch.cuda.get_device_name(0)}")
    
    random.seed(config.SEED); np.random.seed(config.SEED)
    torch.manual_seed(config.SEED); torch.cuda.manual_seed_all(config.SEED)
    
    # Data
    print("\n[1/3] Loading data...")
    df = pair_images_masks(config.IMAGE_DIR, config.MASK_DIR)
    xls = pd.read_excel(config.XLS_PATH)
    xls['stem'] = xls['tile_id'].astype(str)
    xls = xls[xls['pattern'].str.lower() != 'none']
    df = df.merge(xls[['stem','pattern']], on='stem', how='inner').dropna(subset=['pattern'])
    
    labels = sorted(df['pattern'].astype(str).unique())
    label2id = {l:i for i,l in enumerate(labels)}
    id2label = {i:l for l,i in label2id.items()}
    nc = len(labels)
    print(f"  Samples: {len(df)}, Classes: {nc}")
    
    train_df, temp = train_test_split(df, test_size=0.3, stratify=df['pattern'], random_state=config.SEED)
    val_df, test_df = train_test_split(temp, test_size=0.5, stratify=temp['pattern'], random_state=config.SEED)
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    train_lbls = [label2id[str(l)] for l in train_df['pattern']]
    cc = [train_lbls.count(i) for i in range(nc)]
    
    train_ds = HistDataset(train_df, 'pattern', label2id, config.IMG_SIZE, True, config.USE_ROI_CROP)
    val_ds = HistDataset(val_df, 'pattern', label2id, config.IMG_SIZE, False, config.USE_ROI_CROP)
    test_ds = HistDataset(test_df, 'pattern', label2id, config.IMG_SIZE, False, config.USE_ROI_CROP)
    
    sampler = WeightedRandomSampler([1.0/cc[l] for l in train_lbls], len(train_lbls), True)
    train_ld = DataLoader(train_ds, config.BATCH_SIZE, sampler=sampler, num_workers=config.NUM_WORKERS, pin_memory=True)
    val_ld = DataLoader(val_ds, config.BATCH_SIZE, num_workers=config.NUM_WORKERS, pin_memory=True)
    test_ld = DataLoader(test_ds, config.BATCH_SIZE, num_workers=config.NUM_WORKERS, pin_memory=True)
    
    def build_model():
        bb = CTransPathBackbone(config.CTRANSPATH_CHECKPOINT, config.FREEZE_BACKBONE_LAYERS)
        head = nn.Sequential(nn.Linear(bb.out_features, config.EMBED_DIM), nn.LayerNorm(config.EMBED_DIM), nn.GELU(), nn.Dropout(0.15))
        return nn.Sequential(bb, head)
    
    # ========================================
    print("\n" + "="*60)
    print("[2/3] Running Experiments")
    print("="*60)
    
    results = []
    cp = get_class_params()
    
    # # 1. Softmax
    # r = train_exp("1. Softmax", build_model(), SoftmaxLoss(config.EMBED_DIM, nc), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 2. ArcFace
    # r = train_exp("2. ArcFace", build_model(), ArcFaceLoss(config.EMBED_DIM, nc), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 3. FuzzyArcLoss V1
    # r = train_exp("3. FuzzyArcLoss V1", build_model(), FuzzyArcLossV1(config.EMBED_DIM, nc), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 4. FuzzyArcLoss V2
    # r = train_exp("4. FuzzyArcLoss V2", build_model(), FuzzyArcLossV2(config.EMBED_DIM, nc), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # # 5. FuzzyArcLoss V2 + ClassParams
    # r = train_exp("5. V2 + ClassParams", build_model(), FuzzyArcLossV2(config.EMBED_DIM, nc, class_tau=cp['class_tau'], class_margin=cp['class_margin'], class_scale=cp['class_scale']), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    # results.append(r)
    
    # 6. FuzzyArcLoss V3 + Entropy
    r = train_exp("6. V3 + Entropy", build_model(), FuzzyArcLossV3(config.EMBED_DIM, nc, K=1, uncertainty='entropy'), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # 7. FuzzyArcLoss V3 + TopGap
    r = train_exp("7. V3 + TopGap", build_model(), FuzzyArcLossV3(config.EMBED_DIM, nc, K=1, uncertainty='top_gap'), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # 8. FuzzyArcLoss V3 + SubCenters (K=3)
    r = train_exp("8. V3 + SubCenters(K=3)", build_model(), FuzzyArcLossV3(config.EMBED_DIM, nc, K=3, uncertainty='cosine'), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # 9. FuzzyArcLoss V3 + SubCenters + Entropy
    r = train_exp("9. V3 + SubCenters + Entropy", build_model(), FuzzyArcLossV3(config.EMBED_DIM, nc, K=3, uncertainty='entropy'), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # 10. FuzzyArcLoss V3 + SubCenters + Learnable
    r = train_exp("10. V3 + SubCenters + Learnable", build_model(), FuzzyArcLossV3(config.EMBED_DIM, nc, K=3, uncertainty='entropy', learn_params=True, class_tau=cp['class_tau'].clone(), class_margin=cp['class_margin'].clone(), class_scale=cp['class_scale'].clone()), train_ld, val_ld, test_ld, id2label, device, config.EPOCHS)
    results.append(r)
    
    # ========================================
    print("\n" + "="*60)
    print("[3/3] FINAL RESULTS")
    print("="*60)
    
    print(f"\n{'#':<4} {'Method':<35} {'Acc':>8} {'F1':>8} {'Epoch':>8}")
    print("-"*65)
    for i, r in enumerate(sorted(results, key=lambda x: x['f1'], reverse=True), 1):
        print(f"{i:<4} {r['name']:<35} {r['acc']*100:>7.2f}% {r['f1']*100:>7.2f}% {r['best_ep']:>8}")
    
    print(f"\n\nPER-CLASS F1:")
    print("-"*90)
    hdr = f"{'Method':<35}" + "".join(f"{l[:8]:>10}" for l in labels)
    print(hdr)
    print("-"*90)
    for r in sorted(results, key=lambda x: x['f1'], reverse=True):
        row = f"{r['name']:<35}" + "".join(f"{v*100:>10.1f}" for v in r['f1_cls'])
        print(row)
    
    os.makedirs(config.OUT_DIR, exist_ok=True)
    with open(os.path.join(config.OUT_DIR, 'results_v3.json'), 'w') as f:
        json.dump({'timestamp': datetime.now().isoformat(), 'results': results}, f, indent=2)
    
    best = max(results, key=lambda x: x['f1'])
    print(f"\n{'='*60}")
    print(f"  🏆 WINNER: {best['name']}")
    print(f"     Macro-F1: {best['f1']*100:.2f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
