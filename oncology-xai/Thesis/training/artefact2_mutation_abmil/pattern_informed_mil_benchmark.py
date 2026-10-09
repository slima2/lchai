"""
Pattern-Informed ABMIL Benchmark — v2 LUAD Full Cohort
=======================================================
6 conditions × 6 genes × 5-fold stratified CV on TCGA-LUAD (~557 slides)

  Baseline 1  : XGBoost on 7 pattern features
  Baseline 2  : ABMIL on CTransPath embeddings only (512-d)
  Baseline 3  : ABMIL on pattern probabilities only (6-d)
  Proposed    : ABMIL on concat(embeddings, pattern_probs) (518-d)
  Ablation    : ABMIL on concat(embeddings, one-hot labels) (518-d)
  Fuzzy Choq. : Fuzzy Choquet MIL (embeddings + pattern memberships)

Changes vs v1:
  - --slide_list flag: restrict to LUAD-only slides (luad_slide_ids_available.txt)
  - Epoch-by-epoch progress for ALL ABMIL conditions
  - Progress bar within each epoch
  - Fuzzy Choquet included in bar chart + heatmap plots
  - Per-condition timing
  - Gene worker output includes GPU id and real-time fold summary

Run (LUAD-only, 6 GPUs):
  nohup python3 pattern_informed_abmil_benchmark_v2.py \\
    --data_dir   /home/rapids/notebooks/slima/data \\
    --results_dir /home/rapids/notebooks/slima/results_luad_full \\
    --slide_list /home/rapids/notebooks/slima/TGCA\\ MAF/luad_slide_ids_available.txt \\
    --abmil_epochs 50 \\
    --gene_parallel 6 \\
    > output_benchmark_luad_full.txt 2>&1 &
  tail -f output_benchmark_luad_full.txt
  tail -f /home/rapids/notebooks/slima/results_luad_full/logs/worker_*.txt
"""

import os, json, time, argparse, warnings
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
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
import xgboost as xgb

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=UserWarning)

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

PATTERN_NAMES = ["micropapillary", "cribriform", "papillary", "lepidic", "solid", "acinar"]

CONDITION_NAMES = [
    "baseline1_xgboost",
    "baseline2_abmil_embeddings",
    "baseline3_abmil_patterns",
    "proposed_abmil_concat",
    "ablation_abmil_onehot",
    "proposed_fuzzy_choquet",
]

CONDITION_LABELS = {
    "baseline1_xgboost":          "B1\nXGB",
    "baseline2_abmil_embeddings": "B2\nABMIL\nemb",
    "baseline3_abmil_patterns":   "B3\nABMIL\npat",
    "proposed_abmil_concat":      "Prop.\nconcat",
    "ablation_abmil_onehot":      "Abl.\none-hot",
    "proposed_fuzzy_choquet":     "Fuzzy\nChoquet",
}

CONDITION_COLORS = {
    "baseline1_xgboost":          "#4C72B0",
    "baseline2_abmil_embeddings": "#DD8452",
    "baseline3_abmil_patterns":   "#55A868",
    "proposed_abmil_concat":      "#C44E52",
    "ablation_abmil_onehot":      "#8172B2",
    "proposed_fuzzy_choquet":     "#937860",
}

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Config:
    data_dir:          str   = "data"
    results_dir:       str   = "results"
    slide_list:        Optional[str] = None   # path to txt with slide IDs (one per line)
    n_folds:           int   = 5
    seed:              int   = 42
    abmil_epochs:      int   = 50
    abmil_lr:          float = 1e-4
    abmil_wd:          float = 1e-5
    abmil_hidden:      int   = 256
    abmil_attn_dim:    int   = 128
    abmil_dropout:     float = 0.25
    batch_size:        int   = 1
    device:            str   = "cuda" if torch.cuda.is_available() else "cpu"
    xgb_n_estimators:  int   = 300
    xgb_max_depth:     int   = 4
    xgb_lr:            float = 0.05
    min_positive_frac: float = 0.05
    genes:             List[str] = field(default_factory=lambda: GENES)
    gpu_id:            Optional[int] = None   # for worker processes


# ══════════════════════════════════════════════════════════════════════════════
#  PROGRESS HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _tag(cfg: Config, gene: str = "") -> str:
    """Prefix for print statements: [GPU X | GENE]"""
    parts = []
    if cfg.gpu_id is not None:
        parts.append(f"GPU {cfg.gpu_id}")
    if gene:
        parts.append(gene)
    return f"[{' | '.join(parts)}] " if parts else ""


def _bar(current: int, total: int, width: int = 20) -> str:
    filled = int(width * current / max(total, 1))
    return f"[{'█'*filled}{'░'*(width-filled)}] {current}/{total}"


