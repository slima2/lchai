#!/usr/bin/env python3
"""
Mutation benchmark exactly as written in the thesis (Sections 5.4.3, 5.4.4, 5.5, 5.8).
=======================================================================================

This script is an EXPOSITORY implementation of the protocol described in Chapters 4-5.
It is NOT the script that produced the archived results (that is
pattern_informed_mil_benchmark.py, next to this file; the differences are listed in
../../provenance/README.md, items D2, D3, D4, D10, D11, D12). It exists so that a reader
can see, in runnable code, what the text specifies. Data loading, evaluation, summary
and plots are imported from the original script; everything the text specifies
differently is implemented here.

Protocol as written                                      where
---------------------------------------------------------------------------------------
Cohort: every slide in data/labels.csv (687 / 668 pts)   run_benchmark()
Folds: 5-fold stratified on the gene label, all slides   patient_folds()  (StratifiedGroupKFold,
  of a patient in the same fold (Sec. 5.8)                 patient = first 12 chars of the TCGA id)
Early stopping / checkpoint: best AUROC on a held-out    inner_split()  (10 % of the training fold,
  10 % of the training fold, stratified (Sec. 5.9.2);      stratified, patient-grouped); the test
  the test fold is evaluated once                          fold is seen once, in fit_mil()
ABMIL (B2, B3, PI-ABMIL, A): two-layer encoder Eq. 4.17, ABMILAsSpecified
  Adam lr 2e-4 wd 1e-5, cosine annealing with warm       fit_mil(): optimiser = "adam",
  restarts T_0 = 10, 50 epochs, patience 15, batch 1,      CosineAnnealingWarmRestarts(T_0=10),
  gradient accumulation over 4 slides, BCE with logits,    accumulation 4, nn.BCEWithLogitsLoss()
  4,096 tiles resampled each training epoch               (BagDataset of the original script)
FC-MIL: Table 5.7 (AdamW, lr 2e-4), measure/integral/    ../artefact3_mutation_choquet/
  regularisers of Eq. 4.24-4.29 and 5.1-5.2                fuzzy_choquet_mil_as_specified.py
B1: XGBoost, 6 pattern fractions + entropy, depth 4,     fit_xgboost(): early stopping on the inner
  300 trees, lr 0.05, scale_pos_weight auto, logloss,      10 % split, shap.TreeExplainer on the
  early stopping 30 rounds, TreeSHAP (Table 5.8)           test fold
Per-fold predictions and metrics saved as JSON (Sec. 5.8) save_fold(): probs, labels, slide_ids kept
Paired t-tests and Cohen's d between all condition pairs  paired_tests()  ->  paired_tests.csv

Run (sequential, CPU or one GPU):
  python pattern_informed_mil_benchmark_as_specified.py --data_dir /path/to/data --results_dir out
Run (one gene per GPU):
  python pattern_informed_mil_benchmark_as_specified.py --data_dir ... --results_dir out --gene_parallel 6
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy import stats
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedGroupKFold
from torch.utils.data import DataLoader

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "artefact3_mutation_choquet"))
from pattern_informed_mil_benchmark import (  # noqa: E402  (shared, unchanged parts)
    CONDITION_NAMES, GENES, PATTERN_NAMES, BagDataset, GatedAttention, SlideData,
    _tag, build_summary, collate_bags, plot_summary)
from fuzzy_choquet_mil_as_specified import FuzzyChoquetMILAsSpecified  # noqa: E402

try:
    import xgboost as xgb
except ImportError:  # pragma: no cover
    xgb = None
try:
    import shap
except ImportError:  # pragma: no cover
    shap = None


# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — every value is the one printed in the thesis
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class Config:
    data_dir:        str = "data"
    results_dir:     str = "results_as_specified"
    slide_list:      Optional[str] = None     # optional; the text uses the full labels.csv cohort
    genes:           List[str] = field(default_factory=lambda: GENES)
    n_folds:         int = 5
    val_frac:        float = 0.10             # Sec. 5.9.2: 10 % of the training fold
    seed:            int = 42
    epochs:          int = 50
    patience:        int = 15
    lr:              float = 2e-4             # Table 5.6 / 5.7
    weight_decay:    float = 1e-5
    t0_restart:      int = 10                 # cosine annealing with warm restarts, T_0
    accumulation:    int = 4                  # slides per optimiser step
    hidden:          int = 256
    attn_dim:        int = 128
    dropout:         float = 0.25
    max_tiles:       int = 4096
    lambda_I:        float = 0.01             # Eq. 4.26
    lambda_M:        float = 0.1              # Eq. 5.2
    mono_pairs:      int = 100
    choquet_scale:   float = 10.0
    xgb_n_estimators: int = 300               # Table 5.8
    xgb_max_depth:   int = 4
    xgb_lr:          float = 0.05
    xgb_early_stop:  int = 30
    min_positive_frac: float = 0.05
    device:          str = "cuda" if torch.cuda.is_available() else "cpu"
    gpu_id:          Optional[int] = None


def patient_id(slide_id: str) -> str:
    return slide_id[:12]                      # TCGA-XX-XXXX


# ══════════════════════════════════════════════════════════════════════════════
#  ABMIL AS WRITTEN (Eq. 4.17 two-layer encoder, Eq. 4.18-4.20)
# ══════════════════════════════════════════════════════════════════════════════
class ABMILAsSpecified(nn.Module):
    def __init__(self, input_dim, hidden=256, attn_dim=128, dropout=0.25):
        super().__init__()
        self.encoder = nn.Sequential(          # h' = ReLU(W2 ReLU(W1 h + b1) + b2), dropout after each ReLU
            nn.Linear(input_dim, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden), nn.ReLU(), nn.Dropout(dropout),
        )
        self.attention = GatedAttention(hidden, attn_dim)
        self.classifier = nn.Linear(hidden, 1)

    def forward(self, H, return_attention=False):
        z, a = self.attention(self.encoder(H))
        logit = self.classifier(z).squeeze(-1)
        return (logit, a) if return_attention else (logit, None)

    def regularisation(self):
        return torch.zeros((), device=self.classifier.weight.device)


# ══════════════════════════════════════════════════════════════════════════════
#  SPLITS
# ══════════════════════════════════════════════════════════════════════════════
def patient_folds(slide_ids, labels, n_folds, seed):
    groups = [patient_id(s) for s in slide_ids]
    skf = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    return list(skf.split(np.zeros(len(labels)), labels, groups))


def inner_split(slide_ids, labels, val_frac, seed):
    """Hold out val_frac of the training fold, stratified and patient-grouped."""
    groups = [patient_id(s) for s in slide_ids]
    n = max(2, int(round(1 / val_frac)))
    skf = StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=seed)
    tr, va = next(iter(skf.split(np.zeros(len(labels)), labels, groups)))
    return tr, va


# ══════════════════════════════════════════════════════════════════════════════
#  TRAINING OF THE MIL CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════
def _to_device(feat, device):
    return (feat[0].to(device), feat[1].to(device)) if isinstance(feat, (tuple, list)) else feat.to(device)


@torch.no_grad()
def predict(model, loader, device):
    model.eval()
    probs, labels = [], []
    for feats, labs in loader:
        for feat, lab in zip(feats, labs):
            logit, _ = model(_to_device(feat, device))
            probs.append(torch.sigmoid(logit).item()); labels.append(lab.item())
    return np.array(probs), np.array(labels)


def metrics(probs, labels):
    m: Dict = {}
    try: m["auroc"] = float(roc_auc_score(labels, probs))
    except ValueError: m["auroc"] = float("nan")
    try: m["auprc"] = float(average_precision_score(labels, probs))
    except ValueError: m["auprc"] = float("nan")
    m["f1"] = float(f1_score(labels, (probs >= 0.5).astype(int), zero_division=0))
    return m


def fit_mil(model, optimiser_name, tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, condition, gene, fold):
    """Train with the Sec. 5.4.3 configuration, select on the inner validation split, test once."""
    dev = cfg.device
    if optimiser_name == "adam":
        opt = torch.optim.Adam(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(opt, T_0=cfg.t0_restart)
    criterion = nn.BCEWithLogitsLoss()                                     # Sec. 5.4.3: BCE with logits
    mode = {"baseline2_abmil_embeddings": "embeddings", "baseline3_abmil_patterns": "patterns",
            "proposed_abmil_concat": "concat", "ablation_abmil_onehot": "onehot",
            "proposed_fuzzy_choquet": "choquet"}[condition]
    tr_ld = DataLoader(BagDataset(tr_sl, tr_lb, mode, cfg.max_tiles, training=True), batch_size=1, shuffle=True, collate_fn=collate_bags)
    va_ld = DataLoader(BagDataset(va_sl, va_lb, mode, cfg.max_tiles, training=False), batch_size=1, shuffle=False, collate_fn=collate_bags)
    te_ld = DataLoader(BagDataset(te_sl, te_lb, mode, cfg.max_tiles, training=False), batch_size=1, shuffle=False, collate_fn=collate_bags)

    best_auroc, best_state, best_epoch, no_improve = -1.0, None, -1, 0
    t0 = time.time()
    print(f"  {tag}  ┌─ {condition} | {gene} fold{fold+1} | {cfg.epochs} epochs | {optimiser_name} lr={cfg.lr:g}", flush=True)
    for epoch in range(cfg.epochs):
        model.train(); opt.zero_grad(); total, n_seen = 0.0, 0
        for feats, labs in tr_ld:                                          # batch of 1 slide
            feat, lab = _to_device(feats[0], dev), labs[0].to(dev)
            logit, _ = model(feat)
            loss = criterion(logit.unsqueeze(0), lab.unsqueeze(0)) + model.regularisation()
            (loss / cfg.accumulation).backward()                           # gradient accumulation over 4 slides
            total += loss.item(); n_seen += 1
            if n_seen % cfg.accumulation == 0:
                opt.step(); opt.zero_grad()
        if n_seen % cfg.accumulation:
            opt.step(); opt.zero_grad()
        sched.step()
        va_probs, va_labs = predict(model, va_ld, dev)
        va_auroc = metrics(va_probs, va_labs)["auroc"]
        improved = not np.isnan(va_auroc) and va_auroc > best_auroc
        print(f"  {tag}  │  ep {epoch+1:3d}/{cfg.epochs}  loss={total/max(n_seen,1):.4f}  val AUROC={va_auroc:.4f}"
              f"  lr={sched.get_last_lr()[0]:.2e}{' ★' if improved else ''}", flush=True)
        if improved:
            best_auroc, best_epoch, no_improve = va_auroc, epoch + 1, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            no_improve += 1
            if no_improve >= cfg.patience:
                print(f"  {tag}  │  Early stop at epoch {epoch+1}", flush=True); break
    if best_state is None:                                                 # validation AUROC undefined (tiny splits)
        best_epoch = epoch + 1
    else:
        model.load_state_dict(best_state)
        ckpt = Path(cfg.results_dir) / "checkpoints"; ckpt.mkdir(parents=True, exist_ok=True)
        torch.save(best_state, ckpt / f"ckpt_{condition}_{gene}_fold{fold}.pth")
    te_probs, te_labs = predict(model, te_ld, dev)                         # the test fold, once
    m = metrics(te_probs, te_labs)
    m.update(val_auroc_best=best_auroc, best_epoch=best_epoch, probs=te_probs.tolist(),
             labels=te_labs.tolist(), slide_ids=[s.slide_id for s in te_sl],
             n_train=len(tr_sl), n_val=len(va_sl), n_test=len(te_sl), seconds=round(time.time() - t0))
    print(f"  {tag}  └─ test AUROC={m['auroc']:.4f}  (best val {best_auroc:.4f} at ep {best_epoch}, {m['seconds']}s)", flush=True)
    return m


def fit_condition(condition, tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, gene, fold):
    embed_dim = next((s.embed_dim for s in tr_sl if s.embed_dim is not None), 512)
    if condition == "proposed_fuzzy_choquet":
        model = FuzzyChoquetMILAsSpecified(embed_dim, 6, cfg.hidden, cfg.attn_dim, cfg.dropout,
                                           cfg.choquet_scale, cfg.lambda_I, cfg.lambda_M, cfg.mono_pairs).to(cfg.device)
        m = fit_mil(model, "adamw", tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, condition, gene, fold)
        m.update(model.measure_report())
        return m
    input_dim = {"baseline2_abmil_embeddings": embed_dim, "baseline3_abmil_patterns": 6,
                 "proposed_abmil_concat": embed_dim + 6, "ablation_abmil_onehot": embed_dim + 6}[condition]
    model = ABMILAsSpecified(input_dim, cfg.hidden, cfg.attn_dim, cfg.dropout).to(cfg.device)
    return fit_mil(model, "adam", tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, condition, gene, fold)


# ══════════════════════════════════════════════════════════════════════════════
#  B1 — XGBOOST AS WRITTEN (Table 5.8: early stopping 30 rounds, TreeSHAP)
# ══════════════════════════════════════════════════════════════════════════════
def fit_xgboost(tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, gene, fold):
    t0 = time.time()
    print(f"  {tag}  ┌─ baseline1_xgboost | {gene} fold{fold+1}", flush=True)
    X_tr, X_va, X_te = (np.vstack([s.xgboost_features() for s in sl]) for sl in (tr_sl, va_sl, te_sl))
    spw = float((tr_lb == 0).sum() / max((tr_lb == 1).sum(), 1))
    clf = xgb.XGBClassifier(n_estimators=cfg.xgb_n_estimators, max_depth=cfg.xgb_max_depth,
                            learning_rate=cfg.xgb_lr, scale_pos_weight=spw, eval_metric="logloss",
                            early_stopping_rounds=cfg.xgb_early_stop, random_state=cfg.seed, verbosity=0)
    clf.fit(X_tr, tr_lb, eval_set=[(X_va, va_lb)], verbose=False)
    probs = clf.predict_proba(X_te)[:, 1]
    m = metrics(probs, te_lb)
    m.update(probs=probs.tolist(), labels=te_lb.tolist(), slide_ids=[s.slide_id for s in te_sl],
             best_iteration=int(getattr(clf, "best_iteration", cfg.xgb_n_estimators)),
             feature_importances=dict(zip(PATTERN_NAMES + ["entropy"], clf.feature_importances_.tolist())),
             n_train=len(tr_sl), n_val=len(va_sl), n_test=len(te_sl))
    if shap is not None:
        try:
            sv = shap.TreeExplainer(clf).shap_values(X_te)
            m["treeshap_mean_abs"] = dict(zip(PATTERN_NAMES + ["entropy"], np.abs(sv).mean(0).tolist()))
            m["treeshap_per_slide"] = np.asarray(sv).tolist()
        except Exception as e:  # shap/xgboost version mismatches (e.g. shap 0.49 with xgboost 3.x)
            m["treeshap_error"] = f"{type(e).__name__}: {e}"
    m["seconds"] = round(time.time() - t0)
    print(f"  {tag}  └─ test AUROC={m['auroc']:.4f}  (trees used {m['best_iteration']+1}, {m['seconds']}s)", flush=True)
    return m


# ══════════════════════════════════════════════════════════════════════════════
#  SAVE / STATISTICS
# ══════════════════════════════════════════════════════════════════════════════
def save_fold(results_dir, condition, gene, fold, m):
    with open(Path(results_dir) / f"metrics_{condition}_{gene}_fold{fold}.json", "w") as f:
        json.dump(m, f, indent=2)                                          # per-slide predictions kept (Sec. 5.8)


def paired_tests(all_results, genes, metric="auroc"):
    rows = []
    conds = [c for c in CONDITION_NAMES if all_results.get(c)]
    for g in genes:
        for c1, c2 in itertools.combinations(conds, 2):
            a = np.array([m[metric] for m in all_results[c1].get(g, [])])
            b = np.array([m[metric] for m in all_results[c2].get(g, [])])
            if len(a) < 2 or len(a) != len(b):
                continue
            d = a - b
            t, p = stats.ttest_rel(a, b)
            dz = d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else float("nan")
            rows.append(dict(gene=g, condition_a=c1, condition_b=c2, metric=metric, mean_a=a.mean(), mean_b=b.mean(),
                             diff=d.mean(), t=t, p=p, cohen_d=dz, n_folds=len(a)))
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP (Sec. 5.8: gene -> condition -> fold)
# ══════════════════════════════════════════════════════════════════════════════
def run_benchmark(cfg: Config):
    np.random.seed(cfg.seed); torch.manual_seed(cfg.seed)
    data_dir, results_dir = Path(cfg.data_dir), Path(cfg.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    tag = _tag(cfg)
    labels_df = pd.read_csv(data_dir / "labels.csv").set_index("slide_id")
    allowed = None
    if cfg.slide_list and Path(cfg.slide_list).exists():
        allowed = {l.strip() for l in open(cfg.slide_list) if l.strip()}
    slide_ids = sorted(d.name for d in (data_dir / "slides").iterdir()
                       if d.is_dir() and (d / "pattern_probs.npy").exists() and (d / "embeddings.npy").exists()
                       and d.name in labels_df.index and (allowed is None or d.name in allowed))
    slides = [SlideData(s, cfg.data_dir) for s in slide_ids]
    n_patients = len({patient_id(s) for s in slide_ids})
    print(f"{tag}Slides: {len(slides)}  patients: {n_patients}  conditions: {CONDITION_NAMES}", flush=True)
    all_results = {c: {} for c in CONDITION_NAMES}

    for gene in cfg.genes:
        if gene not in labels_df.columns:
            continue
        raw = labels_df.loc[slide_ids, gene]
        keep = ~raw.isna()
        g_slides = [s for s, k in zip(slides, keep) if k]
        g_labels = raw[keep].values.astype(int)
        g_ids = [s.slide_id for s in g_slides]
        pos = g_labels.mean()
        print(f"\n{tag}{'='*60}\n{tag}Gene: {gene}  slides={len(g_slides)}  pos={pos:.1%}\n{tag}{'='*60}", flush=True)
        if pos < cfg.min_positive_frac or pos > 1 - cfg.min_positive_frac:
            print(f"{tag}SKIP {gene}: extreme imbalance", flush=True); continue
        for c in CONDITION_NAMES:
            all_results[c][gene] = []

        for fold, (trv_idx, te_idx) in enumerate(patient_folds(g_ids, g_labels, cfg.n_folds, cfg.seed)):
            tr_rel, va_rel = inner_split([g_ids[i] for i in trv_idx], g_labels[trv_idx], cfg.val_frac, cfg.seed + fold)
            tr_idx, va_idx = trv_idx[tr_rel], trv_idx[va_rel]
            tr_sl, va_sl, te_sl = ([g_slides[i] for i in ix] for ix in (tr_idx, va_idx, te_idx))
            tr_lb, va_lb, te_lb = g_labels[tr_idx], g_labels[va_idx], g_labels[te_idx]
            shared = {patient_id(s.slide_id) for s in tr_sl + va_sl} & {patient_id(s.slide_id) for s in te_sl}
            assert not shared, "patient leakage between training and test"
            print(f"\n{tag}── Fold {fold+1}/{cfg.n_folds} (train={len(tr_sl)}, inner-val={len(va_sl)}, test={len(te_sl)}) ──", flush=True)
            for s in tr_sl + va_sl + te_sl:
                s.load()
            for condition in CONDITION_NAMES:
                if condition == "baseline1_xgboost":
                    if xgb is None:
                        print(f"{tag}  xgboost not installed — B1 skipped", flush=True); continue
                    m = fit_xgboost(tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, gene, fold)
                else:
                    m = fit_condition(condition, tr_sl, tr_lb, va_sl, va_lb, te_sl, te_lb, cfg, tag, gene, fold)
                all_results[condition][gene].append(m)
                save_fold(results_dir, condition, gene, fold, m)
            for s in tr_sl + va_sl + te_sl:
                s.unload()

    active = [c for c in CONDITION_NAMES if any(all_results[c].values())]
    summary = build_summary(all_results, cfg, active)
    summary.to_csv(results_dir / "summary_table.csv", index=False)
    print(summary.to_string(index=False), flush=True)
    tests = paired_tests(all_results, cfg.genes)
    tests.to_csv(results_dir / "paired_tests.csv", index=False)
    plot_summary(summary, results_dir)


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--data_dir", default="/home/rapids/notebooks/slima/data")
    p.add_argument("--results_dir", default="/home/rapids/notebooks/slima/results_as_specified")
    p.add_argument("--slide_list", default=None)
    p.add_argument("--genes", nargs="+", default=GENES)
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--gene_parallel", type=int, default=0, help="GPUs: one worker per gene. 0 = sequential")
    p.add_argument("--_gpu_id", type=int, default=None, help=argparse.SUPPRESS)
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.gene_parallel > 0 and args._gpu_id is None:
        log_dir = Path(args.results_dir) / "logs"; log_dir.mkdir(parents=True, exist_ok=True)
        procs = []
        for i, gene in enumerate(args.genes):
            gpu = i % args.gene_parallel
            cmd = [sys.executable, sys.argv[0], "--data_dir", args.data_dir, "--results_dir", args.results_dir,
                   "--genes", gene, "--epochs", str(args.epochs), "--_gpu_id", str(gpu)]
            if args.slide_list:
                cmd += ["--slide_list", args.slide_list]
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu))
            fh = open(log_dir / f"worker_{gene}.txt", "w")
            procs.append((gene, subprocess.Popen(cmd, stdout=fh, stderr=fh, env=env), fh))
            print(f"[GPU {gpu}] {gene} → PID {procs[-1][1].pid}", flush=True)
        for gene, pr, fh in procs:
            pr.wait(); fh.close()
        # aggregate the workers' JSONs
        all_results = {c: {} for c in CONDITION_NAMES}
        for jp in sorted(Path(args.results_dir).glob("metrics_*.json")):
            gene = next((g for g in GENES if f"_{g}_fold" in jp.stem), None)
            if gene is None:
                continue
            cond = jp.stem[len("metrics_"):jp.stem.rfind(f"_{gene}_fold")]
            all_results.setdefault(cond, {}).setdefault(gene, []).append(json.load(open(jp)))
        cfg = Config(data_dir=args.data_dir, results_dir=args.results_dir, genes=args.genes)
        active = [c for c in CONDITION_NAMES if any(all_results[c].values())]
        summary = build_summary(all_results, cfg, active)
        summary.to_csv(Path(args.results_dir) / "summary_table.csv", index=False)
        paired_tests(all_results, args.genes).to_csv(Path(args.results_dir) / "paired_tests.csv", index=False)
        print(summary.to_string(index=False)); plot_summary(summary, args.results_dir)
        sys.exit(0)
    if args._gpu_id is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args._gpu_id)
    cfg = Config(data_dir=args.data_dir, results_dir=args.results_dir, slide_list=args.slide_list,
                 genes=args.genes, epochs=args.epochs, gpu_id=args._gpu_id,
                 device="cuda" if torch.cuda.is_available() else "cpu")
    run_benchmark(cfg)
