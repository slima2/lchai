#!/usr/bin/env python3
# All 6 GPUs available — NCCL verified working after clearing stale kernels
import os
"""
SLIMA Ablation Study: Loss Function Comparison for Histopathology Classification
================================================================================

Version 12 - February 2026
Updated with Optuna-optimized hyperparameters for FuzzyArcLoss V3 + SubCenters (CTransPath).
All losses use CTransPath backbone with differential LR (backbone vs head).

This script implements a comprehensive ablation study comparing all FuzzyArcLoss 
variants against loss functions mentioned in the paper "FuzzyArcLoss: Dynamic margin 
adjustment for robust recognition across domains" (Expert Systems with Applications, 2025).

Loss Functions Compared:
========================
BASELINE:
1. Softmax - Standard cross-entropy

FACE RECOGNITION (from paper Table 1):
2. SphereFace (A-Softmax) - Multiplicative angular margin
3. CosFace (AM-Softmax) - Additive cosine margin
4. ArcFace - Additive angular margin
5. VPL - Virtual prototypes with margin control
6. SphereFace2 - Improved multiplicative angular margin
7. UniFace - Unified feature normalization
8. AdaptiveFace - Dynamic margin based on class difficulty

FUZZYARCLOSS VARIANTS:
9. FuzzyArcLoss V1 Basic - Original paper version (uncertain → full margin)
10. FuzzyArcLoss V1 Improved - V1 + LabelSmoothing + Focal
11. FuzzyArcLoss V2 Basic - Inverse logic (confident → full margin)
12. FuzzyArcLoss V2 - V2 + LabelSmoothing + Focal
13. FuzzyArcLoss V2 + ClassParams - V2 with class-specific τ/m/s (BEST: 65.09%)
14. FuzzyArcLoss V3 + Entropy - Non-self-referential uncertainty
15. FuzzyArcLoss V3 + TopGap - Top-1 vs Top-2 gap uncertainty
16. FuzzyArcLoss V3 + SubCenters - K prototypes per class (K=3)
17. FuzzyArcLoss V2.5 - V2 inverse + V3 sub-centers
18. FuzzyArcLoss V2.5 + ClassParams - V2.5 with class-specific parameters

EXECUTION ORDER (Best performers first based on ablation studies):
1. FuzzyArcLoss V2 + ClassParams (65.09% F1)
2. FuzzyArcLoss V3 + SubCenters (61.93% F1)
3. Softmax baseline
4. FuzzyArcLoss V1 Improved
5. FuzzyArcLoss V2.5 + SubCenters
6. All remaining methods

Optimizations for 90% F1 Target:
- CTransPath backbone (pathology-specific)
- Stain augmentation (Macenko-style color jitter)
- MixUp and CutMix augmentation
- Strong augmentation pipeline
- Label smoothing + Focal loss combination
- Weighted sampling for class imbalance
- Gradient accumulation for effective larger batch
- Cosine annealing with warmup

Author: Servio F. Lima
Based on: FuzzyArcLoss paper (Expert Systems with Applications, 2025)

BEST HYPERPARAMETERS FOR FUZZYARCLOSS V3 WITH SUBCENTERS
Trial 9 finished with value: 0.9126787310282733 and parameters: {'S_SCALE': 39.001786002638916, 'M_MARGIN': 0.5573158242327586, 'TAU': 0.4542757061233031, 'NUM_SUBCENTERS': 4, 'BACKBONE_LR': 8.425425945372205e-05, 'HEAD_LR_MULT': 7.023202698292164, 'FREEZE_LAYERS': 2, 'EMBED_DIM': 512, 'WARMUP_EPOCHS': 6}. Best is trial 9 with value: 0.9126787310282733.

"""

import os
import sys
import math
import json
import random
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
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

# Optuna for hyperparameter optimization
try:
    import optuna
    from optuna.trial import Trial
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("[WARNING] Optuna not installed. Run: pip install optuna")

# Accelerate (not used for single-GPU training to avoid NCCL timeout issues)
HAS_ACCELERATE = False

# timm for models
try:
    import timm
    HAS_TIMM = True
except ImportError:
    HAS_TIMM = False
    print("[WARNING] timm not installed")

# torchvision
import torchvision.transforms as T
from torchvision import models

warnings.filterwarnings("ignore")


# ==============================================================================
# CONFIGURATION
# ==============================================================================

@dataclass
class AblationConfig:
    """Configuration for ablation study."""
    
    # Data paths
    ROOT_DIR: str = "/home/rapids/notebooks/slima/Zenodo_Anorak_original"
    IMAGE_DIR: str = None
    MASK_DIR: str = None
    XLS_PATH: str = "/home/rapids/notebooks/slima/overlay_index ver 9 nov 2025.xlsx"
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/ablation_study_v12_optuna"
    
    # Model
    CTRANSPATH_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/ctranspath.pth"
    EMBED_DIM: int = 512           # Optuna winner for CTransPath
    FREEZE_BACKBONE_LAYERS: int = 2 # Optuna winner
    
    # Training - differential LR (Optuna-optimized for CTransPath)
    EPOCHS: int = 150
    BATCH_SIZE: int = 8            # per-GPU; effective = 8 * 6 = 48 with DataParallel
    LR: float = 8.425425945372205e-05            # backbone LR (Optuna winner)
    LR_HEAD: float = 5.917e-4       # head/loss LR = LR * 11.76 (Optuna winner)
    HEAD_LR_MULT: float = 7.023202698292164    # head LR multiplier
    WEIGHT_DECAY: float = 1e-4
    WARMUP_EPOCHS: int = 6         # Optuna winner
    
    # Image
    IMG_SIZE: int = 224
    
    # ROI settings
    USE_ROI_CROP: bool = True
    ROI_PADDING: int = 24
    MASK_THRESH: float = 0.5
    
    # Data splits
    VAL_SIZE: float = 0.15
    TEST_SIZE: float = 0.15
    SEED: int = 42
    
    # Distributed
    NUM_WORKERS: int = 0
    MIXED_PRECISION: str = "fp16"
    
    # Augmentation (Enhanced for 90% target)
    USE_CUTMIX: bool = True
    CUTMIX_PROB: float = 0.3
    USE_MIXUP: bool = True
    MIXUP_PROB: float = 0.3
    MIXUP_ALPHA: float = 0.4
    USE_STAIN_AUG: bool = True
    STAIN_AUG_PROB: float = 0.5
    
    # Class weights
    USE_WEIGHTED_SAMPLER: bool = True
    
    # Optuna
    OPTUNA_TRIALS: int = 50
    OPTUNA_TIMEOUT: int = 7200  # 2 hours max
    
    # Print frequency
    PRINT_FREQ: int = 10  # Print every N epochs
    
    def __post_init__(self):
        if self.IMAGE_DIR is None:
            self.IMAGE_DIR = f"{self.ROOT_DIR}/image"
        if self.MASK_DIR is None:
            self.MASK_DIR = f"{self.ROOT_DIR}/mask"


config = AblationConfig()


# ==============================================================================
# LOSS FUNCTIONS FROM THE PAPER (ORIGINAL)
# ==============================================================================

class SoftmaxLoss(nn.Module):
    """
    Standard Softmax Loss (Baseline)
    L_Softmax = -1/N * sum(log(exp(W_yi^T * x_i + b_yi) / sum(exp(W_j^T * x_i + b_j))))
    """
    def __init__(self, in_features: int, out_features: int, s: float = 1.0):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        self.ce = nn.CrossEntropyLoss()
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize features and weights
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Compute logits
        logits = self.s * F.linear(features_norm, weight_norm)
        loss = self.ce(logits, labels)
        
        return loss, logits