# ══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
class SlideData:
    def __init__(self, slide_id: str, data_dir: str):
        self.slide_id   = slide_id
        slide_dir       = Path(data_dir) / "slides" / slide_id
        prob_path       = slide_dir / "pattern_probs.npy"
        label_path      = slide_dir / "pattern_labels.npy"
        emb_path        = slide_dir / "embeddings.npy"

        if not prob_path.exists():
            raise FileNotFoundError(f"Missing pattern_probs.npy for {slide_id}")

        # Store paths only — arrays loaded on demand per fold to avoid OOM
        self._prob_path  = prob_path
        self._label_path = label_path if label_path.exists() else None
        self._emb_path   = emb_path if emb_path.exists() else None

        # Peek at shapes only (tiny read)
        tmp = np.load(str(prob_path), mmap_mode='r')
        self._n_tiles = tmp.shape[0]
        self.embed_dim = (int(np.load(str(emb_path), mmap_mode='r').shape[1])
                          if emb_path.exists() else None)
        # Arrays not loaded yet
        self.pattern_probs  = None
        self.pattern_labels = None
        self.embeddings     = None

    def load(self):
        """Load arrays into RAM. Call before training, unload after."""
        if self.pattern_probs is not None:
            return  # already loaded
        self.pattern_probs  = np.load(str(self._prob_path)).astype(np.float32)
        self.pattern_labels = (np.load(str(self._label_path)).astype(np.int64)
                               if self._label_path else
                               np.argmax(self.pattern_probs, axis=1))
        if self._emb_path:
            self.embeddings = np.load(str(self._emb_path)).astype(np.float32)
            n = min(self.embeddings.shape[0], self.pattern_probs.shape[0])
            self.embeddings     = self.embeddings[:n]
            self.pattern_probs  = self.pattern_probs[:n]
            self.pattern_labels = self.pattern_labels[:n]

    def unload(self):
        """Release arrays from RAM after fold completes."""
        self.pattern_probs  = None
        self.pattern_labels = None
        self.embeddings     = None

    def xgboost_features(self) -> np.ndarray:
        self.load()
        counts      = np.bincount(self.pattern_labels, minlength=6)
        percentages = counts / max(counts.sum(), 1)
        entropy     = -np.sum(percentages * np.log(percentages + 1e-9))
        return np.concatenate([percentages, [entropy]])   # (7,)


# ══════════════════════════════════════════════════════════════════════════════
#  BAG DATASET
# ══════════════════════════════════════════════════════════════════════════════
class BagDataset(Dataset):
    def __init__(self, slides, labels, feature_mode, max_tiles=4096, training=True):
        self.slides       = slides
        self.labels       = labels
        self.feature_mode = feature_mode
        self.max_tiles    = max_tiles
        self.training     = training

    def __len__(self): return len(self.slides)

    def __getitem__(self, idx):
        slide = self.slides[idx]
        n     = slide._n_tiles

        if self.training and n > self.max_tiles:
            sel = np.random.choice(n, self.max_tiles, replace=False)
        else:
            sel = np.arange(n)

        probs = torch.from_numpy(slide.pattern_probs[sel])

        if self.feature_mode == "patterns":
            feat = probs
        else:
            if slide.embeddings is None:
                raise RuntimeError(f"No embeddings.npy for {slide.slide_id}")
            emb = torch.from_numpy(slide.embeddings[sel])
            if self.feature_mode == "embeddings":
                feat = emb
            elif self.feature_mode == "concat":
                feat = torch.cat([emb, probs], dim=1)
            elif self.feature_mode == "onehot":
                oh   = F.one_hot(torch.from_numpy(slide.pattern_labels[sel]),
                                 num_classes=6).float()
                feat = torch.cat([emb, oh], dim=1)
            elif self.feature_mode == "choquet":
                feat = (emb, probs)
            else:
                raise ValueError(f"Unknown feature_mode: {self.feature_mode}")

        return feat, torch.tensor(self.labels[idx], dtype=torch.float32)


def collate_bags(batch):
    feats, labels = zip(*batch)
    if isinstance(feats[0], tuple):
        return list(feats), torch.stack(labels)
    return list(feats), torch.stack(labels)


# ══════════════════════════════════════════════════════════════════════════════
#  ABMIL MODEL
# ══════════════════════════════════════════════════════════════════════════════
class GatedAttention(nn.Module):
    def __init__(self, input_dim, hidden_dim=128):
        super().__init__()
        self.V = nn.Linear(input_dim, hidden_dim)
        self.U = nn.Linear(input_dim, hidden_dim)
        self.w = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, H):
        A = self.w(torch.tanh(self.V(H)) * torch.sigmoid(self.U(H)))
        A = torch.softmax(A, dim=0)
        return (A * H).sum(dim=0), A.squeeze(1)


class ABMIL(nn.Module):
    def __init__(self, input_dim, hidden_dim=256, attn_dim=128, dropout=0.25):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim), nn.ReLU(inplace=True),
            nn.Dropout(dropout),
        )
        self.attention  = GatedAttention(hidden_dim, attn_dim)
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(self, H, return_attention=False):
        h       = self.encoder(H)
        z, a    = self.attention(h)
        logit   = self.classifier(z).squeeze(-1)
        return (logit, a) if return_attention else (logit, None)


