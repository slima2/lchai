# [PATTERN NAMES CORRECTED 4-APR-2026] legacy->true: acinar->micropapillary, lepidic->cribriform, micropapillary->papillary, mucinous->lepidic, papillary->solid, solid->acinar (numeric values untouched)
"""
generate_attention_maps.py
==========================
Generates thesis-quality attention map figures from trained ABMIL checkpoints.

For each gene, loads the selected checkpoint, runs inference on ALL slides
in the test fold, picks the best TP/TN examples, and saves:
  - attention_map_{gene}_TP.png   (true positive: mutant correctly predicted)
  - attention_map_{gene}_TN.png   (true negative: wild-type correctly predicted)
  - attention_summary_{gene}.png  (4-panel: attn heatmap + pattern overlay + probs + info)

Usage:
  python3 generate_attention_maps.py \
    --data_dir   /home/rapids/notebooks/slima/data \
    --results_dir /home/rapids/notebooks/slima/results_luad_full_v2 \
    --ckpt_dir   /home/rapids/notebooks/slima/results_luad_full_v2/viz_checkpoints \
    --output_dir /home/rapids/notebooks/slima/figures/attention_maps_v2 \
    --tile_coords_dir /home/rapids/notebooks/slima/outputs/inference_pipeline_6gpu
"""

import os, json, argparse
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — selected folds per gene
# ══════════════════════════════════════════════════════════════════════════════
SELECTED_FOLDS = {
    "TP53":  {"fold": 2, "auroc": 0.8024, "strategy": "best"},
    "EGFR":  {"fold": 4, "auroc": 0.7504, "strategy": "best"},
    "KRAS":  {"fold": 3, "auroc": 0.6800, "strategy": "best"},
    "STK11": {"fold": 3, "auroc": 0.6962, "strategy": "representative"},
    "KEAP1": {"fold": 1, "auroc": 0.6218, "strategy": "representative"},
    "RBM10": {"fold": 4, "auroc": 0.7371, "strategy": "best"},
}

PATTERN_NAMES  = ["micropapillary", "cribriform", "papillary", "lepidic", "solid", "acinar"]
PATTERN_COLORS = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#DD8452"]

# Known mutation→pattern associations for annotation.
# Literature priors in TRUE ANORAK class names (not legacy labels), hence NOT
# permuted by the 4-Apr-2026 remap. The former "mucinous" prior for KRAS is
# expressed through the lepidic×solid IMA proxy of the thesis (Table 6.12).
EXPECTED_PATTERNS = {
    "TP53":  ["solid", "micropapillary"],
    "EGFR":  ["lepidic", "papillary"],
    "KRAS":  ["lepidic", "solid"],
    "STK11": ["lepidic", "solid"],
    "KEAP1": ["acinar", "solid"],
    "RBM10": ["solid", "acinar"],
}

GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]


# ══════════════════════════════════════════════════════════════════════════════
#  MODEL DEFINITION (must match benchmark script exactly)
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
        h     = self.encoder(H)
        z, a  = self.attention(h)
        logit = self.classifier(z).squeeze(-1)
        return (logit, a) if return_attention else (logit, None)


# ══════════════════════════════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def load_slide(slide_id: str, data_dir: Path):
    """Load embeddings + pattern_probs for a slide."""
    slide_dir = data_dir / "slides" / slide_id
    emb_path  = slide_dir / "embeddings.npy"
    prob_path = slide_dir / "pattern_probs.npy"
    if not emb_path.exists() or not prob_path.exists():
        return None, None
    emb   = np.load(str(emb_path)).astype(np.float32)
    probs = np.load(str(prob_path)).astype(np.float32)
    n     = min(emb.shape[0], probs.shape[0])
    return emb[:n], probs[:n]


def load_tile_coords(slide_id: str, tile_coords_dir: Optional[Path]):
    """Load real tile coordinates if available."""
    if tile_coords_dir is None:
        return None
    p = tile_coords_dir / f"{slide_id}_tiles.csv"
    if p.exists():
        df = pd.read_csv(p)
        if "x" in df.columns and "y" in df.columns:
            return df[["x", "y"]].values
    return None


