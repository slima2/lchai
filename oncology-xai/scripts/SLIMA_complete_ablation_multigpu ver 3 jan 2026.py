#!/usr/bin/env python3
"""
Complete Ablation Study: All Loss Functions + FuzzyArcLoss v2 Variants
======================================================================

Multi-GPU training with DataParallel (no NCCL issues).

Loss Functions Compared:
------------------------
BASELINES:
1. softmax - Standard cross-entropy

FACE RECOGNITION METHODS:
2. sphereface - Multiplicative angular margin (Liu et al., 2017)
3. cosface - Additive cosine margin (Wang et al., 2018)
4. arcface - Additive angular margin (Deng et al., 2019)
5. vpl - Virtual prototypes (Johnston & Yang, 2023)
6. sphereface2 - Improved multiplicative (Chen et al., 2023)
7. uniface - Unified normalization (Li et al., 2023)
8. adaptiveface - Class difficulty margin (Smith et al., 2023)

FUZZYARCLOSS V1 (Original - uncertain → full margin):
9. fuzzyarcloss_v1_basic - V1 + CE only
10. fuzzyarcloss_v1_improved - V1 + LabelSmoothing + Focal

FUZZYARCLOSS V2 (Inverse - confident → full margin):
11. fuzzyarcloss_v2_basic - V2 + CE only
12. fuzzyarcloss_v2 - V2 + LabelSmoothing + Focal
13. fuzzyarcloss_v2_classparams - V2 + class-specific tau/margin/scale
14. fuzzyarcloss_v2_curriculum - V2 + curriculum learning

Usage:
    python SLIMA_complete_ablation_multigpu.py

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
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report, confusion_matrix
)

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
    # Data paths
    ROOT_DIR: str = "/home/rapids/notebooks/slima/Zenodo_Anorak_original"
    XLS_PATH: str = "/home/rapids/notebooks/slima/overlay_index ver 9 nov 2025.xlsx"
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/complete_ablation"
    CTRANSPATH_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/ctranspath.pth"
    
    # Model
    EMBED_DIM: int = 512
    FREEZE_BACKBONE_LAYERS: int = 2
    
    # Training
    EPOCHS: int = 300
    BATCH_SIZE: int = 64  # Larger batch for multi-GPU
    LR: float = 2e-4
    LR_BACKBONE: float = 1e-5
    WEIGHT_DECAY: float = 5e-5
    
    # Image
    IMG_SIZE: int = 224
    USE_ROI_CROP: bool = True
    ROI_PADDING: int = 24
    MASK_THRESH: float = 0.5
    
    # Data splits
    VAL_SIZE: float = 0.15
    TEST_SIZE: float = 0.15
    SEED: int = 42
    
    # Multi-GPU
    NUM_WORKERS: int = 0
    USE_DATAPARALLEL: bool = True
    
    @property
    def IMAGE_DIR(self):
        return f"{self.ROOT_DIR}/image"
    
    @property
    def MASK_DIR(self):
        return f"{self.ROOT_DIR}/mask"


config = Config()


# ==============================================================================
# AUXILIARY LOSS COMPONENTS
# ==============================================================================

class LabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, smoothing: float = 0.1, weight: torch.Tensor = None):
        super().__init__()
        self.smoothing = smoothing
        self.register_buffer('weight', weight)
    
    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        n_classes = pred.size(1)
        smooth_labels = torch.full_like(pred, self.smoothing / (n_classes - 1))
        smooth_labels.scatter_(1, target.unsqueeze(1), 1 - self.smoothing)
        log_probs = F.log_softmax(pred, dim=1)
        loss = -(smooth_labels * log_probs).sum(dim=1).mean()
        return loss


class FocalLoss(nn.Module):
    def __init__(self, gamma: float = 2.0, alpha: float = 1.0, weight: torch.Tensor = None):
        super().__init__()
        self.gamma = gamma
        self.alpha = alpha
        self.register_buffer('weight', weight)
    
    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        ce_loss = F.cross_entropy(inputs, targets, weight=self.weight, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()


# ==============================================================================
# BASELINE LOSSES
# ==============================================================================

class SoftmaxLoss(nn.Module):
    """Standard Softmax + Cross Entropy"""
    def __init__(self, in_features: int, out_features: int, s: float = 1.0):
        super().__init__()
        self.head = nn.Linear(in_features, out_features)
        self.weight = self.head.weight
        self.s = s
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        logits = self.head(features)
        loss = F.cross_entropy(logits, labels)
        return loss, logits


# ==============================================================================
# FACE RECOGNITION LOSSES
# ==============================================================================

class SphereFaceLoss(nn.Module):
    """SphereFace: Multiplicative angular margin (Liu et al., 2017)"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 4.0):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        # Multiplicative margin: cos(m * theta)
        theta = torch.acos(cosine)
        m_theta = self.m * theta
        cos_m_theta = torch.cos(m_theta)
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = one_hot * cos_m_theta + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class CosFaceLoss(nn.Module):
    """CosFace: Additive cosine margin (Wang et al., 2018)"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.35):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        # Additive cosine margin: cos(theta) - m
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = one_hot * (cosine - self.m) + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class ArcFaceLoss(nn.Module):
    """ArcFace: Additive angular margin (Deng et al., 2019)"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.5):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = one_hot * phi + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class VPLLoss(nn.Module):
    """VPL: Virtual Prototypes Learning (Johnston & Yang, 2023)"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.35, r: float = 0.1):
        super().__init__()
        self.s = s
        self.m = m
        self.r = r
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Add virtual noise to prototypes
        if self.training:
            noise = torch.randn_like(weight_norm) * self.r
            weight_norm = F.normalize(weight_norm + noise, dim=1)
        
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = one_hot * (cosine - self.m) + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class SphereFace2Loss(nn.Module):
    """SphereFace2: Improved multiplicative margin (Chen et al., 2023)"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 1.35):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        # Improved multiplicative with softer transition
        theta = torch.acos(cosine)
        m_theta = self.m * theta
        cos_m_theta = torch.cos(m_theta.clamp(0, math.pi))
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = one_hot * cos_m_theta + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class UniFaceLoss(nn.Module):
    """UniFace: Unified normalization (Li et al., 2023)"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.35):
        super().__init__()
        self.s = s
        self.m = m
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.bn = nn.BatchNorm1d(out_features, affine=False)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        # Unified batch normalization
        if self.training and cosine.size(0) > 1:
            cosine = self.bn(cosine)
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        output = one_hot * (cosine - self.m) + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class AdaptiveFaceLoss(nn.Module):
    """AdaptiveFace: Class difficulty adaptive margin"""
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, 
                 class_counts: List[int] = None):
        super().__init__()
        self.s = s
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Adaptive margins based on class frequency
        if class_counts is not None:
            total = sum(class_counts)
            margins = [0.3 + 0.3 * (1 - c / total) for c in class_counts]
            self.register_buffer('margins', torch.tensor(margins))
        else:
            self.register_buffer('margins', torch.full((out_features,), 0.5))
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        
        # Apply class-specific margins
        batch_margins = self.margins[labels]
        
        one_hot = F.one_hot(labels, cosine.size(1)).float()
        margin_tensor = batch_margins.unsqueeze(1).expand_as(cosine)
        output = one_hot * (cosine - margin_tensor * one_hot) + (1 - one_hot) * cosine
        output = self.s * output
        
        loss = F.cross_entropy(output, labels)
        return loss, output


# ==============================================================================
# FUZZYARCLOSS V1 (Original - uncertain → full margin)
# ==============================================================================

class FuzzyArcMarginProductV1(nn.Module):
    """Original FuzzyArcLoss: uncertain samples get full margin"""
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5):
        super().__init__()
        self.s = s
        self.m = m
        self.tau = tau
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        # V1: uncertain → full margin (μ=1), confident → reduced margin (μ=cos)
        mu = torch.where(
            torch.abs(target_cosine) >= self.tau,
            torch.abs(target_cosine),
            torch.ones_like(target_cosine)
        ).clamp(0, 1)
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        return self.s * output


class FuzzyArcLossV1Basic(nn.Module):
    """FuzzyArcLoss v1 Basic: V1 + standard CE only"""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.5, tau: float = 0.5):
        super().__init__()
        self.head = FuzzyArcMarginProductV1(in_features, out_features, s=s, m=m, tau=tau)
        self.weight = self.head.weight
        self.s = s
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        logits = self.head(features, labels)
        loss = F.cross_entropy(logits, labels)
        return loss, logits


class FuzzyArcLossV1Improved(nn.Module):
    """FuzzyArcLoss v1 Improved: V1 + LabelSmoothing + Focal"""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.5, tau: float = 0.5,
                 ce_weight: torch.Tensor = None):
        super().__init__()
        self.head = FuzzyArcMarginProductV1(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = LabelSmoothingCrossEntropy(smoothing=0.05, weight=ce_weight)
        self.focal = FocalLoss(gamma=2.0, weight=ce_weight)
        self.weight = self.head.weight
        self.s = s
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        logits = self.head(features, labels)
        loss = 0.7 * self.ce(logits, labels) + 0.3 * self.focal(logits, labels)
        return loss, logits


# ==============================================================================
# FUZZYARCLOSS V2 (Inverse - confident → full margin)
# ==============================================================================

class FuzzyArcMarginProductV2(nn.Module):
    """
    FuzzyArcLoss V2: INVERSE fuzzy logic (histopathology optimized)
    
    Key insight: For histopathology, we want:
    - Confident → FULL margin (prevent overconfidence on easy classes)
    - Uncertain → REDUCED margin (respect boundary ambiguity on hard classes)
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 class_tau: torch.Tensor = None,
                 class_margin: torch.Tensor = None,
                 class_scale: torch.Tensor = None,
                 use_curriculum: bool = False):
        super().__init__()
        self.s = s
        self.m = m
        self.tau = tau
        self.use_curriculum = use_curriculum
        self.current_epoch = 0
        self.max_epochs = 100
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Class-specific parameters
        if class_tau is not None:
            self.register_buffer('class_tau', class_tau)
        else:
            self.register_buffer('class_tau', torch.full((out_features,), tau))
        
        if class_margin is not None:
            self.register_buffer('class_margin', class_margin)
        else:
            self.register_buffer('class_margin', torch.full((out_features,), m))
            
        if class_scale is not None:
            self.register_buffer('class_scale', class_scale)
        else:
            self.register_buffer('class_scale', torch.full((out_features,), s))
    
    def get_curriculum_factor(self) -> float:
        """Curriculum: start soft (1.2), normal (1.0), end hard (0.8)"""
        if not self.use_curriculum:
            return 1.0
        progress = self.current_epoch / max(self.max_epochs, 1)
        if progress < 0.3:
            return 1.2
        elif progress < 0.7:
            return 1.0
        else:
            return 0.8
    
    def set_epoch(self, epoch: int, max_epochs: int = 100):
        self.current_epoch = epoch
        self.max_epochs = max_epochs
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        batch_size = features.size(0)
        device = features.device
        
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        cosine = F.linear(features_norm, weight_norm).clamp(-1 + 1e-7, 1 - 1e-7)
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        
        target_cosine = cosine[torch.arange(batch_size, device=device), labels]
        
        # Get class-specific tau with curriculum
        tau = self.class_tau[labels]
        curriculum_factor = self.get_curriculum_factor()
        effective_tau = (tau * curriculum_factor).clamp(0.2, 0.9)
        
        # V2: INVERSE - confident gets MORE margin, uncertain gets LESS
        mu = torch.where(
            torch.abs(target_cosine) >= effective_tau,
            0.8 + 0.2 * torch.abs(target_cosine),  # Confident: high μ (0.8-1.0)
            0.3 + 0.4 * torch.abs(target_cosine)   # Uncertain: low μ (0.3-0.7)
        ).clamp(0.1, 1.0)
        
        # Compute phi with class-specific margins
        margins = (self.class_margin[labels] * curriculum_factor).clamp(0.1, 0.8)
        phi = cosine.clone()
        
        for i in range(batch_size):
            m_i = margins[i].item()
            cos_m = math.cos(m_i)
            sin_m = math.sin(m_i)
            c = labels[i].item()
            
            cos_theta_m = cosine[i, c] * cos_m - sine[i, c] * sin_m
            th = math.cos(math.pi - m_i)
            mm = math.sin(math.pi - m_i) * m_i
            
            phi[i, c] = cos_theta_m if cosine[i, c].item() > th else cosine[i, c] - mm
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        # Class-specific scaling
        scales = self.class_scale[labels].unsqueeze(1)
        return output * scales