# ══════════════════════════════════════════════════════════════════════════════
#  FUZZY CHOQUET MIL
# ══════════════════════════════════════════════════════════════════════════════
class FuzzyMeasure(nn.Module):
    def __init__(self, n_patterns=6):
        super().__init__()
        self.K  = n_patterns
        self.v  = nn.Parameter(torch.ones(n_patterns) / n_patterns)
        self.v2 = nn.Parameter(torch.zeros(n_patterns, n_patterns))

    def measure(self, subset_mask):
        singleton   = (subset_mask * torch.sigmoid(self.v)).sum(dim=-1)
        v2_upper    = torch.triu(self.v2, diagonal=1)
        outer       = subset_mask.unsqueeze(-1) * subset_mask.unsqueeze(-2)
        interaction = (outer * v2_upper).sum(dim=(-1, -2))
        return torch.sigmoid(singleton + interaction)


class FuzzyChoquetAggregation(nn.Module):
    def __init__(self, embed_dim, n_patterns=6, hidden_dim=256, attn_dim=128, dropout=0.25):
        super().__init__()
        self.K             = n_patterns
        self.fuzzy_measure = FuzzyMeasure(n_patterns)
        self.encoder       = nn.Sequential(
            nn.Linear(embed_dim, hidden_dim),
            nn.LayerNorm(hidden_dim), nn.ReLU(inplace=True), nn.Dropout(dropout),
        )
        self.V_attn = nn.Linear(hidden_dim, attn_dim)
        self.U_attn = nn.Linear(hidden_dim, attn_dim)
        self.w_attn = nn.Linear(attn_dim, 1, bias=False)
        self.proj   = nn.Sequential(
            nn.Linear(n_patterns + hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim), nn.ReLU(inplace=True), nn.Dropout(dropout),
        )
        self.choquet_scale = nn.Parameter(torch.tensor(10.0))

    def choquet_integral(self, pattern_probs):
        N, K = pattern_probs.shape
        if N > 512:
            idx           = torch.randperm(N, device=pattern_probs.device)[:512]
            pattern_probs = pattern_probs[idx]
            N             = 512
        choquet_vals = torch.zeros(K, device=pattern_probs.device)
        for k in range(K):
            order      = torch.argsort(pattern_probs[:, k], descending=True)
            sorted_p   = pattern_probs[order]
            cumsum     = torch.cumsum(sorted_p, dim=0)
            ranks      = torch.arange(1, N+1, device=pattern_probs.device).float().unsqueeze(1)
            cum_mean   = cumsum / ranks
            mu_i       = self.fuzzy_measure.measure(cum_mean)
            mu_i1      = torch.cat([mu_i[1:], torch.zeros(1, device=pattern_probs.device)])
            choquet_vals[k] = (sorted_p[:, k] * (mu_i - mu_i1)).sum()
        return choquet_vals

    def forward(self, H, probs):
        h      = self.encoder(H)
        A      = self.w_attn(torch.tanh(self.V_attn(h)) * torch.sigmoid(self.U_attn(h)))
        A      = torch.softmax(A, dim=0)
        z_attn = (A * h).sum(dim=0)
        cv     = self.choquet_integral(probs) * self.choquet_scale
        z      = self.proj(torch.cat([cv, z_attn]))
        return z, A.squeeze(1)


class FuzzyChoquetMIL(nn.Module):
    def __init__(self, embed_dim, n_patterns=6, hidden_dim=256, attn_dim=128, dropout=0.25):
        super().__init__()
        self.aggregator = FuzzyChoquetAggregation(embed_dim, n_patterns, hidden_dim, attn_dim, dropout)
        self.classifier = nn.Linear(hidden_dim, 1)

    def forward(self, inputs, return_attention=False):
        H, probs = inputs
        z, a     = self.aggregator(H, probs)
        logit    = self.classifier(z).squeeze(-1)
        return (logit, a) if return_attention else (logit, None)


# ══════════════════════════════════════════════════════════════════════════════
#  TRAINING UTILITIES
# ══════════════════════════════════════════════════════════════════════════════
def _to_device(feat, device):
    if isinstance(feat, (tuple, list)):
        return (feat[0].to(device), feat[1].to(device))
    return feat.to(device)


def train_one_epoch(model, loader, optimizer, device, pos_weight):
    model.train()
    criterion  = nn.BCEWithLogitsLoss(pos_weight=pos_weight.to(device))
    total_loss = 0.0
    n_slides   = 0

    for feats_list, labels in loader:
        labels = labels.to(device)
        optimizer.zero_grad()
        batch_loss = torch.tensor(0.0, device=device, requires_grad=True)
        for feat, label in zip(feats_list, labels):
            feat      = _to_device(feat, device)
            logit, _  = model(feat)
            loss      = criterion(logit.unsqueeze(0), label.unsqueeze(0))
            batch_loss = batch_loss + loss
            n_slides  += 1
        batch_loss = batch_loss / len(feats_list)
        batch_loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        total_loss += batch_loss.item()

    return total_loss / max(len(loader), 1)


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    all_probs, all_labels = [], []
    for feats_list, labels in loader:
        for feat, label in zip(feats_list, labels):
            feat     = _to_device(feat, device)
            logit, _ = model(feat)
            all_probs.append(torch.sigmoid(logit).item())
            all_labels.append(label.item())

    probs  = np.array(all_probs)
    labels = np.array(all_labels)
    preds  = (probs >= 0.5).astype(int)
    m: Dict = {}
    try:    m["auroc"] = roc_auc_score(labels, probs)
    except: m["auroc"] = float("nan")
    try:    m["auprc"] = average_precision_score(labels, probs)
    except: m["auprc"] = float("nan")
    m["f1"]     = f1_score(labels, preds, zero_division=0)
    m["probs"]  = probs.tolist()
    m["labels"] = labels.tolist()
    return m


