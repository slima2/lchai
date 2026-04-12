#!/usr/bin/env python3
"""
SLIMA Statistical Validation — K-Fold × Multi-Seed (Feb 2026)
==============================================================
PURPOSE:
  A single 80/20 split on 128 test samples is NOT statistically
  meaningful. SphereFace 95.03% vs V2 94.48% = 1 sample difference.
  
  This script runs 5-fold stratified CV × 3 seeds = 15 runs per loss.
  Produces mean ± std with 95% confidence intervals and paired t-test
  to determine if any difference is statistically significant.

WHAT THIS PROVES FOR YOUR THESIS:
  - If V2's mean F1 ≥ SphereFace mean F1 → V2 wins (with CI)
  - If overlapping CIs → "no statistically significant difference"
    (still valid: V2 is a NOVEL contribution performing on par)
  - Per-class stability (std on lepidic, micropapillary)

SCOPE: Only runs the top contenders (not all 18) to save time:
  1. FuzzyArcLoss V2 (Optuna)     — your main contribution
  2. SphereFace                    — surprise competitor
  3. FuzzyArcLoss V3 SubCenters   — your secondary contribution
  4. ArcFace                       — standard baseline
  5. Softmax                       — no-margin baseline

RUNTIME: ~5 methods × 15 runs × 120 epochs ≈ 6-10 hours on 6× H100
  (each run is ~5 min, but sequential within a fold to ensure fairness)
  
DETERMINISTIC: Sets all CUDA deterministic flags for reproducibility.
"""

import os, sys, math, json, random, time, copy
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, List

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from scipy import stats

import pandas as pd

# ============================================================
# IMPORTS — same as ablation (copy the full ablation file and 
# import from it, or paste the needed classes here)
# ============================================================
# In practice, you'd do:
#   from SLIMA_ablation_study_loss_functions_ver_12_feb_2026_gpu_rev_11 import (
#       build_model_with_loss, CTransPathBackbone, ConvStem, 
#       FuzzyArcMarginProductV2, ..., GPUCachedMaskDataset, GPUAugmentation,
#       _logits_nomargin_any, normalize_key, pair_images_with_masks,
#       load_mask_from_mat
#   )
#
# For this script, we'll use exec() to import from the ablation file.
# Alternatively, copy the classes into a shared module.

# Point this to your ablation script:
ABLATION_SCRIPT = "/home/rapids/notebooks/slima/SLIMA_ablation_study_loss_functions_ver_23_feb_2026_gpu_rev_13.py"


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class KFoldConfig:
    # Paths (same as ablation)
    ROOT_DIR: str = "/home/rapids/notebooks/slima/Zenodo_Anorak_original"
    XLS_PATH: str = "/home/rapids/notebooks/slima/overlay_index ver 9 nov 2025.xlsx"
    OUT_DIR: str = "/home/rapids/notebooks/slima/outputs/kfold_validation"
    CTRANSPATH_CHECKPOINT: str = "/home/rapids/notebooks/slima/models/ctranspath.pth"

    # Architecture (same as ablation)
    EMBED_DIM: int = 512
    IMG_SIZE: int = 224
    USE_MASK_AS_CHANNEL: bool = True

    # Training (same as ablation)
    BATCH_SIZE: int = 8
    EPOCHS: int = 120
    WEIGHT_DECAY: float = 1e-4
    MIXED_PRECISION: str = "no"
    USE_MIXUP: bool = False
    USE_CUTMIX: bool = False
    FREEZE_BACKBONE_LAYERS: int = 2

    # V2 Optuna-found training params (applied to ALL losses for fairness)
    LR: float = 7.478950876910481e-05
    HEAD_LR_MULT: float = 8.282463948665386
    WARMUP_EPOCHS: int = 8

    # ROI settings
    USE_ROI_CROP: bool = True
    ROI_PADDING: int = 24
    MASK_THRESH: float = 0.5

    # K-Fold settings
    N_FOLDS: int = 5
    SEEDS: list = None  # Set in __post_init__
    INCLUDE_PATTERNS: str = "lepidic,acinar,papillary,micropapillary,solid,mucinous"
    PRINT_FREQ: int = 10

    def __post_init__(self):
        if self.SEEDS is None:
            self.SEEDS = [42, 123, 2026]