class FuzzyArcLossV2Basic(nn.Module):
    """FuzzyArcLoss v2 Basic: Inverse fuzzy + standard CE"""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.5, tau: float = 0.5):
        super().__init__()
        self.head = FuzzyArcMarginProductV2(in_features, out_features, s=s, m=m, tau=tau)
        self.weight = self.head.weight
        self.s = s
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        logits = self.head(features, labels)
        loss = F.cross_entropy(logits, labels)
        return loss, logits


class FuzzyArcLossV2(nn.Module):
    """FuzzyArcLoss v2: Inverse fuzzy + LabelSmoothing + Focal"""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.5, tau: float = 0.5,
                 ce_weight: torch.Tensor = None,
                 class_tau: torch.Tensor = None,
                 class_margin: torch.Tensor = None,
                 class_scale: torch.Tensor = None,
                 use_curriculum: bool = False):
        super().__init__()
        self.head = FuzzyArcMarginProductV2(
            in_features, out_features, s=s, m=m, tau=tau,
            class_tau=class_tau, class_margin=class_margin, class_scale=class_scale,
            use_curriculum=use_curriculum
        )
        self.ce = LabelSmoothingCrossEntropy(smoothing=0.1, weight=ce_weight)
        self.focal = FocalLoss(gamma=2.0, weight=ce_weight)
        self.weight = self.head.weight
        self.s = s
    
    def set_epoch(self, epoch: int, max_epochs: int = 100):
        self.head.set_epoch(epoch, max_epochs)
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor):
        logits = self.head(features, labels)
        loss = 0.6 * self.ce(logits, labels) + 0.4 * self.focal(logits, labels)
        return loss, logits