def _make_loaders(tr_slides, va_slides, tr_labels, va_labels, mode, training=True):
    tr_ds = BagDataset(tr_slides, tr_labels, mode, training=True)
    va_ds = BagDataset(va_slides, va_labels, mode, training=False)
    tr_ld = DataLoader(tr_ds, batch_size=1, shuffle=True,  collate_fn=collate_bags)
    va_ld = DataLoader(va_ds, batch_size=1, shuffle=False, collate_fn=collate_bags)
    return tr_ld, va_ld


def _abmil_loop(model, tr_ld, va_ld, cfg, pos_weight, tag, condition, gene, fold):
    """Shared train loop with epoch-by-epoch progress for all ABMIL variants."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.abmil_lr, weight_decay=cfg.abmil_wd)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.abmil_epochs, eta_min=1e-6)

    best_auroc, best_state, best_val = -1.0, None, {}
    patience, no_improve = 15, 0
    t0 = time.time()

    print(f"  {tag}  ┌─ {condition} | {gene} fold{fold+1} | {cfg.abmil_epochs} epochs", flush=True)

    for epoch in range(cfg.abmil_epochs):
        loss  = train_one_epoch(model, tr_ld, optimizer, cfg.device, pos_weight)
        val_m = evaluate(model, va_ld, cfg.device)
        scheduler.step()

        auroc = val_m.get("auroc", float("nan"))
        f1    = val_m.get("f1", float("nan"))
        mark  = " ★" if (not np.isnan(auroc) and auroc > best_auroc) else ""

        print(
            f"  {tag}  │  ep {epoch+1:3d}/{cfg.abmil_epochs}"
            f"  loss={loss:.4f}"
            f"  AUROC={auroc:.4f}"
            f"  F1={f1:.4f}"
            f"  lr={scheduler.get_last_lr()[0]:.2e}"
            f"{mark}",
            flush=True
        )

        if not np.isnan(auroc) and auroc > best_auroc:
            best_auroc = auroc
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_val   = val_m
            no_improve = 0
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"  {tag}  │  Early stop at epoch {epoch+1}", flush=True)
                break

    elapsed = time.time() - t0
    print(
        f"  {tag}  └─ Best AUROC={best_auroc:.4f}  ({elapsed:.0f}s)",
        flush=True
    )
    if best_state:
        # ── Save best checkpoint to disk ──────────────────────────────────
        ckpt_dir = Path(cfg.results_dir) / "checkpoints"
        ckpt_dir.mkdir(parents=True, exist_ok=True)
        ckpt_path = ckpt_dir / f"ckpt_{condition}_{gene}_fold{fold}.pth"
        torch.save(best_state, ckpt_path)
        print(f"  {tag}  ✓ checkpoint → {ckpt_path.name}", flush=True)
        # ─────────────────────────────────────────────────────────────────
        model.load_state_dict(best_state)
    return model, best_val


# ══════════════════════════════════════════════════════════════════════════════
#  CONDITION TRAINERS
# ══════════════════════════════════════════════════════════════════════════════
def train_abmil(tr_slides, va_slides, tr_labels, va_labels, mode, cfg, tag, gene, fold):
    embed_dim = next((s.embed_dim for s in tr_slides if s.embed_dim is not None), 512)
    input_dim = {"embeddings": embed_dim, "patterns": 6,
                 "concat": embed_dim+6, "onehot": embed_dim+6}[mode]

    model = ABMIL(input_dim, cfg.abmil_hidden, cfg.abmil_attn_dim, cfg.abmil_dropout).to(cfg.device)
    pos_frac   = tr_labels.mean()
    pos_weight = torch.tensor([(1 - pos_frac) / max(pos_frac, 1e-6)])
    tr_ld, va_ld = _make_loaders(tr_slides, va_slides, tr_labels, va_labels, mode)

    cond_name = {"embeddings": "baseline2_abmil_embeddings", "patterns": "baseline3_abmil_patterns",
                 "concat": "proposed_abmil_concat", "onehot": "ablation_abmil_onehot"}[mode]
    return _abmil_loop(model, tr_ld, va_ld, cfg, pos_weight, tag, cond_name, gene, fold)


def train_fuzzy_choquet(tr_slides, va_slides, tr_labels, va_labels, cfg, tag, gene, fold):
    embed_dim  = next((s.embed_dim for s in tr_slides if s.embed_dim is not None), 512)
    model      = FuzzyChoquetMIL(embed_dim, 6, cfg.abmil_hidden, cfg.abmil_attn_dim, cfg.abmil_dropout).to(cfg.device)
    n_pos      = tr_labels.sum()
    n_neg      = len(tr_labels) - n_pos
    pos_weight = torch.tensor([n_neg / max(n_pos, 1)], dtype=torch.float32)
    tr_ld, va_ld = _make_loaders(tr_slides, va_slides, tr_labels, va_labels, "choquet")

    model, best_val = _abmil_loop(model, tr_ld, va_ld, cfg, pos_weight, tag, "proposed_fuzzy_choquet", gene, fold)

    # Save fuzzy measure for interpretability
    fm  = model.aggregator.fuzzy_measure
    shv = torch.sigmoid(fm.v).detach().cpu().numpy()
    v2u = torch.triu(fm.v2, diagonal=1).detach().cpu().numpy()
    best_val["fuzzy_shapley_values"] = dict(zip(PATTERN_NAMES, shv.tolist()))
    best_val["fuzzy_interactions"]   = {
        f"{PATTERN_NAMES[i]}×{PATTERN_NAMES[j]}": float(v2u[i, j])
        for i in range(6) for j in range(i+1, 6)
    }
    return model, best_val


def train_xgboost(tr_slides, va_slides, tr_labels, va_labels, cfg, tag, gene, fold):
    t0 = time.time()
    print(f"  {tag}  ┌─ baseline1_xgboost | {gene} fold{fold+1}", flush=True)
    X_tr = np.vstack([s.xgboost_features() for s in tr_slides])
    X_va = np.vstack([s.xgboost_features() for s in va_slides])
    spw  = (tr_labels == 0).sum() / max((tr_labels == 1).sum(), 1)
    clf  = xgb.XGBClassifier(
        n_estimators=cfg.xgb_n_estimators, max_depth=cfg.xgb_max_depth,
        learning_rate=cfg.xgb_lr, scale_pos_weight=spw,
        use_label_encoder=False, eval_metric="logloss",
        random_state=cfg.seed, verbosity=0,
    )
    clf.fit(X_tr, tr_labels)
    probs = clf.predict_proba(X_va)[:, 1]
    preds = (probs >= 0.5).astype(int)
    m: Dict = {}
    try:    m["auroc"] = roc_auc_score(va_labels, probs)
    except: m["auroc"] = float("nan")
    try:    m["auprc"] = average_precision_score(va_labels, probs)
    except: m["auprc"] = float("nan")
    m["f1"]                   = f1_score(va_labels, preds, zero_division=0)
    m["probs"]                = probs.tolist()
    m["labels"]               = va_labels.tolist()
    m["feature_importances"]  = dict(zip(PATTERN_NAMES + ["entropy"], clf.feature_importances_.tolist()))
    elapsed = time.time() - t0
    print(f"  {tag}  └─ AUROC={m['auroc']:.4f}  F1={m['f1']:.4f}  ({elapsed:.0f}s)", flush=True)
    return m


# ══════════════════════════════════════════════════════════════════════════════
#  SAVE / AGGREGATE / PLOT
# ══════════════════════════════════════════════════════════════════════════════
def _save_fold(results_dir, condition, gene, fold, metrics):
    out = Path(results_dir) / f"metrics_{condition}_{gene}_fold{fold}.json"
    clean = {k: v for k, v in metrics.items() if k not in ("probs", "labels")}
    with open(out, "w") as f:
        json.dump(clean, f, indent=2)


def build_summary(all_results, cfg, active_conditions=None):
    rows = []
    for condition in (active_conditions or CONDITION_NAMES):
        for gene in cfg.genes:
            fold_metrics = all_results.get(condition, {}).get(gene, [])
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


def plot_summary(summary, results_dir):
    results_dir = Path(results_dir)
    if summary.empty or "gene" not in summary.columns:
        print("plot_summary: empty summary — skipping.")
        return
    genes       = sorted(summary["gene"].unique())
    conditions  = [c for c in CONDITION_NAMES if c in summary["condition"].values]
    n_genes     = len(genes)
    n_cond      = len(conditions)
    bar_w       = 0.13

    fig, axes = plt.subplots(1, n_genes, figsize=(4.5 * n_genes, 5.5), sharey=True)
    if n_genes == 1:
        axes = [axes]

    for ax, gene in zip(axes, genes):
        gene_df = summary[summary["gene"] == gene]
        for i, cond in enumerate(conditions):
            row = gene_df[gene_df["condition"] == cond]
            if row.empty:
                continue
            auroc = row["auroc_mean"].values[0]
            std   = row["auroc_std"].values[0]
            x     = i * (bar_w + 0.01)
            color = CONDITION_COLORS[cond]
            ax.bar(x, auroc, bar_w, yerr=std, color=color, capsize=3,
                   label=CONDITION_LABELS[cond] if gene == genes[0] else "")
            ax.text(x, auroc + std + 0.005, f"{auroc:.2f}",
                    ha="center", fontsize=7.5, rotation=0)
        ax.set_title(gene, fontsize=12, fontweight="bold")
        ax.set_ylim(0.4, 1.05)
        ax.set_ylabel("AUROC" if gene == genes[0] else "")
        ax.set_xticks([])
        ax.axhline(0.5, color="gray", ls="--", lw=0.8)

    handles = [plt.Rectangle((0,0),1,1, color=CONDITION_COLORS[c]) for c in conditions]
    labels  = [CONDITION_LABELS[c] for c in conditions]
    fig.legend(handles, labels, loc="lower center", ncol=len(conditions),
               fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.05))
    fig.suptitle(
        "Pattern-Informed ABMIL Benchmark — AUROC per Gene (mean ± std, 5-fold CV)",
        fontsize=12, fontweight="bold", y=1.02
    )
    plt.tight_layout()
    fig.savefig(results_dir / "auroc_by_gene.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Heatmap
    pivot = summary.pivot(index="condition", columns="gene", values="auroc_mean")
    pivot = pivot.reindex([c for c in CONDITION_NAMES if c in pivot.index])
    fig2, ax2 = plt.subplots(figsize=(len(genes)*1.5+1, len(conditions)*0.7+1))
    im = ax2.imshow(pivot.values, cmap="RdYlGn", vmin=0.5, vmax=0.9, aspect="auto")
    ax2.set_xticks(range(len(pivot.columns)));  ax2.set_xticklabels(pivot.columns, fontsize=10)
    ax2.set_yticks(range(len(pivot.index)));
    ax2.set_yticklabels([c.replace("_", "\n") for c in pivot.index], fontsize=8)
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            val = pivot.values[r, c]
            if not np.isnan(val):
                ax2.text(c, r, f"{val:.3f}", ha="center", va="center", fontsize=9)
    plt.colorbar(im, ax=ax2, label="AUROC")
    ax2.set_title("AUROC Heatmap: Condition × Gene", fontsize=11)
    plt.tight_layout()
    fig2.savefig(results_dir / "auroc_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"Plots saved → {results_dir}/auroc_by_gene.png  auroc_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN BENCHMARK LOOP
# ══════════════════════════════════════════════════════════════════════════════
def run_benchmark(cfg: Config):
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)

    data_dir    = Path(cfg.data_dir)
    results_dir = Path(cfg.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    tag = _tag(cfg)

    # Load labels
    labels_df = pd.read_csv(data_dir / "labels.csv")
    labels_df.set_index("slide_id", inplace=True)

    # Determine slide list
    if cfg.slide_list and Path(cfg.slide_list).exists():
        with open(cfg.slide_list) as f:
            allowed = set(l.strip() for l in f if l.strip())
        print(f"{tag}Using slide_list: {len(allowed)} slides from {cfg.slide_list}", flush=True)
    else:
        allowed = None

    # Discover slides
    slide_ids = [
        d.name for d in (data_dir / "slides").iterdir()
        if d.is_dir()
        and (d / "embeddings.npy").exists()
        and (d / "pattern_probs.npy").exists()
        and (allowed is None or d.name in allowed)
    ]
    slide_ids = [s for s in slide_ids if s in labels_df.index]
    print(f"{tag}Slides found: {len(slide_ids)}", flush=True)

    # Load slide data
    all_slides = []
    for sid in slide_ids:
        try:
            all_slides.append(SlideData(sid, cfg.data_dir))
        except Exception as e:
            print(f"{tag}WARNING: skip {sid}: {e}", flush=True)
    slide_ids = [s.slide_id for s in all_slides]
    print(f"{tag}Slides loaded: {len(all_slides)}", flush=True)

    has_embeddings = any(s._emb_path is not None for s in all_slides[:5])
    needs_emb = {"baseline2_abmil_embeddings", "proposed_abmil_concat",
                 "ablation_abmil_onehot", "proposed_fuzzy_choquet"}
    active_conditions = CONDITION_NAMES if has_embeddings else [c for c in CONDITION_NAMES if c not in needs_emb]
    print(f"{tag}Active conditions: {active_conditions}\n", flush=True)

    all_results = {c: {} for c in active_conditions}

    for gene in cfg.genes:
        if gene not in labels_df.columns:
            print(f"{tag}Gene {gene} not in labels.csv — skip", flush=True)
            continue

        gene_labels_raw = labels_df.loc[slide_ids, gene]
        valid_mask      = ~gene_labels_raw.isna()
        valid_slides    = [s for s, m in zip(all_slides, valid_mask) if m]
        valid_labels    = gene_labels_raw[valid_mask].values.astype(int)
        pos_frac        = valid_labels.mean()

        print(f"\n{tag}{'='*60}", flush=True)
        print(f"{tag}Gene: {gene}  slides={len(valid_slides)}  pos={pos_frac:.1%}", flush=True)
        print(f"{tag}{'='*60}", flush=True)

        if pos_frac < cfg.min_positive_frac or pos_frac > 1 - cfg.min_positive_frac:
            print(f"{tag}SKIP {gene}: extreme imbalance ({pos_frac:.1%})", flush=True)
            continue

        skf = StratifiedKFold(n_splits=cfg.n_folds, shuffle=True, random_state=cfg.seed)
        for c in active_conditions:
            all_results[c][gene] = []

        for fold_idx, (tr_idx, va_idx) in enumerate(skf.split(valid_slides, valid_labels)):
            print(f"\n{tag}── Fold {fold_idx+1}/{cfg.n_folds} "
                  f"(train={len(tr_idx)}, val={len(va_idx)}) ──", flush=True)
            tr_sl = [valid_slides[i] for i in tr_idx]
            va_sl = [valid_slides[i] for i in va_idx]
            tr_lb = valid_labels[tr_idx]
            va_lb = valid_labels[va_idx]

            # Load only this fold's slides into RAM (~2GB max), unload after
            print(f"{tag}  Loading fold {fold_idx+1} slides...", flush=True)
            for s in tr_sl + va_sl:
                s.load()
            print(f"{tag}  Fold loaded ({len(tr_sl)+len(va_sl)} slides)", flush=True)

            # Baseline 1 — XGBoost
            if "baseline1_xgboost" in active_conditions:
                m = train_xgboost(tr_sl, va_sl, tr_lb, va_lb, cfg, tag, gene, fold_idx)
                all_results["baseline1_xgboost"][gene].append(m)
                _save_fold(results_dir, "baseline1_xgboost", gene, fold_idx, m)

            # Baseline 2 — ABMIL embeddings
            if "baseline2_abmil_embeddings" in active_conditions:
                _, m = train_abmil(tr_sl, va_sl, tr_lb, va_lb, "embeddings", cfg, tag, gene, fold_idx)
                all_results["baseline2_abmil_embeddings"][gene].append(m)
                _save_fold(results_dir, "baseline2_abmil_embeddings", gene, fold_idx, m)

            # Baseline 3 — ABMIL patterns
            if "baseline3_abmil_patterns" in active_conditions:
                _, m = train_abmil(tr_sl, va_sl, tr_lb, va_lb, "patterns", cfg, tag, gene, fold_idx)
                all_results["baseline3_abmil_patterns"][gene].append(m)
                _save_fold(results_dir, "baseline3_abmil_patterns", gene, fold_idx, m)

            # Proposed — concat
            if "proposed_abmil_concat" in active_conditions:
                _, m = train_abmil(tr_sl, va_sl, tr_lb, va_lb, "concat", cfg, tag, gene, fold_idx)
                all_results["proposed_abmil_concat"][gene].append(m)
                _save_fold(results_dir, "proposed_abmil_concat", gene, fold_idx, m)

            # Ablation — one-hot
            if "ablation_abmil_onehot" in active_conditions:
                _, m = train_abmil(tr_sl, va_sl, tr_lb, va_lb, "onehot", cfg, tag, gene, fold_idx)
                all_results["ablation_abmil_onehot"][gene].append(m)
                _save_fold(results_dir, "ablation_abmil_onehot", gene, fold_idx, m)

            # Fuzzy Choquet
            if "proposed_fuzzy_choquet" in active_conditions:
                _, m = train_fuzzy_choquet(tr_sl, va_sl, tr_lb, va_lb, cfg, tag, gene, fold_idx)
                all_results["proposed_fuzzy_choquet"][gene].append(m)
                _save_fold(results_dir, "proposed_fuzzy_choquet", gene, fold_idx, m)

            # Unload fold slides from RAM
            for s in tr_sl + va_sl:
                s.unload()

            # Fold summary
            print(f"\n{tag}── Fold {fold_idx+1} summary for {gene}:", flush=True)
            for c in active_conditions:
                fold_list = all_results[c][gene]
                if fold_list:
                    last = fold_list[-1]
                    print(f"  {tag}  {c:<36} AUROC={last.get('auroc', float('nan')):.4f}"
                          f"  F1={last.get('f1', float('nan')):.4f}", flush=True)

    summary      = build_summary(all_results, cfg, active_conditions)
    summary_path = results_dir / "summary_table.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\n{tag}Summary → {summary_path}", flush=True)
    print(summary.to_string(index=False), flush=True)
    plot_summary(summary, results_dir)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI & PARALLEL LAUNCHER
# ══════════════════════════════════════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data_dir",         default="/home/rapids/notebooks/slima/data")
    p.add_argument("--results_dir",      default="/home/rapids/notebooks/slima/results_luad_full")
    p.add_argument("--slide_list",       default=None,
                   help="Path to txt file with one slide_id per line (e.g. luad_slide_ids_available.txt)")
    p.add_argument("--n_folds",          type=int,   default=5)
    p.add_argument("--seed",             type=int,   default=42)
    p.add_argument("--abmil_epochs",     type=int,   default=50)
    p.add_argument("--abmil_lr",         type=float, default=1e-4)
    p.add_argument("--abmil_hidden",     type=int,   default=256)
    p.add_argument("--abmil_attn_dim",   type=int,   default=128)
    p.add_argument("--abmil_dropout",    type=float, default=0.25)
    p.add_argument("--xgb_n_estimators", type=int,   default=300)
    p.add_argument("--genes",            nargs="+",  default=GENES)
    p.add_argument("--gene_parallel",    type=int,   default=0,
                   help="Number of GPUs — spawns one subprocess per gene. 0=sequential.")
    p.add_argument("--_gene_worker",     default=None, help=argparse.SUPPRESS)
    p.add_argument("--_gpu_id",          type=int,   default=None, help=argparse.SUPPRESS)
    return p.parse_args()


if __name__ == "__main__":
    import subprocess, sys
    args = parse_args()

    # ── Gene-parallel orchestrator ──────────────────────────────────────────
    if args.gene_parallel > 0 and args._gene_worker is None:
        n_gpus   = args.gene_parallel
        log_dir  = Path(args.results_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        procs    = {}

        print(f"[ORCHESTRATOR] {len(args.genes)} genes across {n_gpus} GPUs")
        for i, gene in enumerate(args.genes):
            gpu_id   = i % n_gpus
            log_path = log_dir / f"worker_{gene}.txt"
            cmd = [
                sys.executable, sys.argv[0],
                "--data_dir",         args.data_dir,
                "--results_dir",      args.results_dir,
                "--n_folds",          str(args.n_folds),
                "--seed",             str(args.seed),
                "--abmil_epochs",     str(args.abmil_epochs),
                "--abmil_lr",         str(args.abmil_lr),
                "--abmil_hidden",     str(args.abmil_hidden),
                "--abmil_attn_dim",   str(args.abmil_attn_dim),
                "--abmil_dropout",    str(args.abmil_dropout),
                "--xgb_n_estimators", str(args.xgb_n_estimators),
                "--genes",            gene,
                "--_gene_worker",     gene,
                "--_gpu_id",          str(gpu_id),
            ]
            if args.slide_list:
                cmd += ["--slide_list", args.slide_list]
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
            fh = open(log_path, "w")
            pr = subprocess.Popen(cmd, stdout=fh, stderr=fh, env=env)
            procs[gene] = (pr, fh, log_path)
            print(f"  [GPU {gpu_id}] {gene} → PID {pr.pid}  log: {log_path}")
            time.sleep(0.5)

        print(f"\nMonitor all genes:  tail -f {log_dir}/worker_*.txt")
        print(f"Monitor one gene:   tail -f {log_dir}/worker_TP53.txt\n")

        while True:
            time.sleep(30)
            done      = {g: pr.poll() for g, (pr, _, _) in procs.items()}
            n_run     = sum(1 for rc in done.values() if rc is None)
            n_ok      = sum(1 for rc in done.values() if rc == 0)
            n_fail    = sum(1 for rc in done.values() if rc not in (None, 0))
            n_json    = len(list(Path(args.results_dir).glob("metrics_*.json")))
            expected  = len(args.genes) * args.n_folds * len(CONDITION_NAMES)
            print(f"  [{time.strftime('%H:%M:%S')}]  "
                  f"Running={n_run}  OK={n_ok}  Failed={n_fail}  "
                  f"JSONs={n_json}/{expected}", flush=True)
            if all(rc is not None for rc in done.values()):
                break

        for g, (pr, fh, _) in procs.items():
            fh.close()

        failed = [g for g, (pr, _, _) in procs.items() if pr.returncode != 0]
        if failed:
            print(f"\n[ORCHESTRATOR] WARNING: failed genes: {failed}")
        else:
            print(f"\n[ORCHESTRATOR] All genes completed!")

        # Aggregate all JSON results
        print("\n[ORCHESTRATOR] Aggregating results …")
        all_results = {c: {} for c in CONDITION_NAMES}
        for jp in sorted(Path(args.results_dir).glob("metrics_*.json")):
            stem  = jp.stem
            gene  = next((g for g in GENES if g in stem), None)
            if gene is None: continue
            fold  = int(stem.split("_fold")[-1])
            cend  = stem.rfind(f"_{gene}_fold")
            cond  = stem[len("metrics_"):cend]
            if cond not in all_results: continue
            if gene not in all_results[cond]:
                all_results[cond][gene] = []
            with open(jp) as f:
                all_results[cond][gene].append(json.load(f))

        active = [c for c in CONDITION_NAMES if any(all_results[c].values())]
        cfg = Config(
            data_dir=args.data_dir, results_dir=args.results_dir,
            n_folds=args.n_folds, seed=args.seed,
            abmil_epochs=args.abmil_epochs, abmil_lr=args.abmil_lr,
            abmil_hidden=args.abmil_hidden, abmil_attn_dim=args.abmil_attn_dim,
            abmil_dropout=args.abmil_dropout, xgb_n_estimators=args.xgb_n_estimators,
            genes=args.genes,
        )
        summary = build_summary(all_results, cfg, active)
        summary.to_csv(Path(args.results_dir) / "summary_table.csv", index=False)
        print(summary.to_string(index=False))
        plot_summary(summary, args.results_dir)
        sys.exit(0)

    # ── Worker / sequential mode ────────────────────────────────────────────
    if args._gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args._gpu_id)

    cfg = Config(
        data_dir         = args.data_dir,
        results_dir      = args.results_dir,
        slide_list       = args.slide_list,
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
        gpu_id           = args._gpu_id,
    )

    print(f"Device: {cfg.device}  GPU: {cfg.gpu_id}  Genes: {cfg.genes}")
    run_benchmark(cfg)