class SphereFaceLoss(nn.Module):
    """
    SphereFace (A-Softmax) Loss - Liu et al., 2017
    L_SphereFace = -1/N * sum(log(exp(s*cos(m*θ_yi)) / (exp(s*cos(m*θ_yi)) + sum(exp(s*cos(θ_j))))))
    
    Uses multiplicative angular margin on the angle.
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 4.0):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m  # Multiplicative margin (integer, typically 1, 2, or 4)
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # For numerical stability
        self.iter = 0
        self.base = 1000.0
        self.gamma = 0.12
        self.power = 1
        self.lambda_min = 5.0
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        cos_theta = cos_theta.clamp(-1, 1)
        
        # Get cos(m*theta) using Chebyshev polynomials approximation
        cos_m_theta = self._cos_m_theta(cos_theta, self.m)
        
        # Lambda for annealing
        self.iter += 1
        lamb = max(self.lambda_min, self.base * (1 + self.gamma * self.iter) ** (-self.power))
        
        # One-hot encoding
        one_hot = torch.zeros_like(cos_theta)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        # Apply margin only to target class with annealing
        output = self.s * (one_hot * ((lamb * cos_theta + cos_m_theta) / (1 + lamb)) + 
                          (1 - one_hot) * cos_theta)
        
        loss = F.cross_entropy(output, labels)
        return loss, output
    
    def _cos_m_theta(self, cos_theta: torch.Tensor, m: int) -> torch.Tensor:
        """Compute cos(m*theta) using recursion."""
        if m == 1:
            return cos_theta
        elif m == 2:
            return 2 * cos_theta ** 2 - 1
        elif m == 4:
            cos_2theta = 2 * cos_theta ** 2 - 1
            return 2 * cos_2theta ** 2 - 1
        else:
            # General case using arccos (less efficient but general)
            theta = torch.acos(cos_theta.clamp(-1 + 1e-7, 1 - 1e-7))
            return torch.cos(m * theta)


class CosFaceLoss(nn.Module):
    """
    CosFace (AM-Softmax) Loss - Wang et al., 2018
    L_CosFace = -1/N * sum(log(exp(s*(cos(θ_yi) - m)) / (exp(s*(cos(θ_yi) - m)) + sum(exp(s*cos(θ_j))))))
    
    Uses additive cosine margin (subtracts m from cosine).
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.35):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m  # Additive cosine margin
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        
        # Subtract margin from target class cosine
        one_hot = torch.zeros_like(cos_theta)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        output = self.s * (cos_theta - one_hot * self.m)
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class ArcFaceLoss(nn.Module):
    """
    ArcFace Loss - Deng et al., 2019
    L_ArcFace = -1/N * sum(log(exp(s*cos(θ_yi + m)) / (exp(s*cos(θ_yi + m)) + sum(exp(s*cos(θ_j))))))
    
    Uses additive angular margin (adds m to angle, not cosine).
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.5):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Precompute constants
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        cos_theta = cos_theta.clamp(-1 + 1e-7, 1 - 1e-7)
        
        # sin(θ) = sqrt(1 - cos²(θ))
        sin_theta = torch.sqrt(1.0 - cos_theta ** 2)
        
        # cos(θ + m) = cos(θ)cos(m) - sin(θ)sin(m)
        phi = cos_theta * self.cos_m - sin_theta * self.sin_m
        
        # Handle edge case
        phi = torch.where(cos_theta > self.th, phi, cos_theta - self.mm)
        
        # One-hot encoding
        one_hot = torch.zeros_like(cos_theta)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        output = self.s * (one_hot * phi + (1 - one_hot) * cos_theta)
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class VPLLoss(nn.Module):
    """
    VPL (Virtual Prototype Learning) Loss - Johnston & Yang, 2023
    
    Creates virtual prototypes around class centers to improve generalization.
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, 
                 m: float = 0.35, r: float = 0.1):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.r = r  # Radius for virtual prototypes
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Add noise to weights during training (virtual prototypes)
        if self.training:
            noise = torch.randn_like(weight_norm) * self.r
            weight_norm = F.normalize(weight_norm + noise, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        
        # CosFace-style margin
        one_hot = torch.zeros_like(cos_theta)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        output = self.s * (cos_theta - one_hot * self.m)
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class SphereFace2Loss(nn.Module):
    """
    SphereFace2 Loss - Chen et al., 2023
    
    Improved multiplicative angular margin with better convergence.
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 1.35):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        cos_theta = cos_theta.clamp(-1 + 1e-7, 1 - 1e-7)
        
        # theta
        theta = torch.acos(cos_theta)
        
        # cos(m * theta) for target class
        cos_m_theta = torch.cos(self.m * theta)
        
        # One-hot encoding
        one_hot = torch.zeros_like(cos_theta)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        # Apply multiplicative margin only to target class
        output = self.s * (one_hot * cos_m_theta + (1 - one_hot) * cos_theta)
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class UniFaceLoss(nn.Module):
    """
    UniFace Loss - Li et al., 2023
    
    Unified feature normalization with consistent margin across all classes.
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, m: float = 0.35):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Learnable temperature per class
        self.class_temp = nn.Parameter(torch.ones(out_features))
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        cos_theta = cos_theta.clamp(-1, 1)
        
        # Apply uniform margin to ALL classes (not just target)
        # This normalizes the feature space
        output = self.s * (cos_theta - self.m) * F.softplus(self.class_temp)
        
        loss = F.cross_entropy(output, labels)
        return loss, output


class AdaptiveFaceLoss(nn.Module):
    """
    AdaptiveFace Loss - Smith et al., 2023
    
    Dynamically adjusts margins based on class difficulty (sample count).
    m_yi = λ * log(1 + e^(-γ * n_yi))
    """
    def __init__(self, in_features: int, out_features: int, s: float = 30.0, 
                 lambda_: float = 0.5, gamma: float = 0.1, class_counts: List[int] = None):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.lambda_ = lambda_
        self.gamma = gamma
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Compute class-specific margins based on sample counts
        if class_counts is None:
            class_counts = [100] * out_features  # Default
        
        # m_yi = λ * log(1 + e^(-γ * n_yi))
        margins = []
        for n in class_counts:
            m = lambda_ * math.log(1 + math.exp(-gamma * n))
            margins.append(m)
        
        self.register_buffer('margins', torch.tensor(margins))
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Normalize
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # Cosine similarity
        cos_theta = F.linear(features_norm, weight_norm)
        cos_theta = cos_theta.clamp(-1 + 1e-7, 1 - 1e-7)
        
        # Get margin for each sample based on its label
        sample_margins = self.margins[labels]  # (B,)
        
        # sin(θ) = sqrt(1 - cos²(θ))
        sin_theta = torch.sqrt(1.0 - cos_theta ** 2 + 1e-7)
        
        # For each sample, apply its specific margin to the target class
        batch_size = features.size(0)
        cos_theta_m = cos_theta.clone()
        
        for i in range(batch_size):
            m = sample_margins[i].item()
            cos_m = math.cos(m)
            sin_m = math.sin(m)
            
            target_cos = cos_theta[i, labels[i]]
            target_sin = sin_theta[i, labels[i]]
            
            # cos(θ + m) — cast to match dtype for fp16 safety
            val = target_cos * cos_m - target_sin * sin_m
            cos_theta_m[i, labels[i]] = val.to(cos_theta_m.dtype)
        
        output = self.s * cos_theta_m
        
        loss = F.cross_entropy(output, labels)
        return loss, output


# ==============================================================================
# FUZZYARCLOSS V1 (ORIGINAL)
# ==============================================================================

class FuzzyArcMarginProductV1(nn.Module):
    """
    FuzzyArcMarginProduct V1 - Original (Paper Version)
    Lima et al., 2025 (Expert Systems with Applications)
    
    Logic: Uncertain samples → FULL margin, Confident samples → REDUCED margin
    
    μ = |cos(θ)| if |cos(θ)| >= τ (confident → reduced margin)
    μ = 1.0 otherwise (uncertain → full margin)
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.easy_margin = easy_margin
        
        # Learnable class centers (weights)
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Precompute for numerical stability
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        # 1. Normalize features and weights to unit sphere
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        # 2. Compute cosine similarity (cos θ)
        cosine = F.linear(features_norm, weight_norm)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        # 3. Compute sin(θ) = sqrt(1 - cos²(θ))
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        
        # 4. Compute cos(θ + m) = cos(θ)cos(m) - sin(θ)sin(m)
        phi = cosine * self.cos_m - sine * self.sin_m
        
        # 5. Handle edge case when θ + m > π (numerical stability)
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        # 6. Get target cosine values for fuzzy membership
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        # 7. V1 Fuzzy membership: uncertain → full margin, confident → reduced
        # μ = |cos(θ)| if |cos(θ)| >= τ, else 1
        mu = torch.where(
            torch.abs(target_cosine) >= self.tau,
            torch.abs(target_cosine),  # Confident: μ = |cos| (reduced margin)
            torch.ones_like(target_cosine)  # Uncertain: μ = 1 (full margin)
        )
        mu = mu.clamp(0, 1)
        
        # 8. Create one-hot encoding for target class
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        # 9. Apply fuzzy-weighted margin
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        # 10. Scale by s
        output = self.s * output
        
        return output


# ==============================================================================
# FUZZYARCLOSS V2 (INVERSE LOGIC - BETTER FOR HISTOPATHOLOGY)
# ==============================================================================

class FuzzyArcMarginProductV2(nn.Module):
    """
    FuzzyArcMarginProduct V2 - Inverse Logic
    
    Key insight: For histopathology, we want:
    - Confident samples → FULL margin (prevent overconfidence on easy classes)
    - Uncertain samples → REDUCED margin (be gentle with ambiguous boundaries)
    
    This is OPPOSITE to V1 and works better for histopathology (65.09% vs 61.98%)
    
    μ = 0.8 + 0.2*|cos(θ)| if |cos(θ)| >= τ (confident: full margin 0.8-1.0)
    μ = 0.3 + 0.4*|cos(θ)| otherwise (uncertain: reduced margin 0.3-0.7)
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.easy_margin = easy_margin
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        cosine = F.linear(features_norm, weight_norm)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        # V2: INVERSE fuzzy membership - confident → full margin
        mu = torch.where(
            torch.abs(target_cosine) >= self.tau,
            0.8 + 0.2 * torch.abs(target_cosine),  # Confident: μ = 0.8-1.0 (FULL margin)
            0.3 + 0.4 * torch.abs(target_cosine)   # Uncertain: μ = 0.3-0.7 (reduced margin)
        )
        mu = mu.clamp(0, 1)
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        output = self.s * output
        
        return output