def get_test_slides(gene: str, fold: int, data_dir: Path,
                    results_dir: Path, labels_df: pd.DataFrame):
    """Reconstruct test fold from the saved JSON (contains slide_ids + labels)."""
    json_path = results_dir / f"metrics_proposed_abmil_concat_{gene}_fold{fold}.json"
    if not json_path.exists():
        print(f"  WARNING: {json_path} not found — using all slides")
        return None, None

    with open(json_path) as f:
        d = json.load(f)

    # JSON has predictions and labels stored per slide
    if "slide_ids" in d and "labels" in d and "probs" in d:
        return d["slide_ids"], {
            "labels": np.array(d["labels"]),
            "probs":  np.array(d["probs"]),
        }
    return None, None


# ══════════════════════════════════════════════════════════════════════════════
#  INFERENCE
# ══════════════════════════════════════════════════════════════════════════════
@torch.no_grad()
def run_inference(model, emb: np.ndarray, probs: np.ndarray,
                  device: str) -> tuple:
    """Return (prediction_prob, attention_weights)."""
    model.eval()
    emb_t   = torch.from_numpy(emb).to(device)
    prob_t  = torch.from_numpy(probs).to(device)
    feat    = torch.cat([emb_t, prob_t], dim=1)   # 518-d concat
    logit, attn = model(feat, return_attention=True)
    pred = torch.sigmoid(logit).item()
    return pred, attn.cpu().numpy()


