"""
Pattern-Informed ABMIL Benchmark for Lung Cancer Mutation Prediction
=====================================================================
Compares 5 conditions on TCGA LUAD+LUSC cohort (5-fold CV):

  Baseline 1  : XGBoost on 7 pattern features (current approach)
  Baseline 2  : ABMIL on CTransPath embeddings only (768-d)
  Baseline 3  : ABMIL on pattern probabilities only (6-d)
  Proposed    : ABMIL on concat(embeddings, pattern_probs) (774-d)
  Ablation    : ABMIL on concat(embeddings, one-hot pattern labels) (774-d)

Expected directory layout
--------------------------
data/
  slides/
    <slide_id>/
      embeddings.npy          # (N_tiles, 768) float32 - CTransPath
      pattern_probs.npy       # (N_tiles, 6)   float32 - FuzzyArcLoss V2 softmax
      pattern_labels.npy      # (N_tiles,)     int64   - argmax of pattern_probs
  labels.csv                  # columns: slide_id, TP53, EGFR, KRAS, STK11, KEAP1, RBM10
                              #          (1=mutated, 0=WT, NaN=unknown)

Outputs
-------
results/
  metrics_<condition>_<gene>_fold<k>.json
  summary_table.csv
  roc_curves.png
  attention_examples/ (top-5 attended tiles per condition per slide, if tile coords available)
"""

import os
import json
import argparse
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    f1_score, classification_report
)
from sklearn.preprocessing import label_binarize
import xgboost as xgb

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

PATTERN_NAMES = [
    "acinar", "lepidic", "micropapillary",
    "mucinous", "papillary", "solid"
]

CONDITION_NAMES = [
    "baseline1_xgboost",
    "baseline2_abmil_embeddings",
    "baseline3_abmil_patterns",
    "proposed_abmil_concat",
    "ablation_abmil_onehot",
]

@dataclass
class Config:
    data_dir:         str  = "data"
    results_dir:      str  = "results"
    n_folds:          int  = 5
    seed:             int  = 42
    # ABMIL training
    abmil_epochs:     int  = 30
    abmil_lr:         float = 1e-4
    abmil_wd:         float = 1e-5
    abmil_hidden:     int  = 256
    abmil_attn_dim:   int  = 128
    abmil_dropout:    float = 0.25
    batch_size:       int  = 1          # bag-level (1 slide at a time)
    device:           str  = "cuda" if torch.cuda.is_available() else "cpu"
    # XGBoost
    xgb_n_estimators: int  = 300
    xgb_max_depth:    int  = 4
    xgb_lr:           float = 0.05
    # Evaluation
    min_positive_frac: float = 0.05     # skip gene if fewer positives
    genes: List[str] = field(default_factory=lambda: GENES)


# ──────────────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────────────

class SlideData:
    """Holds per-tile data for one slide."""
    def __init__(self, slide_id: str, data_dir: str):
        self.slide_id = slide_id
        slide_dir = Path(data_dir) / "slides" / slide_id

        emb_path    = slide_dir / "embeddings.npy"
        prob_path   = slide_dir / "pattern_probs.npy"
        label_path  = slide_dir / "pattern_labels.npy"

        # pattern_probs is always required (produced by prepare_benchmark_inputs.py)
        if not prob_path.exists():
            raise FileNotFoundError(f"Missing pattern_probs.npy for {slide_id}")
        self.pattern_probs  = np.load(prob_path).astype(np.float32)   # (N,6)

        if label_path.exists():
            self.pattern_labels = np.load(label_path).astype(np.int64) # (N,)
        else:
            self.pattern_labels = np.argmax(self.pattern_probs, axis=1)

        # embeddings are optional — only needed for ABMIL conditions
        # (produced by extract_embeddings.py — run that script first if needed)
        if emb_path.exists():
            self.embeddings = np.load(emb_path).astype(np.float32)    # (N,embed_dim)
            if self.embeddings.shape[0] != self.pattern_probs.shape[0]:
                raise ValueError(
                    f"Tile count mismatch for {slide_id}: "
                    f"embeddings={self.embeddings.shape[0]} vs probs={self.pattern_probs.shape[0]}"
                )
        else:
            self.embeddings = None   # will be caught if ABMIL condition is run

        assert self.pattern_probs.shape[1] == 6, \
            f"Expected 6 pattern classes, got {self.pattern_probs.shape[1]}"
        # store actual embedding dim (512 for projected, 768 for raw CTransPath)
        if self.embeddings is not None:
            self.embed_dim = self.embeddings.shape[1]
        else:
            self.embed_dim = None

    # ── slide-level XGBoost features ──────────────────────────────────────

    def xgboost_features(self) -> np.ndarray:
        """
        7-dim feature vector (6 pattern percentages + dominant pattern entropy).
        Matches the current production XGBoost feature set.
        """
        counts = np.bincount(self.pattern_labels, minlength=6)
        percentages = counts / max(counts.sum(), 1)            # (6,)
        entropy = -np.sum(
            percentages * np.log(percentages + 1e-9)
        )
        return np.concatenate([percentages, [entropy]])        # (7,)