class FuzzyArcMarginProductV2ClassParams(nn.Module):
    """
    FuzzyArcMarginProduct V2 with Class-Specific Parameters
    
    Each class has its own τ, margin m, and scale s.
    This allows tailoring regularization to class difficulty.
    
    Best configuration from ablation (65.09% F1):
    - Hard classes (acinar, micropapillary): gentle τ=0.35, m=0.35
    - Easy classes (solid, papillary): aggressive τ=0.65, m=0.60
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 class_tau: List[float] = None,
                 class_margin: List[float] = None,
                 class_scale: List[float] = None,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.easy_margin = easy_margin
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        # Class-specific parameters
        # Default: optimized for lung adenocarcinoma (6 classes)
        # Order: [acinar, lepidic, micropapillary, mucinous, papillary, solid]
        if class_tau is None:
            class_tau = [0.35, 0.45, 0.35, 0.50, 0.60, 0.65]
        if class_margin is None:
            class_margin = [0.35, 0.45, 0.35, 0.50, 0.55, 0.60]
        if class_scale is None:
            class_scale = [25.0, 28.0, 25.0, 30.0, 32.0, 35.0]
        
        self.register_buffer('class_tau', torch.tensor(class_tau))
        self.register_buffer('class_margin', torch.tensor(class_margin))
        self.register_buffer('class_scale', torch.tensor(class_scale))
        
    # def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
    #     features_norm = F.normalize(features, dim=1)
    #     weight_norm = F.normalize(self.weight, dim=1)
        
    #     cosine = F.linear(features_norm, weight_norm)
    #     cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
    #     sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        
    #     batch_size = features.size(0)
    #     target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
    #     # Get class-specific parameters for each sample
    #     sample_tau = self.class_tau[labels]
    #     sample_margin = self.class_margin[labels]
    #     sample_scale = self.class_scale[labels]
        
    #     # Compute cos(θ + m) with class-specific margin
    #     cos_m = torch.cos(sample_margin)
    #     sin_m = torch.sin(sample_margin)
        
    #     target_sine = sine[torch.arange(batch_size, device=features.device), labels]
    #     phi_target = target_cosine * cos_m - target_sine * sin_m
        
    #     # V2 inverse fuzzy membership with class-specific τ
    #     mu = torch.where(
    #         torch.abs(target_cosine) >= sample_tau,
    #         0.8 + 0.2 * torch.abs(target_cosine),
    #         0.3 + 0.4 * torch.abs(target_cosine)
    #     )
    #     mu = mu.clamp(0, 1)
        
    #     # Apply fuzzy-weighted margin for target class
    #     target_logits = mu * phi_target + (1 - mu) * target_cosine
        
    #     # Build output
    #     output = cosine.clone()
    #     output[torch.arange(batch_size, device=features.device), labels] = target_logits
        
    #     # Apply class-specific scale
    #     output = output * sample_scale.unsqueeze(1)
        
    #     return output

    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        cosine = F.linear(features_norm, weight_norm)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        # Get class-specific parameters for each sample
        sample_tau = self.class_tau[labels]
        sample_margin = self.class_margin[labels]
        sample_scale = self.class_scale[labels]
        
        # Compute cos(θ + m) with class-specific margin - CAST TO MATCH DTYPE
        cos_m = torch.cos(sample_margin).to(cosine.dtype)
        sin_m = torch.sin(sample_margin).to(cosine.dtype)
        
        target_sine = sine[torch.arange(batch_size, device=features.device), labels]
        phi_target = target_cosine * cos_m - target_sine * sin_m
        
        # V2 inverse fuzzy membership with class-specific τ
        mu = torch.where(
            torch.abs(target_cosine) >= sample_tau.to(cosine.dtype),
            0.8 + 0.2 * torch.abs(target_cosine),
            0.3 + 0.4 * torch.abs(target_cosine)
        )
        mu = mu.clamp(0, 1)
        
        # Apply fuzzy-weighted margin for target class
        target_logits = mu * phi_target + (1 - mu) * target_cosine
        
        # Build output - ENSURE DTYPE MATCHES
        output = cosine.clone()
        output[torch.arange(batch_size, device=features.device), labels] = target_logits.to(output.dtype)
        
        # Apply class-specific scale
        output = output * sample_scale.to(output.dtype).unsqueeze(1)
        
        return output
# ==============================================================================
# FUZZYARCLOSS V3 (NON-SELF-REFERENTIAL UNCERTAINTY)
# ==============================================================================

class FuzzyArcMarginProductV3Entropy(nn.Module):
    """
    FuzzyArcMarginProduct V3 - Entropy-Based Uncertainty
    
    Key insight: V2's cosine-based μ is self-referential (weak embeddings → weak 
    fuzziness → weak learning signal). V3 breaks this with entropy-based uncertainty.
    
    μ = 1.0 - 0.7 * (H / H_max)
    where H = -sum(p * log(p)) is the entropy of class probabilities
    
    Note: In ablation, this UNDERPERFORMED V2 cosine-based (55.93% vs 65.09%)
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.easy_margin = easy_margin
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
        # Max entropy for normalization
        self.max_entropy = math.log(out_features)
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        cosine = F.linear(features_norm, weight_norm)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        # Compute entropy-based uncertainty
        probs = F.softmax(cosine * self.s, dim=1)
        entropy = -torch.sum(probs * torch.log(probs + 1e-8), dim=1)
        normalized_entropy = entropy / self.max_entropy
        
        # V3 Entropy: high entropy → low μ → reduced margin
        mu = 1.0 - 0.7 * normalized_entropy
        mu = mu.clamp(0.3, 1.0)
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        output = self.s * output
        
        return output


class FuzzyArcMarginProductV3TopGap(nn.Module):
    """
    FuzzyArcMarginProduct V3 - Top-Gap Uncertainty
    
    Uses the gap between top-1 and top-2 predictions as confidence measure.
    
    gap = (cos_top1 - cos_top2) / |cos_top1|
    μ = 0.3 + 0.7 * gap
    
    Large gap → confident → full margin
    Small gap → uncertain → reduced margin
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.easy_margin = easy_margin
        
        self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
        nn.init.xavier_uniform_(self.weight)
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=1)
        
        cosine = F.linear(features_norm, weight_norm)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        # Compute top-gap uncertainty
        sorted_cosine, _ = torch.sort(cosine, dim=1, descending=True)
        top1 = sorted_cosine[:, 0]
        top2 = sorted_cosine[:, 1]
        
        gap = (top1 - top2) / (torch.abs(top1) + 1e-8)
        gap = gap.clamp(0, 1)
        
        # V3 TopGap: large gap → confident → full margin
        mu = 0.3 + 0.7 * gap
        mu = mu.clamp(0.3, 1.0)
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        output = self.s * output
        
        return output


class FuzzyArcMarginProductV3SubCenters(nn.Module):
    """
    FuzzyArcMarginProduct V3 with Sub-Centers
    
    Each class has K prototype vectors to capture multi-modal patterns.
    This is especially useful for histopathology where classes like acinar
    and lepidic have multiple visual subtypes.
    
    cosine(c) = max_k { f · w_{c,k} / (||f|| ||w_{c,k}||) }
    
    Ablation showed +6% improvement with sub-centers (55.93% → 61.93%)
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 num_subcenters: int = 3,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.num_subcenters = num_subcenters
        self.easy_margin = easy_margin
        
        # Sub-center weights: (num_classes, K, embed_dim)
        self.weight = nn.Parameter(torch.FloatTensor(out_features, num_subcenters, in_features))
        nn.init.xavier_uniform_(self.weight.view(-1, in_features))
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)  # (B, D)
        
        # Normalize each sub-center
        weight_norm = F.normalize(self.weight, dim=2)  # (C, K, D)
        
        # Compute cosine with all sub-centers: (B, C, K)
        # einsum: batch features × class subcenter weights
        cosine_all = torch.einsum('bd,ckd->bck', features_norm, weight_norm)
        
        # Take max over sub-centers for each class: (B, C)
        cosine, best_k = cosine_all.max(dim=2)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        # V2-style inverse fuzzy membership (proven better than entropy)
        mu = torch.where(
            torch.abs(target_cosine) >= self.tau,
            0.8 + 0.2 * torch.abs(target_cosine),
            0.3 + 0.4 * torch.abs(target_cosine)
        )
        mu = mu.clamp(0, 1)
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        output = self.s * output
        
        return output


# ==============================================================================
# FUZZYARCLOSS V2.5 (V2 INVERSE + V3 SUB-CENTERS)
# ==============================================================================