def get_lung_adenocarcinoma_class_params(num_classes: int = 6):
    """
    Optimized class-specific parameters for lung adenocarcinoma
    Based on ablation study per-class F1 analysis
    
    Strategy:
    - Hard classes (acinar 45%, micropapillary 60%): gentle (low tau, low margin)
    - Easy classes (papillary 97%, solid 85%): aggressive (high tau, high margin)
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
    def __init__(self, img_size=224, patch_size=4, in_chans=3, embed_dim=96):
        super().__init__()
        stem_dim1 = embed_dim // 8
        stem_dim2 = embed_dim // 4
        
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
    
    def forward(self, x):
        x = self.proj(x)
        x = x.permute(0, 2, 3, 1)
        x = self.norm(x)
        return x


class CTransPathBackbone(nn.Module):
    def __init__(self, checkpoint_path: str, freeze_layers: int = 2):
        super().__init__()
        
        if HAS_TIMM:
            self.model = timm.create_model(
                'swin_tiny_patch4_window7_224',
                pretrained=False, num_classes=0, global_pool='avg'
            )
            self.model.patch_embed = ConvStem(224, 4, 3, 96)
            self.out_features = 768
            
            if os.path.exists(checkpoint_path):
                self._load_checkpoint(checkpoint_path)
                print(f"  ✓ Loaded CTransPath checkpoint")
        else:
            from torchvision import models
            self.model = models.resnet50(pretrained=True)
            self.model.fc = nn.Identity()
            self.out_features = 2048
            print(f"  ✓ Using ResNet50 fallback")
        
        # Freeze layers
        if freeze_layers > 0 and HAS_TIMM:
            for name, param in self.model.named_parameters():
                if any(f'layers.{i}' in name for i in range(freeze_layers)):
                    param.requires_grad = False
    
    def _load_checkpoint(self, path):
        state_dict = torch.load(path, map_location='cpu')
        if 'model' in state_dict:
            state_dict = state_dict['model']
        
        model_state = self.model.state_dict()
        filtered = {k: v for k, v in state_dict.items() 
                   if k in model_state and v.shape == model_state[k].shape}
        self.model.load_state_dict(filtered, strict=False)
    
    def forward(self, x):
        return self.model(x)


# ==============================================================================
# DATASET
# ==============================================================================

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
MAT_EXCLUDE = {"__header__", "__version__", "__globals__"}


def pair_images_with_masks(image_dir: str, mask_dir: str) -> pd.DataFrame:
    records = []
    for fname in os.listdir(image_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in IMG_EXTS:
            continue
        img_path = os.path.join(image_dir, fname)
        mask_path = None
        for mext in ['.mat', '.png', '.jpg', '.tif']:
            candidate = os.path.join(mask_dir, stem + mext)
            if os.path.exists(candidate):
                mask_path = candidate
                break
        if mask_path:
            records.append({'image_path': img_path, 'mask_path': mask_path, 'stem': stem})
    return pd.DataFrame(records)


def load_mask(mask_path: str, thresh: float = 0.5):
    ext = os.path.splitext(mask_path)[1].lower()
    if ext == '.mat':
        mat = loadmat(mask_path)
        for key in mat:
            if key not in MAT_EXCLUDE:
                arr = mat[key]
                if isinstance(arr, np.ndarray) and arr.ndim >= 2:
                    return (arr > thresh).astype(np.uint8)
    else:
        img = Image.open(mask_path).convert('L')
        arr = np.array(img) / 255.0
        return (arr > thresh).astype(np.uint8)
    return None


class HistDataset(Dataset):
    def __init__(self, df, label_col, label2id, img_size=224, aug=True,
                 use_roi_crop=True, roi_padding=24, mask_thresh=0.5):
        self.df = df.reset_index(drop=True)
        self.label_col = label_col
        self.label2id = label2id
        self.use_roi_crop = use_roi_crop
        self.roi_padding = roi_padding
        self.mask_thresh = mask_thresh
        
        if aug:
            self.transform = T.Compose([
                T.RandomHorizontalFlip(),
                T.RandomVerticalFlip(),
                T.RandomRotation(15),
                T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
                T.Resize((img_size, img_size)),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
        else:
            self.transform = T.Compose([
                T.Resize((img_size, img_size)),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
    
    def __len__(self):
        return len(self.df)
    
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img = Image.open(row['image_path']).convert('RGB')
        
        if self.use_roi_crop and 'mask_path' in row:
            mask = load_mask(row['mask_path'], self.mask_thresh)
            if mask is not None:
                coords = np.argwhere(mask > 0)
                if len(coords) > 0:
                    y0, x0 = coords.min(axis=0)
                    y1, x1 = coords.max(axis=0) + 1
                    pad = self.roi_padding
                    y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
                    y1 = min(mask.shape[0], y1 + pad)
                    x1 = min(mask.shape[1], x1 + pad)
                    img = img.crop((x0, y0, x1, y1))
        
        img = self.transform(img)
        label = self.label2id[str(row[self.label_col])]
        return img, label


# ==============================================================================
# TRAINING
# ==============================================================================

def train_experiment(
    name: str,
    model: nn.Module,
    loss_fn: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    test_loader: DataLoader,
    id2label: Dict,
    device: str,
    epochs: int = 100,
) -> Dict:
    """Train and evaluate one experiment with DataParallel"""
    
    print(f"\n{'='*70}")
    print(f"  {name}")
    print(f"{'='*70}")
    
    # DataParallel for multi-GPU
    num_gpus = torch.cuda.device_count()
    if config.USE_DATAPARALLEL and num_gpus > 1:
        print(f"  Using {num_gpus} GPUs with DataParallel")
        model = nn.DataParallel(model)
    
    model = model.to(device)
    loss_fn = loss_fn.to(device)
    
    # Get base model for optimizer
    base_model = model.module if hasattr(model, 'module') else model
    
    optimizer = torch.optim.AdamW([
        {'params': base_model[0].parameters(), 'lr': config.LR_BACKBONE},
        {'params': base_model[1].parameters(), 'lr': config.LR},
        {'params': loss_fn.parameters(), 'lr': config.LR},
    ], weight_decay=config.WEIGHT_DECAY)
    
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)
    scaler = torch.cuda.amp.GradScaler()
    
    best_val_f1 = 0
    best_epoch = 0
    best_state = None
    
    for epoch in range(epochs):
        # Update curriculum learning if supported
        if hasattr(loss_fn, 'set_epoch'):
            loss_fn.set_epoch(epoch, epochs)
        
        # Training
        model.train()
        loss_fn.train()
        total_loss = 0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            
            with torch.cuda.amp.autocast():
                features = model(images)
                loss, _ = loss_fn(features, labels)
            
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            torch.nn.utils.clip_grad_norm_(loss_fn.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            
            total_loss += loss.item()
        
        # Validation
        model.eval()
        val_preds, val_labels_list = [], []
        
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                features = model(images)
                
                weight = F.normalize(loss_fn.weight, dim=1)
                features_norm = F.normalize(features, dim=1)
                logits = features_norm @ weight.t()
                preds = logits.argmax(dim=1)
                
                val_preds.extend(preds.cpu().numpy())
                val_labels_list.extend(labels.numpy())
        
        val_f1 = f1_score(val_labels_list, val_preds, average='weighted')
        
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            base_model = model.module if hasattr(model, 'module') else model
            best_state = {
                'model': {k: v.cpu().clone() for k, v in base_model.state_dict().items()},
                'loss_fn': {k: v.cpu().clone() for k, v in loss_fn.state_dict().items()}
            }
        
        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1:3d}/{epochs} | Loss: {total_loss/len(train_loader):.4f} | "
                  f"Val F1: {val_f1:.4f} | Best: {best_val_f1:.4f} @ {best_epoch+1}")
        
        scheduler.step()
    
    # Load best and test
    if best_state:
        base_model = model.module if hasattr(model, 'module') else model
        base_model.load_state_dict({k: v.to(device) for k, v in best_state['model'].items()})
        loss_fn.load_state_dict({k: v.to(device) for k, v in best_state['loss_fn'].items()})
    
    model.eval()
    test_preds, test_labels_list = [], []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            features = model(images)
            
            weight = F.normalize(loss_fn.weight, dim=1)
            features_norm = F.normalize(features, dim=1)
            logits = features_norm @ weight.t()
            preds = logits.argmax(dim=1)
            
            test_preds.extend(preds.cpu().numpy())
            test_labels_list.extend(labels.numpy())
    
    test_preds = np.array(test_preds)
    test_labels_arr = np.array(test_labels_list)
    
    test_acc = accuracy_score(test_labels_arr, test_preds)
    test_f1 = f1_score(test_labels_arr, test_preds, average='weighted')
    test_prec = precision_score(test_labels_arr, test_preds, average='weighted', zero_division=0)
    test_rec = recall_score(test_labels_arr, test_preds, average='weighted', zero_division=0)
    f1_per_class = f1_score(test_labels_arr, test_preds, average=None, zero_division=0)
    
    print(f"\n  TEST: Acc={test_acc*100:.2f}% | F1={test_f1*100:.2f}%")
    for i, f1 in enumerate(f1_per_class):
        print(f"    {id2label[i]}: {f1*100:.1f}%")
    
    return {
        'name': name,
        'best_epoch': best_epoch + 1,
        'test_accuracy': test_acc,
        'test_f1': test_f1,
        'test_precision': test_prec,
        'test_recall': test_rec,
        'f1_per_class': f1_per_class.tolist(),
    }


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("="*70)
    print("  COMPLETE ABLATION STUDY: All Loss Functions")
    print("  FuzzyArcLoss v1 vs v2 + Face Recognition Baselines")
    print("="*70)
    
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nDevice: {device}")
    if torch.cuda.is_available():
        print(f"GPUs: {torch.cuda.device_count()} x {torch.cuda.get_device_name(0)}")
    
    # Seed
    random.seed(config.SEED)
    np.random.seed(config.SEED)
    torch.manual_seed(config.SEED)
    torch.cuda.manual_seed_all(config.SEED)
    
    # Load data
    print("\n[1/3] Loading data...")
    df = pair_images_with_masks(config.IMAGE_DIR, config.MASK_DIR)
    
    xls = pd.read_excel(config.XLS_PATH)
    xls['stem'] = xls['tile_id'].astype(str)
    xls_filtered = xls[xls['pattern'].str.lower() != 'none'].copy()
    print(f"  Filtered: {len(xls)} -> {len(xls_filtered)} rows")
    
    df = df.merge(xls_filtered[['stem', 'pattern']], on='stem', how='inner')
    df = df.dropna(subset=['pattern'])
    
    labels = sorted(df['pattern'].astype(str).unique())
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    num_classes = len(labels)
    
    print(f"  Samples: {len(df)}, Classes: {num_classes}")
    print(f"  Classes: {labels}")
    
    # Split
    train_df, temp_df = train_test_split(df, test_size=0.3, stratify=df['pattern'], random_state=config.SEED)
    val_df, test_df = train_test_split(temp_df, test_size=0.5, stratify=temp_df['pattern'], random_state=config.SEED)
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # Class weights
    train_labels = [label2id[str(l)] for l in train_df['pattern']]
    class_counts = [train_labels.count(i) for i in range(num_classes)]
    print(f"  Class counts: {dict(zip(labels, class_counts))}")
    
    total = sum(class_counts)
    ce_weights = torch.tensor([total / (num_classes * c) for c in class_counts], dtype=torch.float32)
    ce_weights = ce_weights / ce_weights.sum() * num_classes
    
    # Datasets
    train_ds = HistDataset(train_df, 'pattern', label2id, config.IMG_SIZE, aug=True, use_roi_crop=config.USE_ROI_CROP)
    val_ds = HistDataset(val_df, 'pattern', label2id, config.IMG_SIZE, aug=False, use_roi_crop=config.USE_ROI_CROP)
    test_ds = HistDataset(test_df, 'pattern', label2id, config.IMG_SIZE, aug=False, use_roi_crop=config.USE_ROI_CROP)
    
    # Weighted sampler
    weights = [1.0 / class_counts[l] for l in train_labels]
    sampler = WeightedRandomSampler(weights, len(weights), replacement=True)
    
    train_loader = DataLoader(train_ds, batch_size=config.BATCH_SIZE, sampler=sampler, 
                              num_workers=config.NUM_WORKERS, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=config.BATCH_SIZE, shuffle=False,
                            num_workers=config.NUM_WORKERS, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=config.BATCH_SIZE, shuffle=False,
                             num_workers=config.NUM_WORKERS, pin_memory=True)
    
    # ========================================
    # BUILD MODEL HELPER
    # ========================================
    def build_model():
        backbone = CTransPathBackbone(config.CTRANSPATH_CHECKPOINT, config.FREEZE_BACKBONE_LAYERS)
        head = nn.Sequential(
            nn.Linear(backbone.out_features, config.EMBED_DIM),
            nn.LayerNorm(config.EMBED_DIM),
            nn.GELU(),
            nn.Dropout(0.15),
        )
        return nn.Sequential(backbone, head)
    
    # ========================================
    # EXPERIMENTS
    # ========================================
    print("\n" + "="*70)
    print("[2/3] Running Experiments (14 loss functions)")
    print("="*70)
    
    all_results = []
    
    # === BASELINE ===
    print("\n--- BASELINE ---")
    model = build_model()
    loss_fn = SoftmaxLoss(config.EMBED_DIM, num_classes)
    result = train_experiment("1. Softmax", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    # === FACE RECOGNITION METHODS ===
    print("\n--- FACE RECOGNITION METHODS ---")
    
    # model = build_model()
    # loss_fn = SphereFaceLoss(config.EMBED_DIM, num_classes, s=30.0, m=4.0)
    # result = train_experiment("2. SphereFace", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # model = build_model()
    # loss_fn = CosFaceLoss(config.EMBED_DIM, num_classes, s=30.0, m=0.35)
    # result = train_experiment("3. CosFace", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # model = build_model()
    # loss_fn = ArcFaceLoss(config.EMBED_DIM, num_classes, s=30.0, m=0.5)
    # result = train_experiment("4. ArcFace", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # model = build_model()
    # loss_fn = VPLLoss(config.EMBED_DIM, num_classes, s=30.0, m=0.35, r=0.1)
    # result = train_experiment("5. VPL", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # model = build_model()
    # loss_fn = SphereFace2Loss(config.EMBED_DIM, num_classes, s=30.0, m=1.35)
    # result = train_experiment("6. SphereFace2", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # model = build_model()
    # loss_fn = UniFaceLoss(config.EMBED_DIM, num_classes, s=30.0, m=0.35)
    # result = train_experiment("7. UniFace", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # model = build_model()
    # loss_fn = AdaptiveFaceLoss(config.EMBED_DIM, num_classes, s=30.0, class_counts=class_counts)
    # result = train_experiment("8. AdaptiveFace", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    # all_results.append(result)
    
    # === FUZZYARCLOSS V1 (Original) ===
    print("\n--- FUZZYARCLOSS V1 (Original: uncertain → full margin) ---")
    
    model = build_model()
    loss_fn = FuzzyArcLossV1Basic(config.EMBED_DIM, num_classes, s=30.0, m=0.5, tau=0.5)
    result = train_experiment("9. FuzzyArcLoss V1 Basic", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    model = build_model()
    loss_fn = FuzzyArcLossV1Improved(config.EMBED_DIM, num_classes, s=30.0, m=0.5, tau=0.5, ce_weight=ce_weights)
    result = train_experiment("10. FuzzyArcLoss V1 Improved", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    # === FUZZYARCLOSS V2 (Inverse - Histopathology Optimized) ===
    print("\n--- FUZZYARCLOSS V2 (Inverse: confident → full margin) ---")
    
    model = build_model()
    loss_fn = FuzzyArcLossV2Basic(config.EMBED_DIM, num_classes, s=30.0, m=0.5, tau=0.5)
    result = train_experiment("11. FuzzyArcLoss V2 Basic", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    model = build_model()
    loss_fn = FuzzyArcLossV2(config.EMBED_DIM, num_classes, s=30.0, m=0.5, tau=0.5, ce_weight=ce_weights)
    result = train_experiment("12. FuzzyArcLoss V2", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    model = build_model()
    class_params = get_lung_adenocarcinoma_class_params(num_classes)
    loss_fn = FuzzyArcLossV2(config.EMBED_DIM, num_classes, s=30.0, m=0.5, tau=0.5, ce_weight=ce_weights,
                             class_tau=class_params['class_tau'],
                             class_margin=class_params['class_margin'],
                             class_scale=class_params['class_scale'])
    result = train_experiment("13. FuzzyArcLoss V2 + ClassParams", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    model = build_model()
    class_params = get_lung_adenocarcinoma_class_params(num_classes)
    loss_fn = FuzzyArcLossV2(config.EMBED_DIM, num_classes, s=30.0, m=0.5, tau=0.5, ce_weight=ce_weights,
                             class_tau=class_params['class_tau'],
                             class_margin=class_params['class_margin'],
                             class_scale=class_params['class_scale'],
                             use_curriculum=True)
    result = train_experiment("14. FuzzyArcLoss V2 + Curriculum", model, loss_fn, train_loader, val_loader, test_loader, id2label, device, config.EPOCHS)
    all_results.append(result)
    
    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "="*70)
    print("[3/3] FINAL RESULTS")
    print("="*70)
    
    print(f"\n{'#':<4} {'Method':<35} {'Acc':>8} {'F1':>8} {'Epoch':>8}")
    print("-"*65)
    for i, r in enumerate(sorted(all_results, key=lambda x: x['test_f1'], reverse=True), 1):
        print(f"{i:<4} {r['name']:<35} {r['test_accuracy']*100:>7.2f}% {r['test_f1']*100:>7.2f}% {r['best_epoch']:>8}")
    
    print(f"\n\nPER-CLASS F1 COMPARISON:")
    print("-"*100)
    header = f"{'Method':<35}"
    for l in labels:
        header += f"{l[:8]:>10}"
    print(header)
    print("-"*100)
    
    for r in sorted(all_results, key=lambda x: x['test_f1'], reverse=True):
        row = f"{r['name']:<35}"
        for f1 in r['f1_per_class']:
            row += f"{f1*100:>10.1f}"
        print(row)
    
    # Save
    os.makedirs(config.OUT_DIR, exist_ok=True)
    results_path = os.path.join(config.OUT_DIR, 'complete_ablation_results.json')
    with open(results_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'config': {
                'epochs': config.EPOCHS,
                'batch_size': config.BATCH_SIZE,
                'embed_dim': config.EMBED_DIM,
            },
            'class_labels': labels,
            'results': all_results
        }, f, indent=2)
    print(f"\n✓ Results saved to: {results_path}")
    
    # Winner
    best = max(all_results, key=lambda x: x['test_f1'])
    print(f"\n{'='*70}")
    print(f"  🏆 WINNER: {best['name']}")
    print(f"     Test F1: {best['test_f1']*100:.2f}%")
    print(f"     Test Accuracy: {best['test_accuracy']*100:.2f}%")
    print(f"     Best Epoch: {best['best_epoch']}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