# ── MIL bag dataset ──────────────────────────────────────────────────────────

class BagDataset(Dataset):
    """
    Returns (feature_tensor, label) for ABMIL training.
    feature_mode controls which input representation is used.
    """
    def __init__(
        self,
        slides:       List[SlideData],
        labels:       np.ndarray,   # (n_slides,) binary
        feature_mode: str,          # "embeddings" | "patterns" | "concat" | "onehot"
        max_tiles:    int = 4096,   # cap for memory; random sample during training
        training:     bool = True,
    ):
        self.slides       = slides
        self.labels       = labels
        self.feature_mode = feature_mode
        self.max_tiles    = max_tiles
        self.training     = training

    def __len__(self): return len(self.slides)

    def __getitem__(self, idx):
        slide = self.slides[idx]
        n     = slide.embeddings.shape[0]

        # optional tile subsampling during training
        if self.training and n > self.max_tiles:
            sel = np.random.choice(n, self.max_tiles, replace=False)
        else:
            sel = np.arange(n)

        probs = torch.from_numpy(slide.pattern_probs[sel])    # (N,6)

        if self.feature_mode == "patterns":
            feat = probs                                       # (N,6)
        else:
            # all other modes need embeddings
            if slide.embeddings is None:
                raise RuntimeError(
                    f"Slide {slide.slide_id} has no embeddings.npy.\n"
                    f"Run extract_embeddings.py first, then re-run the benchmark.\n"
                    f"Condition '{self.feature_mode}' requires CTransPath embeddings."
                )
            emb = torch.from_numpy(slide.embeddings[sel])     # (N,D)
            if self.feature_mode == "embeddings":
                feat = emb                                     # (N,D)
            elif self.feature_mode == "concat":
                feat = torch.cat([emb, probs], dim=1)         # (N,D+6)
            elif self.feature_mode == "onehot":
                one_hot = F.one_hot(
                    torch.from_numpy(slide.pattern_labels[sel]),
                    num_classes=6
                ).float()                                      # (N,6)
                feat = torch.cat([emb, one_hot], dim=1)       # (N,D+6)
            else:
                raise ValueError(f"Unknown feature_mode: {self.feature_mode}")

        label = torch.tensor(self.labels[idx], dtype=torch.float32)
        return feat, label                                     # (N,D), scalar


def collate_bags(batch):
    """Custom collate: bags have different tile counts."""
    feats, labels = zip(*batch)
    return list(feats), torch.stack(labels)


# ──────────────────────────────────────────────────────────────────────────────
# ABMIL model
# ──────────────────────────────────────────────────────────────────────────────