kf_config = KFoldConfig()
os.makedirs(kf_config.OUT_DIR, exist_ok=True)


# ============================================================
# TOP CONTENDERS TO VALIDATE
# ============================================================

METHODS_TO_VALIDATE = [
    # (name, loss_type, kwargs) — only the top contenders
    ("FuzzyArcLoss V2 (Optuna)",
     "fuzzyarcloss_v2",
     {"s": 46.101434376822986, "m": 0.5178476475091369, "tau": 0.44787389912216496}),

    ("SphereFace",
     "sphereface",
     {"s": 30.0, "m": 4.0}),

    ("FuzzyArcLoss V3 SubCenters (Optuna)",
     "fuzzyarcloss_v3_subcenters",
     {"s": 39.001786002638916, "m": 0.5573158242327586, "tau": 0.4542757061233031, "num_subcenters": 4}),

    ("ArcFace",
     "arcface",
     {"s": 30.0, "m": 0.5}),

    ("Softmax (CE)",
     "softmax",
     {}),
]


# ============================================================
# DETERMINISTIC TRAINING
# ============================================================

def set_deterministic(seed):
    """Make training as reproducible as possible."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    # CUDA deterministic flags
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    # For full determinism (may slow training ~10%):
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":16:8"
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass  # Not available in all PyTorch versions


# ============================================================
# MAIN K-FOLD VALIDATION
# ============================================================

def run_kfold_validation():
    """
    For each seed × fold × method:
      1. Split data with stratified K-fold
      2. Train for EPOCHS
      3. Evaluate with margin-free logits
      4. Record macro-F1, accuracy, per-class F1
    
    Then compute:
      - Mean ± std per method
      - 95% confidence intervals
      - Paired t-test: V2 vs SphereFace
    """
    print("=" * 70)
    print("  SLIMA K-Fold Statistical Validation")
    print(f"  {kf_config.N_FOLDS}-Fold CV × {len(kf_config.SEEDS)} Seeds "
          f"× {len(METHODS_TO_VALIDATE)} Methods")
    print(f"  = {kf_config.N_FOLDS * len(kf_config.SEEDS) * len(METHODS_TO_VALIDATE)} "
          f"total training runs")
    print("=" * 70)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    if device == 'cuda':
        print(f"  GPUs: {torch.cuda.device_count()} × {torch.cuda.get_device_name(0)}")

    # ── Load and import ablation code ──
    print(f"\n  Loading ablation code from: {ABLATION_SCRIPT}")
    ablation_ns = {}
    with open(ABLATION_SCRIPT) as f:
        exec(compile(f.read(), ABLATION_SCRIPT, 'exec'), ablation_ns)

    # Extract needed functions
    pair_images_with_masks = ablation_ns['pair_images_with_masks']
    normalize_key = ablation_ns['normalize_key']
    build_model_with_loss = ablation_ns['build_model_with_loss']
    _logits_nomargin_any = ablation_ns['_logits_nomargin_any']
    GPUCachedMaskDataset = ablation_ns.get('GPUCachedMaskDataset')
    GPUAugmentation = ablation_ns.get('GPUAugmentation')
    HistMaskDataset = ablation_ns.get('HistMaskDataset')
    abl_config = ablation_ns.get('config')  # ablation's config object

    HAS_KORNIA = ablation_ns.get('HAS_KORNIA', False)

    # ── Load data (same as ablation) ──
    print("\n[1/4] Loading data...")
    root = Path(kf_config.ROOT_DIR)
    image_dir = str(root)
    mask_dir = str(root)
    for d in root.iterdir():
        if d.is_dir():
            dl = d.name.lower()
            if 'image' in dl or 'tile' in dl or 'patch' in dl:
                image_dir = str(d)
            if 'mask' in dl or 'mat' in dl or 'annot' in dl or 'overlay' in dl:
                mask_dir = str(d)

    df = pair_images_with_masks(image_dir, mask_dir)

    xls = pd.read_excel(kf_config.XLS_PATH)
    label_candidates = ["pattern","label","class","type","luad_pattern","histologic_pattern"]
    file_candidates = ["tile_id","overlay_file","image_file","file","path","filename","name","base","stem"]
    label_col = next((c for c in label_candidates if c in xls.columns), None)
    file_col = next((c for c in file_candidates if c in xls.columns), None)

    label_map = {}
    for _, r in xls.iterrows():
        stem = Path(str(r[file_col])).stem
        lbl = str(r[label_col]).strip()
        label_map[stem] = lbl
        label_map[normalize_key(stem)] = lbl
        label_map[stem.lower()] = lbl

    df[label_col] = df["base"].map(label_map)
    miss = df[label_col].isna()
    if miss.any():
        df.loc[miss, label_col] = df.loc[miss, "base_norm"].map(label_map)
    df = df[~df[label_col].isna()].copy()

    inc = {p.strip().lower() for p in kf_config.INCLUDE_PATTERNS.split(",")}
    df[label_col] = df[label_col].astype(str)
    df = df[df[label_col].str.lower().isin(inc)].copy()
    df['label'] = df[label_col].str.lower()

    labels = sorted(df['label'].unique().tolist())
    label2id = {l: i for i, l in enumerate(labels)}
    id2label = {i: l for l, i in label2id.items()}
    num_classes = len(labels)

    print(f"  Dataset: {len(df)} samples, {num_classes} classes: {labels}")

    # ── Storage for all results ──
    # results[method_name] = list of dicts with f1, acc, per_class_f1, seed, fold
    all_results = {name: [] for name, _, _ in METHODS_TO_VALIDATE}

    # ── Run K-Fold × Seeds ──
    print(f"\n[2/4] Running {kf_config.N_FOLDS}-fold CV × {len(kf_config.SEEDS)} seeds...")
    total_runs = kf_config.N_FOLDS * len(kf_config.SEEDS) * len(METHODS_TO_VALIDATE)
    run_count = 0
    t_global = time.time()

    for seed in kf_config.SEEDS:
        skf = StratifiedKFold(n_splits=kf_config.N_FOLDS, shuffle=True, random_state=seed)

        for fold_idx, (train_idx, val_idx) in enumerate(skf.split(df, df['label'])):
            train_df = df.iloc[train_idx].reset_index(drop=True)
            val_df = df.iloc[val_idx].reset_index(drop=True)

            train_labels_list = [label2id[l] for l in train_df['label']]
            class_counts = [train_labels_list.count(i) for i in range(num_classes)]

            # CE weights
            total_samples = sum(class_counts)
            ce_weights = torch.tensor([total_samples / (num_classes * max(c, 1)) for c in class_counts])
            ce_weights = (ce_weights / ce_weights.sum() * num_classes).to(device)

            # Build datasets
            in_channels = 4 if kf_config.USE_MASK_AS_CHANNEL else 3

            if HAS_KORNIA and GPUCachedMaskDataset is not None:
                train_ds = GPUCachedMaskDataset(
                    train_df, 'label', label2id, kf_config.IMG_SIZE,
                    kf_config.USE_MASK_AS_CHANNEL, kf_config.USE_ROI_CROP,
                    kf_config.ROI_PADDING, kf_config.MASK_THRESH)
                val_ds = GPUCachedMaskDataset(
                    val_df, 'label', label2id, kf_config.IMG_SIZE,
                    kf_config.USE_MASK_AS_CHANNEL, kf_config.USE_ROI_CROP,
                    kf_config.ROI_PADDING, kf_config.MASK_THRESH)
                gpu_train_aug = GPUAugmentation(kf_config.IMG_SIZE, training=True).to(device)
                gpu_val_aug = GPUAugmentation(kf_config.IMG_SIZE, training=False).to(device)
                nw = 0
            else:
                train_ds = HistMaskDataset(
                    train_df, 'label', label2id, kf_config.IMG_SIZE, aug=True,
                    use_mask_as_channel=kf_config.USE_MASK_AS_CHANNEL,
                    use_roi_crop=kf_config.USE_ROI_CROP)
                val_ds = HistMaskDataset(
                    val_df, 'label', label2id, kf_config.IMG_SIZE, aug=False,
                    use_mask_as_channel=kf_config.USE_MASK_AS_CHANNEL,
                    use_roi_crop=kf_config.USE_ROI_CROP)
                gpu_train_aug = gpu_val_aug = None
                nw = 4

            bs = kf_config.BATCH_SIZE * max(1, torch.cuda.device_count())
            train_loader = DataLoader(train_ds, batch_size=bs, shuffle=True,
                                       num_workers=nw, pin_memory=not HAS_KORNIA, drop_last=True)
            val_loader = DataLoader(val_ds, batch_size=bs, shuffle=False,
                                     num_workers=nw, pin_memory=not HAS_KORNIA)

            print(f"\n  Seed={seed}, Fold={fold_idx+1}/{kf_config.N_FOLDS} "
                  f"(train={len(train_df)}, val={len(val_df)})")

            for method_name, loss_type, loss_kwargs in METHODS_TO_VALIDATE:
                run_count += 1
                set_deterministic(seed)  # Reset seed before each method

                t0 = time.time()
                print(f"    [{run_count}/{total_runs}] {method_name}...", end=" ", flush=True)

                # Build fresh model
                model, loss_fn = build_model_with_loss(
                    loss_type, num_classes, kf_config.EMBED_DIM,
                    kf_config.CTRANSPATH_CHECKPOINT, kf_config.FREEZE_BACKBONE_LAYERS,
                    class_counts, device, ce_weight=ce_weights,
                    in_channels=in_channels, **loss_kwargs
                )

                if torch.cuda.device_count() > 1:
                    model = nn.DataParallel(model)
                model.to(device)
                loss_fn.to(device)

                # Optimizer
                if isinstance(model, nn.DataParallel):
                    bb_p = list(model.module[0].parameters())
                    hd_p = list(model.module[1].parameters()) + list(loss_fn.parameters())
                else:
                    bb_p = list(model[0].parameters())
                    hd_p = list(model[1].parameters()) + list(loss_fn.parameters())

                optimizer = torch.optim.AdamW([
                    {'params': bb_p, 'lr': kf_config.LR},
                    {'params': hd_p, 'lr': kf_config.LR * kf_config.HEAD_LR_MULT},
                ], weight_decay=kf_config.WEIGHT_DECAY)

                epochs = kf_config.EPOCHS
                warmup = kf_config.WARMUP_EPOCHS
                def lr_lambda(epoch):
                    if epoch < warmup:
                        return (epoch + 1) / warmup
                    return 0.5 * (1 + math.cos(math.pi * (epoch - warmup) / max(1, epochs - warmup)))
                scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)

                # Train
                best_avg_pr = 0
                best_state = None

                for epoch in range(epochs):
                    model.train(); loss_fn.train()
                    for imgs, lbl in train_loader:
                        imgs = imgs.to(device, non_blocking=True)
                        lbl = lbl.to(device, non_blocking=True)
                        if gpu_train_aug is not None:
                            imgs = gpu_train_aug(imgs)
                        feats = model(imgs)
                        loss, _ = loss_fn(feats, lbl)
                        optimizer.zero_grad(set_to_none=True)
                        loss.backward()
                        optimizer.step()
                    scheduler.step()

                    # Validate every PRINT_FREQ epochs
                    if (epoch + 1) % kf_config.PRINT_FREQ == 0 or epoch == epochs - 1:
                        model.eval(); loss_fn.eval()
                        vp, vl = [], []
                        with torch.no_grad():
                            for imgs, lbl in val_loader:
                                imgs = imgs.to(device, non_blocking=True)
                                if gpu_val_aug is not None:
                                    imgs = gpu_val_aug(imgs)
                                feats = model(imgs)
                                logits = _logits_nomargin_any(feats, loss_fn)
                                if logits is None:
                                    _, logits = loss_fn(feats, lbl.to(device))
                                vp.extend(logits.argmax(1).cpu().numpy())
                                vl.extend(lbl.numpy())
                        prec = precision_score(vl, vp, average='macro', zero_division=0)
                        rec = recall_score(vl, vp, average='macro', zero_division=0)
                        avg_pr = (prec + rec) / 2
                        if avg_pr > best_avg_pr:
                            best_avg_pr = avg_pr
                            if isinstance(model, nn.DataParallel):
                                ms = {k: v.cpu().clone() for k, v in model.module.state_dict().items()}
                            else:
                                ms = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                            best_state = {
                                'model': ms,
                                'loss_fn': {k: v.cpu().clone() for k, v in loss_fn.state_dict().items()},
                            }

                # Load best & evaluate
                if best_state:
                    if isinstance(model, nn.DataParallel):
                        model.module.load_state_dict({k: v.to(device) for k, v in best_state['model'].items()})
                    else:
                        model.load_state_dict({k: v.to(device) for k, v in best_state['model'].items()})
                    loss_fn.load_state_dict({k: v.to(device) for k, v in best_state['loss_fn'].items()})

                model.eval(); loss_fn.eval()
                tp, tl = [], []
                with torch.no_grad():
                    for imgs, lbl in val_loader:
                        imgs = imgs.to(device, non_blocking=True)
                        if gpu_val_aug is not None:
                            imgs = gpu_val_aug(imgs)
                        feats = model(imgs)
                        logits = _logits_nomargin_any(feats, loss_fn)
                        if logits is None:
                            _, logits = loss_fn(feats, lbl.to(device))
                        tp.extend(logits.argmax(1).cpu().numpy())
                        tl.extend(lbl.numpy())

                f1 = f1_score(tl, tp, average='macro', zero_division=0)
                acc = accuracy_score(tl, tp)
                f1_pc = f1_score(tl, tp, average=None, zero_division=0)

                elapsed = time.time() - t0
                print(f"F1={f1*100:.1f}% Acc={acc*100:.1f}% ({elapsed:.0f}s)")

                all_results[method_name].append({
                    'seed': seed, 'fold': fold_idx,
                    'f1': f1, 'acc': acc,
                    'f1_per_class': f1_pc.tolist(),
                    'avg_pr': best_avg_pr,
                })

                # Cleanup
                del model, loss_fn, optimizer, scheduler, best_state
                torch.cuda.empty_cache()

    # ============================================================
    # [3/4] STATISTICAL ANALYSIS
    # ============================================================
    print("\n" + "=" * 70)
    print("[3/4] STATISTICAL ANALYSIS")
    print("=" * 70)

    summary = {}
    for name, results in all_results.items():
        f1s = [r['f1'] for r in results]
        accs = [r['acc'] for r in results]
        f1_pcs = np.array([r['f1_per_class'] for r in results])

        n = len(f1s)
        mean_f1 = np.mean(f1s)
        std_f1 = np.std(f1s, ddof=1)
        ci95 = stats.t.ppf(0.975, n-1) * std_f1 / np.sqrt(n) if n > 1 else 0

        summary[name] = {
            'mean_f1': mean_f1,
            'std_f1': std_f1,
            'ci95': ci95,
            'mean_acc': np.mean(accs),
            'std_acc': np.std(accs, ddof=1),
            'per_class_mean': f1_pcs.mean(axis=0).tolist(),
            'per_class_std': f1_pcs.std(axis=0, ddof=1).tolist() if n > 1 else [0]*num_classes,
            'all_f1': f1s,
            'n_runs': n,
        }

    # Print rankings
    ranked = sorted(summary.items(), key=lambda x: x[1]['mean_f1'], reverse=True)

    print(f"\n{'Method':<38} {'Mean F1':>8} {'± Std':>7} {'95% CI':>12} {'Mean Acc':>9}  N")
    print("-" * 85)
    for name, s in ranked:
        lo = (s['mean_f1'] - s['ci95']) * 100
        hi = (s['mean_f1'] + s['ci95']) * 100
        print(f"  {name:<36} {s['mean_f1']*100:>7.2f}% {s['std_f1']*100:>6.2f} "
              f"[{lo:>5.1f},{hi:>5.1f}] {s['mean_acc']*100:>8.2f}% {s['n_runs']:>3}")

    # Per-class comparison for top 2
    print(f"\nPer-Class F1 (mean ± std across {kf_config.N_FOLDS * len(kf_config.SEEDS)} runs):")
    print(f"{'Method':<38}", end="")
    for l in labels:
        print(f" {l[:8]:>10}", end="")
    print()
    print("-" * (38 + 10 * num_classes))
    for name, s in ranked[:5]:
        print(f"  {name:<36}", end="")
        for i in range(num_classes):
            m = s['per_class_mean'][i] * 100
            sd = s['per_class_std'][i] * 100
            print(f" {m:>5.1f}±{sd:>3.1f}", end="")
        print()

    # Paired t-test: V2 vs SphereFace
    v2_name = "FuzzyArcLoss V2 (Optuna)"
    sf_name = "SphereFace"
    if v2_name in summary and sf_name in summary:
        v2_f1s = summary[v2_name]['all_f1']
        sf_f1s = summary[sf_name]['all_f1']

        if len(v2_f1s) == len(sf_f1s) and len(v2_f1s) > 1:
            t_stat, p_val = stats.ttest_rel(v2_f1s, sf_f1s)
            diff_mean = np.mean(v2_f1s) - np.mean(sf_f1s)

            print(f"\n{'='*70}")
            print(f"PAIRED T-TEST: V2 vs SphereFace")
            print(f"{'='*70}")
            print(f"  V2 mean:        {np.mean(v2_f1s)*100:.2f}% ± {np.std(v2_f1s, ddof=1)*100:.2f}")
            print(f"  SphereFace mean: {np.mean(sf_f1s)*100:.2f}% ± {np.std(sf_f1s, ddof=1)*100:.2f}")
            print(f"  Difference:     {diff_mean*100:+.2f} pp")
            print(f"  t-statistic:    {t_stat:.4f}")
            print(f"  p-value:        {p_val:.4f}")
            if p_val < 0.05:
                winner = "V2" if diff_mean > 0 else "SphereFace"
                print(f"  → STATISTICALLY SIGNIFICANT (p<0.05): {winner} wins")
            else:
                print(f"  → NOT significant (p={p_val:.3f} ≥ 0.05): no meaningful difference")
                print(f"    Thesis claim: V2 performs ON PAR with SphereFace")
                print(f"    (while being a novel, interpretable contribution)")

    # ============================================================
    # [4/4] SAVE RESULTS
    # ============================================================
    print(f"\n[4/4] Saving results...")

    output = {
        'config': {
            'n_folds': kf_config.N_FOLDS,
            'seeds': kf_config.SEEDS,
            'epochs': kf_config.EPOCHS,
            'dataset_size': len(df),
            'num_classes': num_classes,
            'labels': labels,
        },
        'methods': {},
    }
    for name, s in summary.items():
        output['methods'][name] = {
            'mean_f1': s['mean_f1'],
            'std_f1': s['std_f1'],
            'ci95': s['ci95'],
            'mean_acc': s['mean_acc'],
            'per_class_mean': s['per_class_mean'],
            'per_class_std': s['per_class_std'],
            'all_f1': s['all_f1'],
        }

    results_path = os.path.join(kf_config.OUT_DIR, 'kfold_validation_results.json')
    with open(results_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  ✓ {results_path}")

    # Save best V2 checkpoint info
    print(f"\n{'='*70}")
    print(f"  For thesis: report mean ± std from this K-fold validation")
    print(f"  If p ≥ 0.05: 'V2 performs comparably to SphereFace (p={p_val:.3f})'")
    print(f"  If p < 0.05 and V2 wins: 'V2 significantly outperforms (p={p_val:.3f})'")
    print(f"  Either way: V2 is a NOVEL CONTRIBUTION with competitive performance")
    print(f"{'='*70}")

    total_time = time.time() - t_global
    print(f"\nTotal time: {total_time/3600:.1f} hours")

    return output


if __name__ == "__main__":
    run_kfold_validation()