class FuzzyArcMarginProductV25(nn.Module):
    """
    FuzzyArcMarginProduct V2.5 - Best of V2 + V3
    
    Combines:
    - V2's inverse cosine uncertainty (PROVEN better than entropy)
    - V3's sub-centers (K prototypes per class for multi-modal patterns)
    
    This is designed to combine the best aspects of both approaches.
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 num_subcenters: int = 3,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.num_subcenters = num_subcenters
        self.easy_margin = easy_margin
        
        # Sub-center weights: (num_classes, K, embed_dim)
        self.weight = nn.Parameter(torch.FloatTensor(out_features, num_subcenters, in_features))
        nn.init.xavier_uniform_(self.weight.view(-1, in_features))
        
        self.cos_m = math.cos(m)
        self.sin_m = math.sin(m)
        self.th = math.cos(math.pi - m)
        self.mm = math.sin(math.pi - m) * m
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=2)
        
        # Cosine with all sub-centers
        cosine_all = torch.einsum('bd,ckd->bck', features_norm, weight_norm)
        cosine, best_k = cosine_all.max(dim=2)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        phi = cosine * self.cos_m - sine * self.sin_m
        
        if self.easy_margin:
            phi = torch.where(cosine > 0, phi, cosine)
        else:
            phi = torch.where(cosine > self.th, phi, cosine - self.mm)
        
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        # V2 inverse fuzzy membership
        mu = torch.where(
            torch.abs(target_cosine) >= self.tau,
            0.8 + 0.2 * torch.abs(target_cosine),
            0.3 + 0.4 * torch.abs(target_cosine)
        )
        mu = mu.clamp(0, 1)
        
        one_hot = torch.zeros_like(cosine)
        one_hot.scatter_(1, labels.view(-1, 1), 1)
        
        mu_expanded = mu.unsqueeze(1)
        target_logits = mu_expanded * phi + (1 - mu_expanded) * cosine
        output = one_hot * target_logits + (1 - one_hot) * cosine
        
        output = self.s * output
        
        return output


class FuzzyArcMarginProductV25ClassParams(nn.Module):
    """
    FuzzyArcMarginProduct V2.5 with Class-Specific Parameters
    
    Combines V2.5 sub-centers with class-specific τ, margin, and scale.
    
    CAUTION: In ablation, miscalibrated class params caused lepidic to collapse
    from 51.6% to 13.3%. Use with care and proper validation.
    """
    def __init__(self, in_features: int, out_features: int, 
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 num_subcenters: int = 3,
                 class_tau: List[float] = None,
                 class_margin: List[float] = None,
                 class_scale: List[float] = None,
                 easy_margin: bool = False):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.s = s
        self.m = m
        self.tau = tau
        self.num_subcenters = num_subcenters
        self.easy_margin = easy_margin
        
        # Sub-center weights
        self.weight = nn.Parameter(torch.FloatTensor(out_features, num_subcenters, in_features))
        nn.init.xavier_uniform_(self.weight.view(-1, in_features))
        
        # Class-specific parameters (INVERTED: minority classes get GENTLE params)
        if class_tau is None:
            # [acinar, lepidic, micropapillary, mucinous, papillary, solid]
            # Minority classes (lepidic=59, mucinous=61) get LOW tau/margin
            class_tau = [0.45, 0.30, 0.45, 0.30, 0.40, 0.55]
        if class_margin is None:
            class_margin = [0.40, 0.25, 0.40, 0.25, 0.35, 0.50]
        if class_scale is None:
            class_scale = [28.0, 22.0, 28.0, 22.0, 26.0, 32.0]
        
        self.register_buffer('class_tau', torch.tensor(class_tau))
        self.register_buffer('class_margin', torch.tensor(class_margin))
        self.register_buffer('class_scale', torch.tensor(class_scale))
        
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        features_norm = F.normalize(features, dim=1)
        weight_norm = F.normalize(self.weight, dim=2)
        
        cosine_all = torch.einsum('bd,ckd->bck', features_norm, weight_norm)
        cosine, best_k = cosine_all.max(dim=2)
        cosine = cosine.clamp(-1 + 1e-7, 1 - 1e-7)
        
        sine = torch.sqrt(1.0 - cosine ** 2 + 1e-7)
        
        batch_size = features.size(0)
        target_cosine = cosine[torch.arange(batch_size, device=features.device), labels]
        
        sample_tau = self.class_tau[labels]
        sample_margin = self.class_margin[labels]
        sample_scale = self.class_scale[labels]
        
        cos_m = torch.cos(sample_margin).to(cosine.dtype)
        sin_m = torch.sin(sample_margin).to(cosine.dtype)
        
        target_sine = sine[torch.arange(batch_size, device=features.device), labels]
        phi_target = target_cosine * cos_m - target_sine * sin_m
        
        mu = torch.where(
            torch.abs(target_cosine) >= sample_tau.to(cosine.dtype),
            0.8 + 0.2 * torch.abs(target_cosine),
            0.3 + 0.4 * torch.abs(target_cosine)
        )
        mu = mu.clamp(0, 1)
        
        target_logits = mu * phi_target + (1 - mu) * target_cosine
        
        output = cosine.clone()
        output[torch.arange(batch_size, device=features.device), labels] = target_logits.to(output.dtype)
        output = output * sample_scale.to(output.dtype).unsqueeze(1)
        
        return output


# ==============================================================================
# AUXILIARY LOSS COMPONENTS
# ==============================================================================

class LabelSmoothingCrossEntropy(nn.Module):
    """
    Label Smoothing Cross Entropy Loss
    
    Instead of hard labels [0, 0, 1, 0, 0, 0], uses soft labels:
    [0.01, 0.01, 0.95, 0.01, 0.01, 0.01] with smoothing=0.05
    """
    def __init__(self, smoothing: float = 0.05, weight: torch.Tensor = None):
        super().__init__()
        self.smoothing = smoothing
        self.weight = weight
        
    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        n_classes = pred.size(1)
        
        smooth_labels = torch.full_like(pred, self.smoothing / (n_classes - 1))
        smooth_labels.scatter_(1, target.unsqueeze(1), 1 - self.smoothing)
        
        log_probs = F.log_softmax(pred, dim=1)
        
        if self.weight is not None:
            weight = self.weight.to(pred.device)
            sample_weights = weight[target]
            loss = -(smooth_labels * log_probs).sum(dim=1)
            loss = (loss * sample_weights).mean()
        else:
            loss = -(smooth_labels * log_probs).sum(dim=1).mean()
        
        return loss


class FocalLoss(nn.Module):
    """
    Focal Loss for handling hard examples
    Lin et al., 2017 - "Focal Loss for Dense Object Detection"
    
    Formula: FL = -α(1-p)^γ * log(p)
    """
    def __init__(self, alpha: float = 1.0, gamma: float = 2.0, 
                 weight: torch.Tensor = None, reduction: str = 'mean'):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.weight = weight
        self.reduction = reduction
    
    def forward(self, inputs: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        weight = self.weight.to(inputs.device) if self.weight is not None else None
        
        ce_loss = F.cross_entropy(inputs, targets, weight=weight, reduction='none')
        pt = torch.exp(-ce_loss)
        focal_weight = (1 - pt) ** self.gamma
        focal_loss = self.alpha * focal_weight * ce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        return focal_loss


# ==============================================================================
# COMPLETE FUZZYARCLOSS WRAPPERS
# ==============================================================================

class FuzzyArcLossV1Basic(nn.Module):
    """FuzzyArcLoss V1 Basic - Paper version with CE only."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5):
        super().__init__()
        self.head = FuzzyArcMarginProductV1(in_features, out_features, s=s, m=m, tau=tau)
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        loss = F.cross_entropy(logits, labels)
        return loss, logits


class FuzzyArcLossV1Improved(nn.Module):
    """FuzzyArcLoss V1 Improved - V1 + LabelSmoothing + Focal."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 label_smoothing: float = 0.05, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV1(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV2Basic(nn.Module):
    """FuzzyArcLoss V2 Basic - Inverse logic with CE only."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5):
        super().__init__()
        self.head = FuzzyArcMarginProductV2(in_features, out_features, s=s, m=m, tau=tau)
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        loss = F.cross_entropy(logits, labels)
        return loss, logits


class FuzzyArcLossV2(nn.Module):
    """FuzzyArcLoss V2 - Inverse logic + LabelSmoothing + Focal."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV2(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV2ClassParams(nn.Module):
    """FuzzyArcLoss V2 + ClassParams - BEST PERFORMER (65.09% F1)."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 class_tau: List[float] = None,
                 class_margin: List[float] = None,
                 class_scale: List[float] = None,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV2ClassParams(
            in_features, out_features, s=s, m=m, tau=tau,
            class_tau=class_tau, class_margin=class_margin, class_scale=class_scale
        )
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV3Entropy(nn.Module):
    """FuzzyArcLoss V3 Entropy - Non-self-referential uncertainty."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV3Entropy(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV3TopGap(nn.Module):
    """FuzzyArcLoss V3 TopGap - Gap-based uncertainty."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV3TopGap(in_features, out_features, s=s, m=m, tau=tau)
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV3SubCenters(nn.Module):
    """FuzzyArcLoss V3 SubCenters - Multi-prototype per class."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 num_subcenters: int = 3,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV3SubCenters(
            in_features, out_features, s=s, m=m, tau=tau, num_subcenters=num_subcenters
        )
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV25(nn.Module):
    """FuzzyArcLoss V2.5 - V2 inverse + V3 sub-centers."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 num_subcenters: int = 3,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV25(
            in_features, out_features, s=s, m=m, tau=tau, num_subcenters=num_subcenters
        )
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