class GatedAttention(nn.Module):
    """
    Ilse et al. 2018 gated attention:
      a_i = softmax( w^T tanh(V h_i) ⊙ sigm(U h_i) )
    """
    def __init__(self, input_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.V = nn.Linear(input_dim, hidden_dim)
        self.U = nn.Linear(input_dim, hidden_dim)
        self.w = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, H: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        H : (N, D)  tile embeddings for one slide
        returns:
            z : (D,)    slide-level representation
            a : (N,)    attention weights (sum to 1)
        """
        A = self.w(torch.tanh(self.V(H)) * torch.sigmoid(self.U(H)))  # (N,1)
        A = torch.softmax(A, dim=0)                                     # (N,1)
        z = (A * H).sum(dim=0)                                          # (D,)
        return z, A.squeeze(1)                                          # (D,), (N,)


class ABMIL(nn.Module):
    """
    Attention-Based MIL for binary mutation prediction.

    Architecture:
      Tile encoder  : Linear → LayerNorm → ReLU → Dropout  [D → hidden]
      Attention      : GatedAttention                        [hidden → hidden]
      Classifier     : Linear → sigmoid                     [hidden → 1]
    """
    def __init__(
        self,
        input_dim:  int,
        hidden_dim: int = 256,
        attn_dim:   int = 128,
        dropout:    float = 0.25,
    ):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.attention  = GatedAttention(hidden_dim, attn_dim)
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(
        self,
        H: torch.Tensor,
        return_attention: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        H : (N, D)  raw tile features
        returns logit (scalar), attention weights (N,) if requested
        """
        h   = self.encoder(H)                         # (N, hidden)
        z, a = self.attention(h)                      # (hidden,), (N,)
        logit = self.classifier(z).squeeze(-1)        # scalar
        if return_attention:
            return logit, a
        return logit, None


# ──────────────────────────────────────────────────────────────────────────────
# Training & evaluation helpers
# ──────────────────────────────────────────────────────────────────────────────

def train_one_epoch(
    model:     nn.Module,
    loader:    DataLoader,
    optimizer: torch.optim.Optimizer,
    device:    str,
    pos_weight: torch.Tensor,
) -> float:
    model.train()
    total_loss = 0.0
    criterion  = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))

    for feats_list, labels in loader:
        labels = labels.to(device)
        optimizer.zero_grad()
        batch_loss = torch.tensor(0.0, device=device, requires_grad=True)

        for feat, label in zip(feats_list, labels):
            feat   = feat.to(device)
            logit, _ = model(feat)
            loss   = criterion(logit.unsqueeze(0), label.unsqueeze(0))
            batch_loss = batch_loss + loss

        batch_loss = batch_loss / len(feats_list)
        batch_loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        total_loss += batch_loss.item()

    return total_loss / max(len(loader), 1)


@torch.no_grad()
def evaluate(
    model:   nn.Module,
    loader:  DataLoader,
    device:  str,
) -> Dict[str, float]:
    model.eval()
    all_probs  = []
    all_labels = []

    for feats_list, labels in loader:
        for feat, label in zip(feats_list, labels):
            feat  = feat.to(device)
            logit, _ = model(feat)
            prob  = torch.sigmoid(logit).item()
            all_probs.append(prob)
            all_labels.append(label.item())

    all_probs  = np.array(all_probs)
    all_labels = np.array(all_labels)
    preds      = (all_probs >= 0.5).astype(int)

    metrics: Dict[str, float] = {}
    try:
        metrics["auroc"] = roc_auc_score(all_labels, all_probs)
    except ValueError:
        metrics["auroc"] = float("nan")
    try:
        metrics["auprc"] = average_precision_score(all_labels, all_probs)
    except ValueError:
        metrics["auprc"] = float("nan")
    metrics["f1"]  = f1_score(all_labels, preds, zero_division=0)
    metrics["probs"]  = all_probs.tolist()
    metrics["labels"] = all_labels.tolist()
    return metrics