# ══════════════════════════════════════════════════════════════════════════════
#  VISUALIZATION
# ══════════════════════════════════════════════════════════════════════════════
def make_attention_figure(
    slide_id: str,
    gene: str,
    label: int,
    pred_prob: float,
    attn_weights: np.ndarray,
    pattern_probs: np.ndarray,
    tile_coords: Optional[np.ndarray],
    out_path: Path,
    auroc: float,
    fold: int,
):
    """Generate 4-panel thesis figure for one slide."""

    n_tiles        = len(attn_weights)
    top_k          = min(200, n_tiles)
    top_idx        = np.argsort(attn_weights)[::-1][:top_k]
    dominant_pat   = np.argmax(pattern_probs, axis=1)   # (N,) int
    slide_pat_dist = pattern_probs.mean(axis=0)          # (6,) mean per pattern

    label_str = "Mutant" if label == 1 else "Wild-type"
    correct   = (label == 1 and pred_prob >= 0.5) or (label == 0 and pred_prob < 0.5)
    verdict   = "✓ Correct" if correct else "✗ Incorrect"
    expected  = EXPECTED_PATTERNS.get(gene, [])

    fig = plt.figure(figsize=(18, 12))
    fig.patch.set_facecolor("#0F1117")

    # ── Title ────────────────────────────────────────────────────────────────
    title = (f"{gene}  |  {label_str}  |  Pred={pred_prob:.3f}  |  {verdict}"
             f"\n{slide_id[:40]}  |  fold {fold}  |  AUROC={auroc:.3f}")
    fig.suptitle(title, color="white", fontsize=13, y=0.98, fontweight="bold")

    gs = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.35,
                          left=0.06, right=0.96, top=0.90, bottom=0.06)

    # ── Panel 1: Attention scatter (spatial if coords, else ranked) ───────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor("#1A1D27")
    ax1.set_title("Attention Weights (spatial)", color="white", fontsize=10)

    norm_attn = (attn_weights - attn_weights.min()) / \
                (attn_weights.max() - attn_weights.min() + 1e-8)

    if tile_coords is not None and len(tile_coords) >= n_tiles:
        coords = tile_coords[:n_tiles]
        sc = ax1.scatter(coords[:, 0], coords[:, 1],
                         c=norm_attn, cmap="hot", s=1.5, alpha=0.7,
                         vmin=0, vmax=1)
        ax1.set_xlabel("x (pixels)", color="#AAAAAA", fontsize=8)
        ax1.set_ylabel("y (pixels)", color="#AAAAAA", fontsize=8)
        ax1.invert_yaxis()
    else:
        # Pseudo-grid layout
        ncols = int(np.ceil(np.sqrt(n_tiles)))
        nrows = int(np.ceil(n_tiles / ncols))
        grid  = np.full(nrows * ncols, np.nan)
        grid[:n_tiles] = norm_attn
        grid  = grid.reshape(nrows, ncols)
        sc = ax1.imshow(grid, cmap="hot", aspect="auto", vmin=0, vmax=1,
                        interpolation="nearest")
        ax1.set_xlabel("tile column", color="#AAAAAA", fontsize=8)
        ax1.set_ylabel("tile row", color="#AAAAAA", fontsize=8)

    plt.colorbar(sc, ax=ax1, label="attention", fraction=0.03).ax.yaxis.\
        label.set_color("#AAAAAA")
    ax1.tick_params(colors="#AAAAAA")
    for spine in ax1.spines.values():
        spine.set_edgecolor("#444444")

    # ── Panel 2: Pattern overlay on top-attended tiles ────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor("#1A1D27")
    ax2.set_title(f"Pattern of Top-{top_k} Attended Tiles", color="white", fontsize=10)

    top_patterns = dominant_pat[top_idx]
    for pi, (pname, pcolor) in enumerate(zip(PATTERN_NAMES, PATTERN_COLORS)):
        mask = top_patterns == pi
        if mask.sum() == 0:
            continue
        top_attn_pat = norm_attn[top_idx][mask]
        if tile_coords is not None and len(tile_coords) >= n_tiles:
            top_coords_pat = tile_coords[:n_tiles][top_idx][mask]
            ax2.scatter(top_coords_pat[:, 0], top_coords_pat[:, 1],
                        c=pcolor, s=3, alpha=0.8, label=pname)
        else:
            ax2.bar(pi, mask.sum(), color=pcolor, alpha=0.8, label=pname)

    if tile_coords is not None and len(tile_coords) >= n_tiles:
        ax2.invert_yaxis()
        ax2.set_xlabel("x (pixels)", color="#AAAAAA", fontsize=8)
        ax2.set_ylabel("y (pixels)", color="#AAAAAA", fontsize=8)
    else:
        ax2.set_xticks(range(6))
        ax2.set_xticklabels(PATTERN_NAMES, rotation=30, ha="right", fontsize=8)
        ax2.set_ylabel("tile count", color="#AAAAAA", fontsize=8)

    # Highlight expected patterns
    legend_patches = [
        mpatches.Patch(color=PATTERN_COLORS[i],
                       label=f"{'★ ' if PATTERN_NAMES[i] in expected else ''}{PATTERN_NAMES[i]}")
        for i in range(6)
    ]
    ax2.legend(handles=legend_patches, fontsize=7, loc="upper right",
               facecolor="#1A1D27", labelcolor="white",
               title="★ = expected", title_fontsize=7)
    ax2.tick_params(colors="#AAAAAA")
    for spine in ax2.spines.values():
        spine.set_edgecolor("#444444")

    # ── Panel 3: Slide-level pattern distribution ─────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor("#1A1D27")
    ax3.set_title("Slide Pattern Distribution", color="white", fontsize=10)

    bars = ax3.bar(range(6), slide_pat_dist * 100,
                   color=PATTERN_COLORS, alpha=0.85, edgecolor="#444444")
    ax3.set_xticks(range(6))
    ax3.set_xticklabels(PATTERN_NAMES, rotation=30, ha="right",
                        fontsize=8, color="#AAAAAA")
    ax3.set_ylabel("Mean probability (%)", color="#AAAAAA", fontsize=8)
    ax3.set_ylim(0, min(100, slide_pat_dist.max() * 120 + 5))

    # Annotate values
    for bar, val in zip(bars, slide_pat_dist):
        if val > 0.02:
            ax3.text(bar.get_x() + bar.get_width()/2, val * 100 + 0.5,
                     f"{val*100:.1f}%", ha="center", va="bottom",
                     fontsize=7, color="white")

    # Mark expected patterns with star
    for pi, pname in enumerate(PATTERN_NAMES):
        if pname in expected:
            ax3.get_xticklabels()[pi].set_color("#FFD700")
            ax3.get_xticklabels()[pi].set_fontweight("bold")

    ax3.tick_params(colors="#AAAAAA")
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    for spine in ax3.spines.values():
        spine.set_edgecolor("#444444")

    # ── Panel 4: Attention distribution histogram ─────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.set_facecolor("#1A1D27")
    ax4.set_title("Attention Weight Distribution", color="white", fontsize=10)
    ax4.hist(attn_weights * 1e4, bins=50, color="#8E44AD", alpha=0.8,
             edgecolor="#444444")
    ax4.axvline(np.percentile(attn_weights, 90) * 1e4, color="#FFD700",
                linestyle="--", linewidth=1.2, label="90th pct")
    ax4.set_xlabel("Attention weight (×10⁻⁴)", color="#AAAAAA", fontsize=8)
    ax4.set_ylabel("Tile count", color="#AAAAAA", fontsize=8)
    ax4.legend(fontsize=8, facecolor="#1A1D27", labelcolor="white")
    ax4.tick_params(colors="#AAAAAA")
    for spine in ax4.spines.values():
        spine.set_edgecolor("#444444")

    # ── Panel 5: Top-attended tiles pattern breakdown ─────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.set_facecolor("#1A1D27")
    ax5.set_title(f"Pattern Composition: Top {top_k} Tiles vs All Tiles",
                  color="white", fontsize=10)

    top_dist = np.bincount(top_patterns, minlength=6) / top_k
    x        = np.arange(6)
    w        = 0.35
    ax5.bar(x - w/2, slide_pat_dist * 100, w,
            color=PATTERN_COLORS, alpha=0.5, label="All tiles", edgecolor="#444444")
    ax5.bar(x + w/2, top_dist * 100, w,
            color=PATTERN_COLORS, alpha=0.95, label=f"Top-{top_k} attended",
            edgecolor="white", linewidth=0.5)
    ax5.set_xticks(x)
    ax5.set_xticklabels(PATTERN_NAMES, rotation=30, ha="right",
                        fontsize=8, color="#AAAAAA")
    ax5.set_ylabel("Proportion (%)", color="#AAAAAA", fontsize=8)
    ax5.legend(fontsize=8, facecolor="#1A1D27", labelcolor="white")
    ax5.tick_params(colors="#AAAAAA")
    for spine in ax5.spines.values():
        spine.set_edgecolor("#444444")

    # ── Panel 6: Info box ─────────────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.set_facecolor("#1A1D27")
    ax6.axis("off")

    top_pat_name   = PATTERN_NAMES[np.argmax(slide_pat_dist)]
    top_attn_pat   = PATTERN_NAMES[np.bincount(top_patterns, minlength=6).argmax()]
    enrichment     = top_dist / (slide_pat_dist + 1e-8)
    most_enriched  = PATTERN_NAMES[np.argmax(enrichment)]

    info_lines = [
        f"Gene:           {gene}",
        f"Status:         {label_str}",
        f"Prediction:     {pred_prob:.4f}",
        f"Outcome:        {verdict}",
        f"",
        f"Fold:           {fold}",
        f"Fold AUROC:     {auroc:.4f}",
        f"",
        f"N tiles:        {n_tiles:,}",
        f"Top-k:          {top_k}",
        f"",
        f"Dominant pat.:  {top_pat_name}",
        f"Top-attn pat.:  {top_attn_pat}",
        f"Most enriched:  {most_enriched}",
        f"",
        f"Expected pats:  {', '.join(expected)}",
        f"",
        f"Model:          proposed_abmil_concat",
        f"Input dim:      518-d (512 emb + 6 pat)",
    ]

    ax6.text(0.05, 0.95, "\n".join(info_lines),
             transform=ax6.transAxes,
             va="top", ha="left", fontsize=9,
             color="#DDDDDD", fontfamily="monospace",
             bbox=dict(boxstyle="round", facecolor="#262A35",
                       edgecolor="#444444", alpha=0.9))

    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  Saved → {out_path.name}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir",       default="/home/rapids/notebooks/slima/data")
    parser.add_argument("--results_dir",    default="/home/rapids/notebooks/slima/results_luad_full_v2")
    parser.add_argument("--ckpt_dir",       default="/home/rapids/notebooks/slima/results_luad_full_v2/viz_checkpoints")
    parser.add_argument("--output_dir",     default="/home/rapids/notebooks/slima/figures/attention_maps_v2")
    parser.add_argument("--tile_coords_dir",default="/home/rapids/notebooks/slima/outputs/inference_pipeline_6gpu")
    parser.add_argument("--genes",          nargs="+", default=GENES)
    parser.add_argument("--n_slides",       type=int, default=3,
                        help="Number of TP and TN slides to visualize per gene")
    parser.add_argument("--device",         default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    data_dir       = Path(args.data_dir)
    results_dir    = Path(args.results_dir)
    ckpt_dir       = Path(args.ckpt_dir)
    output_dir     = Path(args.output_dir)
    tile_coords_dir = Path(args.tile_coords_dir) if args.tile_coords_dir else None
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load labels
    labels_df = pd.read_csv(data_dir / "labels.csv")
    labels_df.set_index("slide_id", inplace=True)

    for gene in args.genes:
        if gene not in SELECTED_FOLDS:
            print(f"Skipping {gene} — not in SELECTED_FOLDS")
            continue

        fold_info = SELECTED_FOLDS[gene]
        fold      = fold_info["fold"]
        auroc     = fold_info["auroc"]

        print(f"\n{'═'*60}")
        print(f"Gene: {gene}  fold={fold}  AUROC={auroc:.4f}")

        # Load checkpoint
        ckpt_path = ckpt_dir / f"ckpt_proposed_abmil_concat_{gene}_fold{fold}.pth"
        if not ckpt_path.exists():
            print(f"  ERROR: {ckpt_path} not found — skipping")
            continue

        # Build model (518-d input = 512 emb + 6 pattern probs)
        model = ABMIL(input_dim=518, hidden_dim=256, attn_dim=128, dropout=0.25)
        state = torch.load(str(ckpt_path), map_location=args.device)
        model.load_state_dict(state)
        model = model.to(args.device)
        model.eval()
        print(f"  Loaded checkpoint: {ckpt_path.name}")

        # Get test slides from JSON or reconstruct from labels
        slide_ids_all = [
            d.name for d in (data_dir / "slides").iterdir()
            if d.is_dir()
            and (d / "embeddings.npy").exists()
            and (d / "pattern_probs.npy").exists()
            and d.name in labels_df.index
        ]

        # Reconstruct the same fold split used during training
        from sklearn.model_selection import StratifiedKFold
        gene_labels = labels_df.loc[slide_ids_all, gene].dropna()
        valid_ids   = list(gene_labels.index)
        valid_lbls  = gene_labels.values.astype(int)

        skf       = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        splits    = list(skf.split(valid_ids, valid_lbls))
        _, va_idx = splits[fold]
        test_ids  = [valid_ids[i] for i in va_idx]
        test_lbls = valid_lbls[va_idx]

        print(f"  Test fold: {len(test_ids)} slides "
              f"(mut={test_lbls.sum()}, wt={(1-test_lbls).sum()})")

        # Run inference on all test slides
        results = []
        for sid, lbl in zip(test_ids, test_lbls):
            emb, probs = load_slide(sid, data_dir)
            if emb is None:
                continue
            pred, attn = run_inference(model, emb, probs, args.device)
            results.append({
                "slide_id": sid, "label": lbl,
                "pred": pred, "attn": attn,
                "probs": probs, "emb": emb,
            })

        # Sort: best TP (highest pred among mutants) and best TN (lowest pred among wt)
        tps = sorted([r for r in results if r["label"] == 1],
                     key=lambda x: -x["pred"])
        tns = sorted([r for r in results if r["label"] == 0],
                     key=lambda x:  x["pred"])

        gene_dir = output_dir / gene
        gene_dir.mkdir(exist_ok=True)

        # Generate figures for top N_SLIDES TP and TN
        for rank, r in enumerate(tps[:args.n_slides]):
            coords = load_tile_coords(r["slide_id"], tile_coords_dir)
            out    = gene_dir / f"TP_rank{rank+1}_{r['slide_id'][:20]}.png"
            make_attention_figure(
                slide_id=r["slide_id"], gene=gene, label=r["label"],
                pred_prob=r["pred"], attn_weights=r["attn"],
                pattern_probs=r["probs"], tile_coords=coords,
                out_path=out, auroc=auroc, fold=fold,
            )

        for rank, r in enumerate(tns[:args.n_slides]):
            coords = load_tile_coords(r["slide_id"], tile_coords_dir)
            out    = gene_dir / f"TN_rank{rank+1}_{r['slide_id'][:20]}.png"
            make_attention_figure(
                slide_id=r["slide_id"], gene=gene, label=r["label"],
                pred_prob=r["pred"], attn_weights=r["attn"],
                pattern_probs=r["probs"], tile_coords=coords,
                out_path=out, auroc=auroc, fold=fold,
            )

        print(f"  Done: {len(tps[:args.n_slides])} TP + {len(tns[:args.n_slides])} TN figures")

    print(f"\n✅ All figures saved to {output_dir}")


if __name__ == "__main__":
    main()