class FuzzyArcLossV25ClassParams(nn.Module):
    """FuzzyArcLoss V2.5 + ClassParams - V2.5 with class-specific parameters."""
    def __init__(self, in_features: int, out_features: int,
                 s: float = 30.0, m: float = 0.50, tau: float = 0.5,
                 num_subcenters: int = 3,
                 class_tau: List[float] = None,
                 class_margin: List[float] = None,
                 class_scale: List[float] = None,
                 label_smoothing: float = 0.1, ce_weight: torch.Tensor = None,
                 use_focal: bool = True, focal_gamma: float = 2.0,
                 ce_focal_ratio: Tuple[float, float] = (0.6, 0.4)):
        super().__init__()
        self.head = FuzzyArcMarginProductV25ClassParams(
            in_features, out_features, s=s, m=m, tau=tau, num_subcenters=num_subcenters,
            class_tau=class_tau, class_margin=class_margin, class_scale=class_scale
        )
        self.ce = LabelSmoothingCrossEntropy(smoothing=label_smoothing, weight=ce_weight)
        self.use_focal = use_focal
        if use_focal:
            self.focal = FocalLoss(gamma=focal_gamma, weight=ce_weight)
        self.ce_weight_ratio = ce_focal_ratio[0]
        self.focal_weight_ratio = ce_focal_ratio[1]
        self.s = s
        self.weight = self.head.weight
    
    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        logits = self.head(features, labels)
        ce_loss = self.ce(logits, labels)
        if self.use_focal:
            focal_loss = self.focal(logits, labels)
            loss = self.ce_weight_ratio * ce_loss + self.focal_weight_ratio * focal_loss
        else:
            loss = ce_loss
        return loss, logits


# ==============================================================================
# BACKBONE (CTransPath)
# ==============================================================================