def train_abmil(
    train_slides: List[SlideData],
    val_slides:   List[SlideData],
    train_labels: np.ndarray,
    val_labels:   np.ndarray,
    feature_mode: str,
    cfg:          Config,
) -> Tuple[nn.Module, Dict]:
    """Full train/val loop for one ABMIL condition and one fold."""

    # infer embed_dim from first training slide (supports 512-d or 768-d)
    embed_dim = next(
        (s.embed_dim for s in train_slides if s.embed_dim is not None), 512
    )
    dim_map = {
        "embeddings": embed_dim,
        "patterns":   6,
        "concat":     embed_dim + 6,
        "onehot":     embed_dim + 6,
    }
    input_dim = dim_map[feature_mode]

    model = ABMIL(
        input_dim  = input_dim,
        hidden_dim = cfg.abmil_hidden,
        attn_dim   = cfg.abmil_attn_dim,
        dropout    = cfg.abmil_dropout,
    ).to(cfg.device)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.abmil_lr, weight_decay=cfg.abmil_wd
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=cfg.abmil_epochs, eta_min=1e-6
    )

    # class imbalance correction
    pos_frac   = train_labels.mean()
    pos_weight = torch.tensor([(1 - pos_frac) / max(pos_frac, 1e-6)])

    train_ds = BagDataset(train_slides, train_labels, feature_mode, training=True)
    val_ds   = BagDataset(val_slides,   val_labels,   feature_mode, training=False)
    train_ld = DataLoader(train_ds, batch_size=1, shuffle=True,  collate_fn=collate_bags)
    val_ld   = DataLoader(val_ds,   batch_size=1, shuffle=False, collate_fn=collate_bags)

    best_auroc  = -1.0
    best_state  = None
    best_val    = {}

    for epoch in range(cfg.abmil_epochs):
        train_loss = train_one_epoch(model, train_ld, optimizer, cfg.device, pos_weight)
        val_metrics = evaluate(model, val_ld, cfg.device)
        scheduler.step()

        auroc = val_metrics.get("auroc", -1.0)
        if not np.isnan(auroc) and auroc > best_auroc:
            best_auroc = auroc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_val   = val_metrics

        if (epoch + 1) % 10 == 0:
            print(
                f"    epoch {epoch+1:3d}/{cfg.abmil_epochs} "
                f"loss={train_loss:.4f}  val_AUROC={auroc:.4f}"
            )

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, best_val


def train_xgboost(
    train_slides: List[SlideData],
    val_slides:   List[SlideData],
    train_labels: np.ndarray,
    val_labels:   np.ndarray,
    cfg:          Config,
) -> Dict:
    """XGBoost on 7 pattern features (Baseline 1)."""
    X_train = np.vstack([s.xgboost_features() for s in train_slides])
    X_val   = np.vstack([s.xgboost_features() for s in val_slides])

    scale_pos_weight = (train_labels == 0).sum() / max((train_labels == 1).sum(), 1)

    clf = xgb.XGBClassifier(
        n_estimators      = cfg.xgb_n_estimators,
        max_depth         = cfg.xgb_max_depth,
        learning_rate     = cfg.xgb_lr,
        scale_pos_weight  = scale_pos_weight,
        use_label_encoder = False,
        eval_metric       = "logloss",
        random_state      = cfg.seed,
        verbosity         = 0,
    )
    clf.fit(X_train, train_labels)

    probs  = clf.predict_proba(X_val)[:, 1]
    preds  = (probs >= 0.5).astype(int)
    labels = val_labels

    metrics: Dict[str, float] = {}
    try:
        metrics["auroc"] = roc_auc_score(labels, probs)
    except ValueError:
        metrics["auroc"] = float("nan")
    try:
        metrics["auprc"] = average_precision_score(labels, probs)
    except ValueError:
        metrics["auprc"] = float("nan")
    metrics["f1"]     = f1_score(labels, preds, zero_division=0)
    metrics["probs"]  = probs.tolist()
    metrics["labels"] = labels.tolist()

    # feature importances for interpretability
    metrics["feature_importances"] = dict(zip(
        PATTERN_NAMES + ["entropy"],
        clf.feature_importances_.tolist()
    ))
    return metrics


# ──────────────────────────────────────────────────────────────────────────────
# Main benchmark loop
# ──────────────────────────────────────────────────────────────────────────────

def run_benchmark(cfg: Config):
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)

    data_dir    = Path(cfg.data_dir)
    results_dir = Path(cfg.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Load labels ──────────────────────────────────────────────────────
    labels_df = pd.read_csv(data_dir / "labels.csv")
    labels_df.set_index("slide_id", inplace=True)

    slide_ids = [
        d.name for d in (data_dir / "slides").iterdir()
        if d.is_dir() and (d / "embeddings.npy").exists()
    ]
    print(f"Found {len(slide_ids)} slides with embeddings.")

    # keep only slides that appear in labels
    slide_ids = [s for s in slide_ids if s in labels_df.index]
    print(f"{len(slide_ids)} slides have mutation labels.")

    # ── 2. Load all slide data ───────────────────────────────────────────────
    print("Loading slide data …")
    all_slides: List[SlideData] = []
    for sid in slide_ids:
        try:
            all_slides.append(SlideData(sid, cfg.data_dir))
        except Exception as e:
            print(f"  WARNING: could not load {sid}: {e}")
    slide_ids = [s.slide_id for s in all_slides]
    print(f"Successfully loaded {len(all_slides)} slides.")

    # ── 3. Check which conditions are runnable ──────────────────────────────
    has_embeddings = any(
        (Path(cfg.data_dir) / "slides" / s.slide_id / "embeddings.npy").exists()
        for s in all_slides[:5]
    )
    needs_embeddings = {
        "baseline2_abmil_embeddings", "proposed_abmil_concat", "ablation_abmil_onehot"
    }
    if not has_embeddings:
        print("\n[WARNING] No embeddings.npy found in data/slides/.")
        print("  Conditions requiring embeddings will be SKIPPED:")
        for c in needs_embeddings:
            print(f"    - {c}")
        print("  Run extract_embeddings.py to enable these conditions.\n")
        active_conditions = [c for c in CONDITION_NAMES if c not in needs_embeddings]
    else:
        active_conditions = CONDITION_NAMES
    print(f"Active conditions: {active_conditions}\n")

    # ── 4. Per-gene, per-condition, k-fold benchmark ─────────────────────────
    all_results: Dict = {}   # [condition][gene][fold] → metrics

    for condition in active_conditions:
        all_results[condition] = {}

    for gene in cfg.genes:
        if gene not in labels_df.columns:
            print(f"Gene {gene} not in labels.csv — skipping.")
            continue

        gene_labels_raw = labels_df.loc[slide_ids, gene]
        valid_mask      = ~gene_labels_raw.isna()
        valid_slides    = [s for s, m in zip(all_slides, valid_mask) if m]
        valid_labels    = gene_labels_raw[valid_mask].values.astype(int)

        pos_frac = valid_labels.mean()
        print(f"\n{'='*60}")
        print(f"  Gene: {gene}  |  slides: {len(valid_slides)}  |  pos: {pos_frac:.1%}")
        print(f"{'='*60}")

        if pos_frac < cfg.min_positive_frac or pos_frac > (1 - cfg.min_positive_frac):
            print(f"  Skipping {gene}: class imbalance too extreme ({pos_frac:.1%} positive).")
            continue

        skf = StratifiedKFold(n_splits=cfg.n_folds, shuffle=True, random_state=cfg.seed)

        for condition in active_conditions:
            all_results[condition][gene] = []

        for fold_idx, (tr_idx, val_idx) in enumerate(
            skf.split(valid_slides, valid_labels)
        ):
            print(f"\n  ── Fold {fold_idx+1}/{cfg.n_folds} ──")
            tr_slides = [valid_slides[i] for i in tr_idx]
            va_slides = [valid_slides[i] for i in val_idx]
            tr_labels = valid_labels[tr_idx]
            va_labels = valid_labels[val_idx]

            # ── Baseline 1: XGBoost ─────────────────────────────────────
            print(f"  [baseline1_xgboost]")
            metrics = train_xgboost(tr_slides, va_slides, tr_labels, va_labels, cfg)
            all_results["baseline1_xgboost"][gene].append(
                {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
            )
            _save_fold(results_dir, "baseline1_xgboost", gene, fold_idx, metrics)
            print(f"    AUROC={metrics['auroc']:.4f}  F1={metrics['f1']:.4f}")

            # ── Baseline 2: ABMIL embeddings ─────────────────────────────
            if "baseline2_abmil_embeddings" in active_conditions:
                print(f"  [baseline2_abmil_embeddings]")
                _, metrics = train_abmil(
                    tr_slides, va_slides, tr_labels, va_labels, "embeddings", cfg
                )
                all_results["baseline2_abmil_embeddings"][gene].append(
                    {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
                )
                _save_fold(results_dir, "baseline2_abmil_embeddings", gene, fold_idx, metrics)
                print(f"    AUROC={metrics.get('auroc', float('nan')):.4f}  F1={metrics.get('f1', float('nan')):.4f}")

            # ── Baseline 3: ABMIL patterns ────────────────────────────────
            print(f"  [baseline3_abmil_patterns]")
            _, metrics = train_abmil(
                tr_slides, va_slides, tr_labels, va_labels, "patterns", cfg
            )
            all_results["baseline3_abmil_patterns"][gene].append(
                {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
            )
            _save_fold(results_dir, "baseline3_abmil_patterns", gene, fold_idx, metrics)
            print(f"    AUROC={metrics.get('auroc', float('nan')):.4f}  F1={metrics.get('f1', float('nan')):.4f}")

            # ── Proposed: ABMIL concat ────────────────────────────────────
            if "proposed_abmil_concat" in active_conditions:
                print(f"  [proposed_abmil_concat]")
                _, metrics = train_abmil(
                    tr_slides, va_slides, tr_labels, va_labels, "concat", cfg
                )
                all_results["proposed_abmil_concat"][gene].append(
                    {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
                )
                _save_fold(results_dir, "proposed_abmil_concat", gene, fold_idx, metrics)
                print(f"    AUROC={metrics.get('auroc', float('nan')):.4f}  F1={metrics.get('f1', float('nan')):.4f}")

            # ── Ablation: ABMIL one-hot ───────────────────────────────────
            if "ablation_abmil_onehot" in active_conditions:
                print(f"  [ablation_abmil_onehot]")
                _, metrics = train_abmil(
                    tr_slides, va_slides, tr_labels, va_labels, "onehot", cfg
                )
                all_results["ablation_abmil_onehot"][gene].append(
                    {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
                )
                _save_fold(results_dir, "ablation_abmil_onehot", gene, fold_idx, metrics)
                print(f"    AUROC={metrics.get('auroc', float('nan')):.4f}  F1={metrics.get('f1', float('nan')):.4f}")

    # ── 4. Aggregate and report ──────────────────────────────────────────────
    summary = build_summary(all_results, cfg, active_conditions)
    summary_path = results_dir / "summary_table.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\n\nSummary saved → {summary_path}")
    print(summary.to_string(index=False))

    # ── 5. Plots ─────────────────────────────────────────────────────────────
    plot_summary(summary, results_dir)
    print(f"Plots saved → {results_dir}/")


# ──────────────────────────────────────────────────────────────────────────────
# Utility: save, aggregate, plot
# ──────────────────────────────────────────────────────────────────────────────

def _save_fold(
    results_dir: Path, condition: str, gene: str, fold: int, metrics: Dict
):
    out = results_dir / f"metrics_{condition}_{gene}_fold{fold}.json"
    # strip large arrays before saving
    metrics_clean = {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
    with open(out, "w") as f:
        json.dump(metrics_clean, f, indent=2)


def build_summary(all_results: Dict, cfg: Config, active_conditions: list = None) -> pd.DataFrame:
    """Build a tidy summary DataFrame: condition × gene → mean±std AUROC/F1/AUPRC."""
    rows = []
    for condition in (active_conditions or CONDITION_NAMES):
        for gene in cfg.genes:
            fold_metrics = all_results[condition].get(gene, [])
            if not fold_metrics:
                continue
            aurocs = [m.get("auroc", np.nan) for m in fold_metrics]
            auprc  = [m.get("auprc", np.nan) for m in fold_metrics]
            f1s    = [m.get("f1",    np.nan) for m in fold_metrics]
            rows.append({
                "condition":  condition,
                "gene":       gene,
                "n_folds":    len(fold_metrics),
                "auroc_mean": np.nanmean(aurocs),
                "auroc_std":  np.nanstd(aurocs),
                "auprc_mean": np.nanmean(auprc),
                "auprc_std":  np.nanstd(auprc),
                "f1_mean":    np.nanmean(f1s),
                "f1_std":     np.nanstd(f1s),
            })
    return pd.DataFrame(rows)


def plot_summary(summary: pd.DataFrame, results_dir: Path):
    """Bar chart: AUROC per gene × condition."""
    genes      = summary["gene"].unique()
    conditions = CONDITION_NAMES
    n_genes    = len(genes)
    n_cond     = len(conditions)

    fig, axes = plt.subplots(1, n_genes, figsize=(4 * n_genes, 5), sharey=True)
    if n_genes == 1:
        axes = [axes]

    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]
    bar_w  = 0.15

    for ax, gene in zip(axes, genes):
        gene_df = summary[summary["gene"] == gene]
        for i, (cond, color) in enumerate(zip(conditions, colors)):
            row = gene_df[gene_df["condition"] == cond]
            if row.empty:
                continue
            auroc = row["auroc_mean"].values[0]
            std   = row["auroc_std"].values[0]
            x     = i * bar_w
            ax.bar(x, auroc, bar_w * 0.9, yerr=std, color=color,
                   label=cond if gene == genes[0] else "", capsize=4)
            ax.text(x, auroc + std + 0.01, f"{auroc:.2f}",
                    ha="center", fontsize=7, rotation=45)

        ax.set_title(gene, fontsize=11, fontweight="bold")
        ax.set_ylim(0.4, 1.05)
        ax.set_ylabel("AUROC" if gene == genes[0] else "")
        ax.set_xticks([])
        ax.axhline(0.5, color="gray", linestyle="--", linewidth=0.8)

    short_labels = [
        "B1\nXGB", "B2\nABMIL\nemb",
        "B3\nABMIL\npat", "Prop.\nconcat",
        "Abl.\none-hot"
    ]
    fig.legend(
        [plt.Rectangle((0,0),1,1, color=c) for c in colors],
        short_labels,
        loc="lower center", ncol=5, fontsize=8, frameon=False,
        bbox_to_anchor=(0.5, -0.05)
    )
    fig.suptitle(
        "Pattern-Informed ABMIL Benchmark — AUROC per Gene (mean ± std, 5-fold CV)",
        fontsize=12, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    fig.savefig(results_dir / "auroc_by_gene.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # ── AUROC heatmap ──────────────────────────────────────────────────────
    pivot = summary.pivot(index="condition", columns="gene", values="auroc_mean")
    pivot = pivot.reindex(conditions)
    fig2, ax2 = plt.subplots(figsize=(len(genes) * 1.4 + 1, 4))
    im = ax2.imshow(pivot.values, cmap="RdYlGn", vmin=0.5, vmax=0.9, aspect="auto")
    ax2.set_xticks(range(len(pivot.columns)))
    ax2.set_xticklabels(pivot.columns, fontsize=10)
    ax2.set_yticks(range(len(pivot.index)))
    ax2.set_yticklabels([c.replace("_", "\n") for c in pivot.index], fontsize=8)
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            val = pivot.values[r, c]
            if not np.isnan(val):
                ax2.text(c, r, f"{val:.3f}", ha="center", va="center", fontsize=8)
    plt.colorbar(im, ax=ax2, label="AUROC")
    ax2.set_title("AUROC Heatmap: Condition × Gene", fontsize=11)
    plt.tight_layout()
    fig2.savefig(results_dir / "auroc_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)


# ──────────────────────────────────────────────────────────────────────────────
# Attention visualisation (optional, requires tile coordinates)
# ──────────────────────────────────────────────────────────────────────────────

@torch.no_grad()
def get_top_attended_tiles(
    model:   ABMIL,
    slide:   SlideData,
    feature_mode: str,
    device:  str,
    top_k:   int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns (top_k tile indices, top_k attention weights)
    sorted descending by attention weight.
    """
    model.eval()
    emb   = torch.from_numpy(slide.embeddings).to(device)
    probs = torch.from_numpy(slide.pattern_probs).to(device)

    if feature_mode == "embeddings":
        feat = emb
    elif feature_mode == "patterns":
        feat = probs
    elif feature_mode == "concat":
        feat = torch.cat([emb, probs], dim=1)
    elif feature_mode == "onehot":
        one_hot = F.one_hot(
            torch.from_numpy(slide.pattern_labels).to(device),
            num_classes=6
        ).float()
        feat = torch.cat([emb, one_hot], dim=1)

    _, attn_weights = model(feat, return_attention=True)
    attn_np = attn_weights.cpu().numpy()
    top_idx = np.argsort(attn_np)[::-1][:top_k]
    return top_idx, attn_np[top_idx]


# ──────────────────────────────────────────────────────────────────────────────
# Synthetic data generator (for testing the pipeline without real data)
# ──────────────────────────────────────────────────────────────────────────────

def generate_synthetic_data(data_dir: str, n_slides: int = 60, seed: int = 42):
    """
    Creates a synthetic dataset so you can test the full pipeline
    without real TCGA data.

    Run once with:
        python pattern_informed_abmil_benchmark.py --generate_synthetic
    """
    rng = np.random.default_rng(seed)
    data_path = Path(data_dir)
    (data_path / "slides").mkdir(parents=True, exist_ok=True)

    slide_ids = [f"TCGA-SYNTH-{i:04d}" for i in range(n_slides)]
    label_rows = []

    for sid in slide_ids:
        n_tiles = rng.integers(300, 1500)
        emb     = rng.standard_normal((n_tiles, 512)).astype(np.float32)  # 512-d projected CTransPath
        logits  = rng.standard_normal((n_tiles, 6)).astype(np.float32)
        probs   = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        labels  = probs.argmax(axis=1)

        slide_dir = data_path / "slides" / sid
        slide_dir.mkdir(parents=True, exist_ok=True)
        np.save(slide_dir / "embeddings.npy",    emb)
        np.save(slide_dir / "pattern_probs.npy", probs)
        np.save(slide_dir / "pattern_labels.npy", labels)

        row = {"slide_id": sid}
        for gene in GENES:
            # ~30% positive rate, correlated weakly with solid % (pattern 4)
            solid_pct = (labels == 4).mean()
            p_mut     = 0.2 + 0.3 * solid_pct + 0.1 * rng.random()
            row[gene] = int(rng.random() < p_mut)
        label_rows.append(row)

    pd.DataFrame(label_rows).to_csv(data_path / "labels.csv", index=False)
    print(f"Synthetic dataset created: {n_slides} slides in {data_dir}/")


# ──────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pattern-Informed ABMIL Benchmark for Mutation Prediction"
    )
    parser.add_argument("--data_dir",          default="data",    help="Root data directory")
    parser.add_argument("--results_dir",       default="results", help="Output directory")
    parser.add_argument("--n_folds",           type=int,   default=5)
    parser.add_argument("--seed",              type=int,   default=42)
    parser.add_argument("--abmil_epochs",      type=int,   default=30)
    parser.add_argument("--abmil_lr",          type=float, default=1e-4)
    parser.add_argument("--abmil_hidden",      type=int,   default=256)
    parser.add_argument("--abmil_attn_dim",    type=int,   default=128)
    parser.add_argument("--abmil_dropout",     type=float, default=0.25)
    parser.add_argument("--xgb_n_estimators",  type=int,   default=300)
    parser.add_argument("--genes",             nargs="+",  default=GENES,
                        help="Genes to benchmark")
    parser.add_argument("--generate_synthetic", action="store_true",
                        help="Generate synthetic data for testing and exit")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.generate_synthetic:
        generate_synthetic_data(args.data_dir)
        exit(0)

    cfg = Config(
        data_dir         = args.data_dir,
        results_dir      = args.results_dir,
        n_folds          = args.n_folds,
        seed             = args.seed,
        abmil_epochs     = args.abmil_epochs,
        abmil_lr         = args.abmil_lr,
        abmil_hidden     = args.abmil_hidden,
        abmil_attn_dim   = args.abmil_attn_dim,
        abmil_dropout    = args.abmil_dropout,
        xgb_n_estimators = args.xgb_n_estimators,
        genes            = args.genes,
        device           = "cuda" if torch.cuda.is_available() else "cpu",
    )

    print(f"Device: {cfg.device}")
    print(f"Conditions: {CONDITION_NAMES}")
    print(f"Genes: {cfg.genes}")
    print(f"Folds: {cfg.n_folds}\n")

    run_benchmark(cfg)