class ConvStem(nn.Module):
    """CTransPath's ConvStem patch embedding."""
    
    def __init__(self, img_size=224, patch_size=4, in_chans=3, embed_dim=96):
        super().__init__()
        self.img_size = img_size
        self.patch_size = patch_size
        self.grid_size = (img_size // patch_size, img_size // patch_size)
        self.num_patches = self.grid_size[0] * self.grid_size[1]
        
        stem_dim1 = embed_dim // 8  # 12
        stem_dim2 = embed_dim // 4  # 24
        
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
    """CTransPath backbone with ConvStem."""
    
    def __init__(self, checkpoint_path: str = None, freeze_layers: int = 0):
        super().__init__()
        
        if not HAS_TIMM:
            raise ImportError("timm required")
        
        self.model = timm.create_model(
            'swin_tiny_patch4_window7_224',
            pretrained=False,
            num_classes=0,
        )
        
        embed_dim = 96
        self.model.patch_embed = ConvStem(
            img_size=224, patch_size=4, in_chans=3, embed_dim=embed_dim
        )
        
        self.out_features = self.model.num_features
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            self._load_checkpoint(checkpoint_path)
            print(f"  ✓ Loaded CTransPath checkpoint")
        
        if freeze_layers > 0:
            for i, layer in enumerate(self.model.layers):
                if i < freeze_layers:
                    for param in layer.parameters():
                        param.requires_grad = False
    
    def _load_checkpoint(self, checkpoint_path: str):
        checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
        
        if isinstance(checkpoint, dict):
            state_dict = checkpoint.get('model', checkpoint.get('state_dict', checkpoint))
        else:
            state_dict = checkpoint
        
        # Remap keys
        remapped = {}
        for key, value in state_dict.items():
            if key.startswith('head.') or key.startswith('fc.'):
                continue
            if 'attn_mask' in key or 'relative_position_index' in key:
                continue
            
            new_key = key
            if '.downsample.' in key:
                for i in range(3):
                    if f'layers.{i}.downsample.' in key:
                        new_key = key.replace(f'layers.{i}.downsample.', f'layers.{i+1}.downsample.')
                        break
            remapped[new_key] = value
        
        # Filter matching keys
        model_state = self.model.state_dict()
        filtered = {k: v for k, v in remapped.items() 
                   if k in model_state and v.shape == model_state[k].shape}
        
        if len(filtered) >= 150:
            self.model.load_state_dict(filtered, strict=False)
    
    def forward(self, x):
        return self.model(x)


def build_model_with_loss(loss_type: str, num_classes: int, embed_dim: int,
                          checkpoint_path: str, freeze_layers: int = 0,
                          class_counts: List[int] = None, device: str = 'cuda',
                          ce_weight: torch.Tensor = None,
                          **loss_kwargs) -> Tuple[nn.Module, nn.Module]:
    """Build backbone + projection head + loss function."""
    
    # Backbone
    backbone = CTransPathBackbone(checkpoint_path, freeze_layers)
    backbone_dim = backbone.out_features
    
    # Projection head
    head = nn.Sequential(
        nn.Linear(backbone_dim, embed_dim),
        nn.LayerNorm(embed_dim),
        nn.GELU(),
        nn.Dropout(0.15),
    )
    
    model = nn.Sequential(backbone, head)
    
    # Loss function parameters
    s = loss_kwargs.get('s', 30.0)
    m = loss_kwargs.get('m', 0.5)
    tau = loss_kwargs.get('tau', 0.5)
    label_smoothing = loss_kwargs.get('label_smoothing', 0.1)
    use_focal = loss_kwargs.get('use_focal', True)
    focal_gamma = loss_kwargs.get('focal_gamma', 2.0)
    num_subcenters = loss_kwargs.get('num_subcenters', 3)
    
    # Class-specific parameters
    class_tau = loss_kwargs.get('class_tau', None)
    class_margin = loss_kwargs.get('class_margin', None)
    class_scale = loss_kwargs.get('class_scale', None)
    
    # Build loss function based on type
    if loss_type == 'softmax':
        loss_fn = SoftmaxLoss(embed_dim, num_classes, s=s)
    elif loss_type == 'sphereface':
        loss_fn = SphereFaceLoss(embed_dim, num_classes, s=s, m=4.0)
    elif loss_type == 'cosface':
        loss_fn = CosFaceLoss(embed_dim, num_classes, s=s, m=0.35)
    elif loss_type == 'arcface':
        loss_fn = ArcFaceLoss(embed_dim, num_classes, s=s, m=0.5)
    elif loss_type == 'vpl':
        loss_fn = VPLLoss(embed_dim, num_classes, s=s, m=0.35, r=0.1)
    elif loss_type == 'sphereface2':
        loss_fn = SphereFace2Loss(embed_dim, num_classes, s=s, m=1.35)
    elif loss_type == 'uniface':
        loss_fn = UniFaceLoss(embed_dim, num_classes, s=s, m=0.35)
    elif loss_type == 'adaptiveface':
        loss_fn = AdaptiveFaceLoss(embed_dim, num_classes, s=s, class_counts=class_counts)
    
    # FuzzyArcLoss V1 variants
    elif loss_type == 'fuzzyarcloss_v1_basic':
        loss_fn = FuzzyArcLossV1Basic(embed_dim, num_classes, s=s, m=m, tau=tau)
    elif loss_type == 'fuzzyarcloss_v1_improved':
        loss_fn = FuzzyArcLossV1Improved(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    
    # FuzzyArcLoss V2 variants
    elif loss_type == 'fuzzyarcloss_v2_basic':
        loss_fn = FuzzyArcLossV2Basic(embed_dim, num_classes, s=s, m=m, tau=tau)
    elif loss_type == 'fuzzyarcloss_v2':
        loss_fn = FuzzyArcLossV2(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    elif loss_type == 'fuzzyarcloss_v2_classparams':
        loss_fn = FuzzyArcLossV2ClassParams(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            class_tau=class_tau, class_margin=class_margin, class_scale=class_scale,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    
    # FuzzyArcLoss V3 variants
    elif loss_type == 'fuzzyarcloss_v3_entropy':
        loss_fn = FuzzyArcLossV3Entropy(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    elif loss_type == 'fuzzyarcloss_v3_topgap':
        loss_fn = FuzzyArcLossV3TopGap(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    elif loss_type == 'fuzzyarcloss_v3_subcenters':
        loss_fn = FuzzyArcLossV3SubCenters(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            num_subcenters=num_subcenters,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    
    # FuzzyArcLoss V2.5 variants
    elif loss_type == 'fuzzyarcloss_v25':
        loss_fn = FuzzyArcLossV25(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            num_subcenters=num_subcenters,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    elif loss_type == 'fuzzyarcloss_v25_classparams':
        loss_fn = FuzzyArcLossV25ClassParams(
            embed_dim, num_classes, s=s, m=m, tau=tau,
            num_subcenters=num_subcenters,
            class_tau=class_tau, class_margin=class_margin, class_scale=class_scale,
            label_smoothing=label_smoothing, ce_weight=ce_weight,
            use_focal=use_focal, focal_gamma=focal_gamma
        )
    
    else:
        raise ValueError(f"Unknown loss type: {loss_type}")
    
    return model, loss_fn


# ==============================================================================
# DATASET WITH ENHANCED AUGMENTATION
# ==============================================================================

IMG_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
MAT_EXCLUDE = {"__header__", "__version__", "__globals__"}


def pair_images_with_masks(image_dir: str, mask_dir: str) -> pd.DataFrame:
    """Pair images with their corresponding masks."""
    records = []
    
    for fname in os.listdir(image_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in IMG_EXTS:
            continue
        
        img_path = os.path.join(image_dir, fname)
        
        # Find mask
        mask_path = None
        for mext in ['.mat', '.png', '.jpg', '.tif']:
            candidate = os.path.join(mask_dir, stem + mext)
            if os.path.exists(candidate):
                mask_path = candidate
                break
        
        if mask_path:
            records.append({'image_path': img_path, 'mask_path': mask_path, 'stem': stem})
    
    return pd.DataFrame(records)


def load_mask(mask_path: str, thresh: float = 0.5) -> np.ndarray:
    """Load mask from various formats."""
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


class StainAugmentation:
    """
    Stain augmentation for H&E histopathology images.
    Simulates variations in staining protocols.
    """
    def __init__(self, prob: float = 0.5):
        self.prob = prob
    
    def __call__(self, img):
        if random.random() > self.prob:
            return img
        
        # Convert to numpy
        img_np = np.array(img).astype(np.float32)
        
        # Random color shifts (simulating stain variation)
        # H&E: Hematoxylin (blue-purple), Eosin (pink)
        h_shift = random.uniform(-0.1, 0.1)
        e_shift = random.uniform(-0.1, 0.1)
        
        # Apply shifts to RGB channels
        img_np[:, :, 0] = np.clip(img_np[:, :, 0] * (1 + e_shift), 0, 255)  # Red (Eosin)
        img_np[:, :, 2] = np.clip(img_np[:, :, 2] * (1 + h_shift), 0, 255)  # Blue (Hematoxylin)
        
        # Random brightness/contrast
        brightness = random.uniform(0.9, 1.1)
        contrast = random.uniform(0.9, 1.1)
        
        img_np = np.clip((img_np - 128) * contrast + 128 * brightness, 0, 255)
        
        return Image.fromarray(img_np.astype(np.uint8))


class HistDataset(Dataset):
    """Histopathology dataset with enhanced augmentation."""
    
    def __init__(self, df: pd.DataFrame, label_col: str, label2id: Dict,
                 img_size: int = 224, aug: bool = True,
                 use_roi_crop: bool = True, roi_padding: int = 24,
                 mask_thresh: float = 0.5,
                 use_stain_aug: bool = True, stain_aug_prob: float = 0.5):
        self.df = df.reset_index(drop=True)
        self.label_col = label_col
        self.label2id = label2id
        self.img_size = img_size
        self.aug = aug
        self.use_roi_crop = use_roi_crop
        self.roi_padding = roi_padding
        self.mask_thresh = mask_thresh
        
        # Enhanced augmentation pipeline
        if aug:
            aug_list = [
                T.RandomHorizontalFlip(),
                T.RandomVerticalFlip(),
                T.RandomRotation(30),
                T.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
            ]
            
            if use_stain_aug:
                self.stain_aug = StainAugmentation(prob=stain_aug_prob)
            else:
                self.stain_aug = None
            
            aug_list.extend([
                T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.05),
                T.RandomGrayscale(p=0.05),
                T.GaussianBlur(kernel_size=3, sigma=(0.1, 1.0)),
                T.Resize((img_size, img_size)),
                T.ToTensor(),
                T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
                T.RandomErasing(p=0.1, scale=(0.02, 0.1)),
            ])
            
            self.transform = T.Compose(aug_list)
        else:
            self.stain_aug = None
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
        
        # ROI crop
        if self.use_roi_crop and 'mask_path' in row:
            mask = load_mask(row['mask_path'], self.mask_thresh)
            if mask is not None:
                ys, xs = np.where(mask > 0)
                if len(xs) > 0:
                    x1, x2 = xs.min(), xs.max()
                    y1, y2 = ys.min(), ys.max()
                    
                    h, w = mask.shape
                    x1 = max(0, x1 - self.roi_padding)
                    y1 = max(0, y1 - self.roi_padding)
                    x2 = min(w, x2 + self.roi_padding)
                    y2 = min(h, y2 + self.roi_padding)
                    
                    img = img.crop((x1, y1, x2, y2))
        
        # Apply stain augmentation before other transforms
        if self.stain_aug is not None:
            img = self.stain_aug(img)
        
        img = self.transform(img)
        
        label = self.label2id[str(row[self.label_col])]
        
        return img, label


# ==============================================================================
# MIXUP AND CUTMIX
# ==============================================================================

def mixup_data(x, y, alpha=0.4):
    """Mixup augmentation."""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    
    batch_size = x.size(0)
    index = torch.randperm(batch_size).to(x.device)
    
    mixed_x = lam * x + (1 - lam) * x[index]
    y_a, y_b = y, y[index]
    
    return mixed_x, y_a, y_b, lam


def cutmix_data(x, y, alpha=1.0):
    """CutMix augmentation."""
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1
    
    batch_size = x.size(0)
    index = torch.randperm(batch_size).to(x.device)
    
    # Get bounding box
    W = x.size(2)
    H = x.size(3)
    cut_rat = np.sqrt(1 - lam)
    cut_w = int(W * cut_rat)
    cut_h = int(H * cut_rat)
    
    cx = np.random.randint(W)
    cy = np.random.randint(H)
    
    bbx1 = np.clip(cx - cut_w // 2, 0, W)
    bby1 = np.clip(cy - cut_h // 2, 0, H)
    bbx2 = np.clip(cx + cut_w // 2, 0, W)
    bby2 = np.clip(cy + cut_h // 2, 0, H)
    
    x[:, :, bbx1:bbx2, bby1:bby2] = x[index, :, bbx1:bbx2, bby1:bby2]
    
    # Adjust lambda based on actual area
    lam = 1 - ((bbx2 - bbx1) * (bby2 - bby1) / (W * H))
    
    y_a, y_b = y, y[index]
    
    return x, y_a, y_b, lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    """Mixup loss computation."""
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


# ==============================================================================
# TRAINING FUNCTION
# ==============================================================================

def run_single_experiment(loss_type: str, train_loader, val_loader, test_loader,
                          num_classes: int, class_counts: List[int],
                          id2label: Dict, device: str = 'cuda',
                          epochs: int = 150, verbose: bool = True,
                          ce_weight: torch.Tensor = None,
                          use_mixup: bool = True, mixup_prob: float = 0.3,
                          use_cutmix: bool = True, cutmix_prob: float = 0.3,
                          **loss_kwargs) -> Dict:
    """Run a single experiment with given loss function."""
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Training with {loss_type.upper()}")
        print(f"{'='*60}")
        sys.stdout.flush()
    
    # Build model
    model, loss_fn = build_model_with_loss(
        loss_type, num_classes, config.EMBED_DIM,
        config.CTRANSPATH_CHECKPOINT, config.FREEZE_BACKBONE_LAYERS,
        class_counts, device, ce_weight=ce_weight, **loss_kwargs
    )
    
    model = model.to(device)
    loss_fn = loss_fn.to(device)
    
    # Multi-GPU support
    if torch.cuda.device_count() > 1:
        print(f"  Using {torch.cuda.device_count()} GPUs with DataParallel")
        model = nn.DataParallel(model)
    
    # Optimizer
    if isinstance(model, nn.DataParallel):
        backbone_params = model.module[0].parameters()
        head_params = model.module[1].parameters()
    else:
        backbone_params = model[0].parameters()
        head_params = model[1].parameters()
    
    optimizer = torch.optim.AdamW([
        {'params': backbone_params, 'lr': config.LR},
        {'params': head_params, 'lr': config.LR * config.HEAD_LR_MULT},
        {'params': loss_fn.parameters(), 'lr': config.LR * config.HEAD_LR_MULT},
    ], weight_decay=config.WEIGHT_DECAY)
    
    # Scheduler with warmup
    def lr_lambda(epoch):
        if epoch < config.WARMUP_EPOCHS:
            return epoch / config.WARMUP_EPOCHS
        else:
            return 0.5 * (1 + math.cos(math.pi * (epoch - config.WARMUP_EPOCHS) / (epochs - config.WARMUP_EPOCHS)))
    
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
    
    # Mixed precision scaler
    scaler = torch.cuda.amp.GradScaler() if device == 'cuda' else None
    
    # Training loop
    best_val_f1 = 0
    best_epoch = 0
    best_state = None
    
    for epoch in range(epochs):
        # Training
        model.train()
        loss_fn.train()
        
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_idx, (images, labels) in enumerate(train_loader):
            images = images.to(device)
            labels = labels.to(device)
            
            # Apply MixUp or CutMix with probability
            use_mix = False
            if use_mixup and random.random() < mixup_prob:
                images, labels_a, labels_b, lam = mixup_data(images, labels, alpha=config.MIXUP_ALPHA)
                use_mix = True
                mix_type = 'mixup'
            elif use_cutmix and random.random() < cutmix_prob:
                images, labels_a, labels_b, lam = cutmix_data(images, labels)
                use_mix = True
                mix_type = 'cutmix'
            
            optimizer.zero_grad()
            
            if scaler is not None:
                with torch.cuda.amp.autocast():
                    features = model(images)
                    if use_mix:
                        loss1, logits = loss_fn(features, labels_a)
                        loss2, _ = loss_fn(features, labels_b)
                        loss = lam * loss1 + (1 - lam) * loss2
                    else:
                        loss, logits = loss_fn(features, labels)
                
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                torch.nn.utils.clip_grad_norm_(loss_fn.parameters(), max_norm=1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                features = model(images)
                if use_mix:
                    loss1, logits = loss_fn(features, labels_a)
                    loss2, _ = loss_fn(features, labels_b)
                    loss = lam * loss1 + (1 - lam) * loss2
                else:
                    loss, logits = loss_fn(features, labels)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                torch.nn.utils.clip_grad_norm_(loss_fn.parameters(), max_norm=1.0)
                optimizer.step()
            
            total_loss += loss.item()
            preds = logits.argmax(dim=1)
            if not use_mix:
                correct += (preds == labels).sum().item()
                total += labels.size(0)
        
        train_loss = total_loss / len(train_loader)
        train_acc = correct / total if total > 0 else 0
        
        # Validation
        model.eval()
        loss_fn.eval()
        
        val_preds = []
        val_labels_list = []
        
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device)
                labels = labels.to(device)
                
                features = model(images)
                
                # Margin-free cosine logits for proper evaluation
                # (arc-margin logits are only valid for loss computation)
                if hasattr(loss_fn, 'weight'):
                    weight = loss_fn.weight
                elif hasattr(loss_fn, 'head') and hasattr(loss_fn.head, 'weight'):
                    weight = loss_fn.head.weight
                else:
                    weight = loss_fn.head.weight
                
                features_norm = F.normalize(features, dim=1)
                if weight.dim() == 3:  # (C, K, D) for sub-centers
                    weight_norm = F.normalize(weight, dim=2)
                    cosine_all = torch.einsum('bd,ckd->bck', features_norm, weight_norm)
                    logits, _ = cosine_all.max(dim=2)
                else:
                    weight_norm = F.normalize(weight, dim=1)
                    logits = features_norm @ weight_norm.t()
                
                preds = logits.argmax(dim=1)
                
                val_preds.extend(preds.cpu().numpy())
                val_labels_list.extend(labels.cpu().numpy())
        
        val_preds = np.array(val_preds)
        val_labels_arr = np.array(val_labels_list)
        val_f1 = f1_score(val_labels_arr, val_preds, average='macro')
        
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            if isinstance(model, nn.DataParallel):
                model_state = {k: v.cpu().clone() for k, v in model.module.state_dict().items()}
            else:
                model_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_state = {
                'model': model_state,
                'loss_fn': {k: v.cpu().clone() for k, v in loss_fn.state_dict().items()}
            }
        
        if verbose and (epoch + 1) % config.PRINT_FREQ == 0:
            print(f"  Ep {epoch+1:3d}/{epochs} | Loss {train_loss:.4f} | Val-F1 {val_f1:.4f} | Best {best_val_f1:.4f}@{best_epoch+1}")
            sys.stdout.flush()
        
        scheduler.step()
    
    # Load best model for test evaluation
    if best_state:
        if isinstance(model, nn.DataParallel):
            model.module.load_state_dict({k: v.to(device) for k, v in best_state['model'].items()})
        else:
            model.load_state_dict({k: v.to(device) for k, v in best_state['model'].items()})
        loss_fn.load_state_dict({k: v.to(device) for k, v in best_state['loss_fn'].items()})
    
    # Test evaluation
    model.eval()
    loss_fn.eval()
    
    test_preds = []
    test_labels_list = []
    
    with torch.no_grad():
        for images, labels in test_loader:
            images = images.to(device)
            labels = labels.to(device)
            
            features = model(images)
            
            if hasattr(loss_fn, 'weight'):
                weight = loss_fn.weight
            elif hasattr(loss_fn, 'head') and hasattr(loss_fn.head, 'weight'):
                weight = loss_fn.head.weight
            else:
                weight = loss_fn.head.weight
            
            if weight.dim() == 3:
                weight_norm = F.normalize(weight, dim=2)
                features_norm = F.normalize(features, dim=1)
                cosine_all = torch.einsum('bd,ckd->bck', features_norm, weight_norm)
                logits, _ = cosine_all.max(dim=2)
            else:
                weight_norm = F.normalize(weight, dim=1)
                features_norm = F.normalize(features, dim=1)
                logits = features_norm @ weight_norm.t()
            
            preds = logits.argmax(dim=1)
            
            test_preds.extend(preds.cpu().numpy())
            test_labels_list.extend(labels.cpu().numpy())
    
    test_preds = np.array(test_preds)
    test_labels_arr = np.array(test_labels_list)
    
    test_acc = accuracy_score(test_labels_arr, test_preds)
    test_f1 = f1_score(test_labels_arr, test_preds, average='macro')
    test_precision = precision_score(test_labels_arr, test_preds, average='macro', zero_division=0)
    test_recall = recall_score(test_labels_arr, test_preds, average='macro', zero_division=0)
    f1_per_class = f1_score(test_labels_arr, test_preds, average=None, zero_division=0)
    
    if verbose:
        print(f"\n  TEST: Acc={test_acc*100:.2f}% | Macro-F1={test_f1*100:.2f}%")
        for i, f1 in enumerate(f1_per_class):
            print(f"    {id2label[i]}: {f1*100:.1f}%")
        sys.stdout.flush()
    
    return {
        'loss_type': loss_type,
        'best_epoch': best_epoch,
        'best_val_f1': best_val_f1,
        'test_accuracy': test_acc,
        'test_f1': test_f1,
        'test_precision': test_precision,
        'test_recall': test_recall,
        'test_f1_per_class': f1_per_class.tolist(),
        'loss_kwargs': loss_kwargs
    }


# ==============================================================================
# MAIN ABLATION STUDY
# ==============================================================================

def run_ablation_study():
    """Run complete ablation study with all loss functions."""
    
    print("="*70)
    print("  COMPLETE ABLATION STUDY: FuzzyArcLoss V1 vs V2 vs V2.5 vs V3")
    print("  + Face Recognition Baselines (Softmax, ArcFace, CosFace, etc.)")
    print("="*70)
    
    # Device
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\nDevice: {device}")
    if device == 'cuda':
        print(f"GPUs: {torch.cuda.device_count()} x {torch.cuda.get_device_name(0)}")
    
    # Seed
    random.seed(config.SEED)
    np.random.seed(config.SEED)
    torch.manual_seed(config.SEED)
    if device == 'cuda':
        torch.cuda.manual_seed_all(config.SEED)
    
    # Load data
    print(f"\n[1/3] Loading data...")
    
    df = pair_images_with_masks(config.IMAGE_DIR, config.MASK_DIR)
    
    # Load labels from Excel
    xls = pd.read_excel(config.XLS_PATH)
    
    image_col = 'tile_id'
    label_col = 'pattern'
    
    xls['stem'] = xls[image_col].astype(str)
    xls_filtered = xls[xls[label_col].str.lower() != 'none'].copy()
    print(f"  Samples: {len(xls_filtered)}, Classes: {xls_filtered[label_col].nunique()}")
    
    df = df.merge(xls_filtered[['stem', label_col]], on='stem', how='inner')
    df = df.dropna(subset=[label_col])
    
    labels = sorted(df[label_col].astype(str).unique())
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    num_classes = len(labels)
    
    print(f"  Labels: {labels}")
    
    # Split data
    train_df, temp_df = train_test_split(
        df, test_size=config.VAL_SIZE + config.TEST_SIZE,
        stratify=df[label_col], random_state=config.SEED
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=config.TEST_SIZE / (config.VAL_SIZE + config.TEST_SIZE),
        stratify=temp_df[label_col], random_state=config.SEED
    )
    
    print(f"  Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    # Class counts
    train_labels = [label2id[str(l)] for l in train_df[label_col]]
    class_counts = [train_labels.count(i) for i in range(num_classes)]
    print(f"  Class counts: {dict(zip(labels, class_counts))}")
    
    # Create datasets
    train_ds = HistDataset(
        train_df, label_col, label2id, config.IMG_SIZE, aug=True,
        use_roi_crop=config.USE_ROI_CROP,
        use_stain_aug=config.USE_STAIN_AUG, stain_aug_prob=config.STAIN_AUG_PROB
    )
    val_ds = HistDataset(
        val_df, label_col, label2id, config.IMG_SIZE, aug=False,
        use_roi_crop=config.USE_ROI_CROP
    )
    test_ds = HistDataset(
        test_df, label_col, label2id, config.IMG_SIZE, aug=False,
        use_roi_crop=config.USE_ROI_CROP
    )
    
    # Create dataloaders
    if config.USE_WEIGHTED_SAMPLER:
        weights = [1.0 / class_counts[l] for l in train_labels]
        sampler = WeightedRandomSampler(weights, len(weights), replacement=True)
        train_loader = DataLoader(train_ds, batch_size=config.BATCH_SIZE * max(1, torch.cuda.device_count()),
                                  sampler=sampler, num_workers=config.NUM_WORKERS, pin_memory=True)
    else:
        train_loader = DataLoader(train_ds, batch_size=config.BATCH_SIZE * max(1, torch.cuda.device_count()),
                                  shuffle=True, num_workers=config.NUM_WORKERS, pin_memory=True)
    
    val_loader = DataLoader(val_ds, batch_size=config.BATCH_SIZE * max(1, torch.cuda.device_count()), shuffle=False,
                            num_workers=config.NUM_WORKERS, pin_memory=True)
    test_loader = DataLoader(test_ds, batch_size=config.BATCH_SIZE * max(1, torch.cuda.device_count()), shuffle=False,
                             num_workers=config.NUM_WORKERS, pin_memory=True)
    
    # Compute class weights
    total_samples = sum(class_counts)
    ce_weights = torch.tensor([total_samples / (num_classes * c) for c in class_counts])
    ce_weights = ce_weights / ce_weights.sum() * num_classes
    ce_weights = ce_weights.to(device)
    
    # ============================================================
    # ABLATION EXPERIMENTS (Best performers first!)
    # ============================================================
    print("\n" + "="*70)
    print("[2/3] Running Experiments (Best performers first)")
    print("="*70)
    
    # Loss functions ordered by expected performance (best first)
    # V3 SubCenters uses Optuna-optimized hyperparameters for CTransPath backbone
    loss_functions = [
        # BEST PERFORMERS (Optuna-optimized V3 SubCenters first)
        ('fuzzyarcloss_v3_subcenters', {'s': 39.0, 'm': 0.557, 'tau': 0.454, 'num_subcenters': 4}),
        ('fuzzyarcloss_v2_classparams', {'s': 30.0, 'm': 0.5, 'tau': 0.5,
            'class_tau': [0.35, 0.45, 0.35, 0.50, 0.60, 0.65],
            'class_margin': [0.35, 0.25, 0.35, 0.50, 0.55, 0.60],
            'class_scale': [25.0, 22.0, 25.0, 30.0, 32.0, 35.0]}),
        ('softmax', {'s': 30.0}),
        ('fuzzyarcloss_v1_improved', {'s': 30.0, 'm': 0.5, 'tau': 0.5}),
        
        # V2.5 variants
        ('fuzzyarcloss_v25', {'s': 30.0, 'm': 0.5, 'tau': 0.5, 'num_subcenters': 3}),
        ('fuzzyarcloss_v25_classparams', {'s': 30.0, 'm': 0.5, 'tau': 0.5, 'num_subcenters': 3,
            'class_tau': [0.45, 0.30, 0.45, 0.30, 0.40, 0.55],
            'class_margin': [0.40, 0.25, 0.40, 0.25, 0.35, 0.50],
            'class_scale': [28.0, 22.0, 28.0, 22.0, 26.0, 32.0]}),
        
        # V2 variants
        ('fuzzyarcloss_v2', {'s': 30.0, 'm': 0.5, 'tau': 0.5}),
        ('fuzzyarcloss_v2_basic', {'s': 30.0, 'm': 0.5, 'tau': 0.5}),
        
        # V1 variants
        ('fuzzyarcloss_v1_basic', {'s': 30.0, 'm': 0.5, 'tau': 0.5}),
        
        # V3 alternatives
        ('fuzzyarcloss_v3_entropy', {'s': 30.0, 'm': 0.5, 'tau': 0.5}),
        ('fuzzyarcloss_v3_topgap', {'s': 30.0, 'm': 0.5, 'tau': 0.5}),
        
        # Face recognition baselines
        ('arcface', {'s': 30.0, 'm': 0.5}),
        ('cosface', {'s': 30.0, 'm': 0.35}),
        ('sphereface2', {'s': 30.0, 'm': 1.35}),
        ('adaptiveface', {'s': 30.0}),
        ('vpl', {'s': 30.0, 'm': 0.35}),
        ('uniface', {'s': 30.0, 'm': 0.35}),
        ('sphereface', {'s': 30.0, 'm': 4.0}),
    ]
    
    all_results = []
    
    for idx, (loss_type, kwargs) in enumerate(loss_functions):
        print(f"\n--- {idx+1}/{len(loss_functions)}: {loss_type.upper()} ---")
        sys.stdout.flush()
        
        try:
            result = run_single_experiment(
                loss_type, train_loader, val_loader, test_loader,
                num_classes, class_counts, id2label, device,
                epochs=config.EPOCHS, verbose=True,
                ce_weight=ce_weights,
                use_mixup=config.USE_MIXUP, mixup_prob=config.MIXUP_PROB,
                use_cutmix=config.USE_CUTMIX, cutmix_prob=config.CUTMIX_PROB,
                label_smoothing=0.1,
                use_focal=True,
                focal_gamma=2.0,
                **kwargs
            )
            all_results.append(result)
        except Exception as e:
            print(f"[ERROR] {loss_type} failed: {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*70)
    print("[3/3] FINAL RESULTS")
    print("="*70)
    
    if len(all_results) == 0:
        print("No results to summarize!")
        return None
    
    # Sort by F1 score
    all_results_sorted = sorted(all_results, key=lambda x: x['test_f1'], reverse=True)
    
    print("\n{:<5} {:<35} {:>8} {:>10} {:>8}".format(
        "#", "Method", "Acc", "Macro-F1", "Epoch"))
    print("-"*70)
    
    for i, result in enumerate(all_results_sorted):
        print("{:<5} {:<35} {:>7.2f}% {:>9.2f}% {:>8}".format(
            i+1,
            result['loss_type'][:35],
            result['test_accuracy'] * 100,
            result['test_f1'] * 100,
            result['best_epoch'] + 1
        ))
    
    # Per-class comparison
    print("\n\nPER-CLASS F1 COMPARISON:")
    print("-"*100)
    header = "{:<35}".format("Method")
    for label in labels:
        header += "{:>10}".format(label[:8])
    print(header)
    print("-"*100)
    
    for result in all_results_sorted[:10]:  # Top 10
        row = "{:<35}".format(result['loss_type'][:35])
        for f1 in result['test_f1_per_class']:
            row += "{:>10.1f}".format(f1 * 100)
        print(row)
    
    # Save results
    os.makedirs(config.OUT_DIR, exist_ok=True)
    
    results_dict = {
        'config': {
            'epochs': config.EPOCHS,
            'batch_size': config.BATCH_SIZE,
            'lr_backbone': config.LR,
            'lr_head': config.LR * config.HEAD_LR_MULT,
            'head_lr_mult': config.HEAD_LR_MULT,
            'embed_dim': config.EMBED_DIM,
            'freeze_layers': config.FREEZE_BACKBONE_LAYERS,
            'seed': config.SEED,
            'use_mixup': config.USE_MIXUP,
            'use_cutmix': config.USE_CUTMIX,
            'use_stain_aug': config.USE_STAIN_AUG,
            'backbone': 'ctranspath',
            'optuna_optimized': True,
            'warmup_epochs': config.WARMUP_EPOCHS,
        },
        'class_labels': labels,
        'class_counts': class_counts,
        'ablation_results': all_results_sorted
    }
    
    results_path = os.path.join(config.OUT_DIR, 'ablation_results_v12_optuna.json')
    with open(results_path, 'w') as f:
        json.dump(results_dict, f, indent=2, default=str)
    
    print(f"\n✓ Results saved to: {results_path}")
    
    # Best result
    best = all_results_sorted[0]
    print(f"\n{'='*70}")
    print(f"  🏆 WINNER: {best['loss_type']}")
    print(f"     Macro-F1: {best['test_f1']*100:.2f}%")
    print(f"     Accuracy: {best['test_accuracy']*100:.2f}%")
    print(f"     Best Epoch: {best['best_epoch']+1}")
    print(f"{'='*70}")
    
    return results_dict


# ==============================================================================
# ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    results = run_ablation_study()
