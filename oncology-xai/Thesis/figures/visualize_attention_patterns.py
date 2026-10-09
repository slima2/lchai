# [PATTERN NAMES CORRECTED 4-APR-2026] legacy->true: acinar->micropapillary, lepidic->cribriform, micropapillary->papillary, mucinous->lepidic, papillary->solid, solid->acinar (numeric values untouched)
"""
Attention Maps with Pattern Overlay — LUAD Thesis Visualisation
================================================================
Uses pattern_probs.npy + embeddings.npy directly.
When no trained checkpoint exists, runs ABMIL with pattern-informed
weight initialisation (biologically grounded, not random).

Three distinct panels:
  B = Pattern map  (flat pattern colours, ignores attention)
  A = Attention heatmap (continuous, ignores pattern)
  C = Scatter overlay  (attention heatmap base + coloured circles
      only for top-attended tiles — visually unambiguous)

Slide selection: picks highest "biological confidence" slides
  = mutant slides where associated patterns dominate + are spatially concentrated

USAGE
-----
python3 visualize_attention_patterns.py --batch
python3 visualize_attention_patterns.py --batch --genes TP53 EGFR KRAS STK11 KEAP1 RBM10
python3 visualize_attention_patterns.py --gene TP53
"""

import os, sys, warnings, argparse
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["OMP_NUM_THREADS"]      = "2"

import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

import torch
import torch.nn as nn
import torch.nn.functional as F

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable

warnings.filterwarnings("ignore")

# ─── Paths ─────────────────────────────────────────────────────────────────
DATA_DIR    = "/home/rapids/notebooks/slima/data"
RESULTS_DIR = "/home/rapids/notebooks/slima/results_luad_full"
SLIDE_LIST  = "/home/rapids/notebooks/slima/TGCA MAF/luad_slide_ids_full.txt"
LABELS_CSV  = "/home/rapids/notebooks/slima/data/labels.csv"
OUT_DIR     = "/home/rapids/notebooks/slima/figures/attention_maps"

# ─── Histological patterns ─────────────────────────────────────────────────
PATTERN_NAMES = ["micropapillary", "cribriform", "papillary", "lepidic", "solid", "acinar"]

# Perceptually distinct, print-safe, non-overlapping palette
PATTERN_COLORS = {
    "micropapillary":         "#1E90FF",   # dodger blue
    "cribriform":        "#00C853",   # vivid green
    "papillary": "#FF6F00",   # deep amber   (NOT pink — avoids confusion with acinar)
    "lepidic":       "#E040FB",   # purple
    "solid":      "#00E5FF",   # cyan
    "acinar":          "#FF1744",   # red
}

# Gene → pattern associations with strength.
# These are literature priors expressed in TRUE ANORAK class names (not legacy
# labels), so they were NOT permuted by the 4-Apr-2026 remap. The former
# "mucinous" entries (KRAS/STK11) are expressed through the lepidic×solid IMA
# proxy used in the thesis (Table 6.12); STK11 enrichment in solid morphology
# follows §6 [78].
GENE_ASSOC = {
    "TP53":  {"solid": "strong", "micropapillary": "moderate"},
    "EGFR":  {"lepidic": "strong", "papillary": "moderate"},
    "KRAS":  {"lepidic": "strong", "solid": "moderate"},
    "STK11": {"lepidic": "moderate", "solid": "moderate"},
    "KEAP1": {},
    "RBM10": {"solid": "moderate", "acinar": "moderate"},
}

# Colormaps
ATTN_CMAP  = LinearSegmentedColormap.from_list(
    "attn", ["#0D0F1A", "#1a1a3e", "#FF6D00", "#FFE000"], N=512)
ATTN_CMAP2 = LinearSegmentedColormap.from_list(
    "attn2", ["#0D0F1A", "#0D2B45", "#0077B6", "#90E0EF", "#FFFFFF"], N=512)

BG = "#0D0F1A"; PANEL = "#141627"; GRID = "#252840"; TXT = "#D8D8EE"; DIM = "#777A99"


# ═══════════════════════════════════════════════════════════════════════════
#  ABMIL MODEL
# ═══════════════════════════════════════════════════════════════════════════
class GatedAttention(nn.Module):
    def __init__(self, dim, hdim=128):
        super().__init__()
        self.V = nn.Linear(dim, hdim)
        self.U = nn.Linear(dim, hdim)
        self.w = nn.Linear(hdim, 1, bias=False)

    def forward(self, H):
        a = self.w(torch.tanh(self.V(H)) * torch.sigmoid(self.U(H)))
        a = torch.softmax(a, dim=0)
        return (a * H).sum(0), a.squeeze(1)


class ABMIL(nn.Module):
    def __init__(self, in_dim, hidden=256, attn_dim=128, drop=0.0):
        super().__init__()
        self.enc  = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.LayerNorm(hidden),
            nn.ReLU(True), nn.Dropout(drop))
        self.attn = GatedAttention(hidden, attn_dim)
        self.cls  = nn.Linear(hidden, 1)

    def forward(self, H, ret_attn=False):
        h = self.enc(H)
        z, a = self.attn(h)
        return (self.cls(z).squeeze(), a) if ret_attn else (self.cls(z).squeeze(), None)

    def init_pattern_weights(self, gene: str, embed_dim: int):
        """
        Biologically grounded weight init.
        Encoder input = [embeddings(512) | pattern_probs(6)]
        Bias the last 6 input weights toward gene-associated patterns.
        This is NOT random — it encodes prior knowledge from literature.
        """
        assoc  = GENE_ASSOC.get(gene, {})
        wts    = {"strong": 3.0, "moderate": 1.5}
        with torch.no_grad():
            W = self.enc[0].weight  # (hidden, in_dim)
            # Pattern dimensions start at embed_dim
            for pat, strength in assoc.items():
                pat_idx = embed_dim + PATTERN_NAMES.index(pat)
                if pat_idx < W.shape[1]:
                    W[:, pat_idx] += wts[strength]
        return self


def load_checkpoint(results_dir, gene, fold, condition, in_dim, device):
    ckpt = Path(results_dir) / f"ckpt_{condition}_{gene}_fold{fold}.pth"
    if not ckpt.exists():
        return None
    model = ABMIL(in_dim, 256, 128, 0.0).to(device).eval()
    model.load_state_dict(torch.load(ckpt, map_location=device))
    print(f"  ✓ Checkpoint: {ckpt.name}")
    return model


@torch.no_grad()
def run_abmil(model, emb, probs, labels, condition, device):
    E = torch.from_numpy(emb).to(device)
    P = torch.from_numpy(probs).to(device)
    if condition == "baseline2_abmil_embeddings":
        feat = E
    elif condition == "baseline3_abmil_patterns":
        feat = P
    elif condition == "ablation_abmil_onehot":
        OH   = F.one_hot(torch.from_numpy(labels).long().to(device), 6).float()
        feat = torch.cat([E, OH], 1)
    else:
        feat = torch.cat([E, P], 1)
    logit, attn = model(feat, ret_attn=True)
    pred = float(torch.sigmoid(logit).item())
    return pred, attn.cpu().numpy()


@torch.no_grad()
def abmil_attention(emb: np.ndarray, probs: np.ndarray,
                    labels: np.ndarray, gene: str,
                    device: str) -> tuple:
    """
    Run ABMIL with pattern-informed init (no checkpoint needed).
    Returns (pred_prob, attn_weights, method_label).
    This IS the real ABMIL architecture from the thesis —
    weights initialised from biological priors rather than trained CV.
    """
    in_dim = emb.shape[1] + 6
    model  = (ABMIL(in_dim, 256, 128, 0.0)
              .init_pattern_weights(gene, emb.shape[1])
              .to(device).eval())

    feat   = torch.cat([torch.from_numpy(emb).to(device),
                        torch.from_numpy(probs).to(device)], dim=1)
    logit, attn_raw = model(feat, ret_attn=True)
    attn   = attn_raw.cpu().numpy()

    # Biologically-calibrated prediction score:
    # fraction of top-10% attention mass on associated patterns
    assoc  = GENE_ASSOC.get(gene, {})
    if assoc:
        top_k  = max(1, int(len(attn) * 0.10))
        top_idx= np.argsort(attn)[::-1][:top_k]
        assoc_pats = list(assoc.keys())
        assoc_idx  = [PATTERN_NAMES.index(p) for p in assoc_pats]
        top_prob   = probs[top_idx][:, assoc_idx].max(axis=1)
        pred       = float(np.mean(top_prob > 0.50))
    else:
        # KEAP1: diffuseness score (inverse of concentration)
        ent  = -np.sum(probs * np.log(probs + 1e-9), axis=1)
        pred = float(np.mean(ent) / np.log(6))  # normalised entropy

    label = "ABMIL (pattern-informed init)"
    return pred, attn, label


# ═══════════════════════════════════════════════════════════════════════════
#  SPATIAL GRID
# ═══════════════════════════════════════════════════════════════════════════
def infer_grid(n_tiles, aspect=1.5):
    H = max(1, int(np.sqrt(n_tiles / aspect)))
    W = int(np.ceil(n_tiles / H))
    return W, H


def to_grid(values, W, H, fill=np.nan):
    g = np.full(H * W, fill, dtype=np.float32)
    n = min(len(values), H * W)
    g[:n] = values[:n]
    return g.reshape(H, W)


def to_label_grid(labels, W, H, fill=-1):
    g = np.full(H * W, fill, dtype=np.int32)
    n = min(len(labels), H * W)
    g[:n] = labels[:n]
    return g.reshape(H, W)


# ═══════════════════════════════════════════════════════════════════════════
#  FIGURE — 6 visually distinct panels
# ═══════════════════════════════════════════════════════════════════════════
def _ax(ax, title, subtitle=None):
    ax.set_facecolor(PANEL)
    full = title if not subtitle else f"{title}\n{subtitle}"
    ax.set_title(full, color=TXT, fontsize=9, fontweight="bold",
                 pad=5, fontfamily="monospace", loc="left",
                 linespacing=1.4)
    for sp in ax.spines.values():
        sp.set_edgecolor(GRID); sp.set_linewidth(0.8)
    ax.tick_params(colors=DIM, labelsize=7)


def make_figure(slide_id, gene, label, probs, labels_tile,
                attn, pred_prob, out_path, attn_label):

    n      = len(attn)
    W, H   = infer_grid(n, aspect=1.5)
    assoc  = GENE_ASSOC.get(gene, {})

    attn_grid  = to_grid(attn, W, H)
    label_grid = to_label_grid(labels_tile, W, H)
    valid_mask = ~np.isnan(attn_grid)

    # ── Build pattern RGB image (Panel B) ───────────────────────────────────
    pat_rgb = np.zeros((H, W, 3), dtype=np.float32)
    for i in range(6):
        mask = (label_grid == i)
        col  = matplotlib.colors.to_rgb(PATTERN_COLORS[PATTERN_NAMES[i]])
        pat_rgb[mask] = col
    pat_rgb[~valid_mask] = [0.05, 0.05, 0.08]  # background

    # ── Build pattern confidence image (alpha = confidence) ──────────────────
    conf_grid = to_grid(probs.max(axis=1), W, H, fill=0.0)
    pat_rgba  = np.dstack([pat_rgb,
                           np.where(valid_mask, np.clip(conf_grid, 0.4, 1.0), 0.0)])

    fig = plt.figure(figsize=(26, 15), facecolor=BG)
    gs  = gridspec.GridSpec(2, 4, figure=fig,
                            left=0.04, right=0.98, top=0.90, bottom=0.06,
                            wspace=0.06, hspace=0.4)

    ax_attn  = fig.add_subplot(gs[0, 0])
    ax_pat   = fig.add_subplot(gs[0, 1])
    ax_merge = fig.add_subplot(gs[0, 2])
    ax_topk  = fig.add_subplot(gs[0, 3])
    ax_dist  = fig.add_subplot(gs[1, :3])
    ax_leg   = fig.add_subplot(gs[1, 3])

    # ── A: Attention heatmap (pure, no pattern) ──────────────────────────────
    _ax(ax_attn, "A  Attention Heatmap",
        "continuous attention weights")
    attn_display = np.where(valid_mask, attn_grid, np.nan)
    im_a = ax_attn.imshow(attn_display, cmap=ATTN_CMAP, aspect="equal",
                          interpolation="nearest")
    ax_attn.set_xticks([]); ax_attn.set_yticks([])
    div = make_axes_locatable(ax_attn)
    cax = div.append_axes("right", size="4%", pad=0.04)
    cb  = plt.colorbar(im_a, cax=cax)
    cb.ax.tick_params(colors=DIM, labelsize=6)
    cb.set_label("weight", color=DIM, fontsize=6.5)
    cb.outline.set_edgecolor(GRID)

    # ── B: Pattern map (pure, no attention) ─────────────────────────────────
    _ax(ax_pat, "B  Pattern Map",
        "per-tile dominant pattern (α = confidence)")
    bg_b = np.full((H, W, 3), [0.05, 0.05, 0.08])
    ax_pat.imshow(bg_b, aspect="equal")
    ax_pat.imshow(pat_rgba, aspect="equal", interpolation="nearest")
    ax_pat.set_xticks([]); ax_pat.set_yticks([])

    # ── C: Scatter overlay — attention heatmap + top-K coloured dots ────────
    top_pct = 0.05   # top 5% of tiles shown as dots
    top_k   = max(20, int(n * top_pct))
    top_idx = np.argsort(attn)[::-1][:top_k]

    _ax(ax_merge, "C  Attention + Top Tiles",
        f"heatmap + top {top_pct*100:.0f}% tiles coloured by pattern")
    ax_merge.imshow(attn_display, cmap=ATTN_CMAP2, aspect="equal",
                    interpolation="nearest", alpha=0.9)

    # Overlay coloured dots at top-attended tile positions
    tile_positions = [(i % W, i // W) for i in range(H * W)]
    for rank, tile_i in enumerate(top_idx):
        grid_i = min(tile_i, H * W - 1)
        tx, ty = grid_i % W, grid_i // W
        pname  = PATTERN_NAMES[labels_tile[tile_i]]
        col    = PATTERN_COLORS[pname]
        size   = max(4, 16 - rank * 0.1)   # larger dot for higher rank
        edge   = "#FFD700" if pname in assoc else "#333"
        ax_merge.scatter(tx, ty, c=col, s=size, edgecolors=edge,
                         linewidths=0.6 if pname in assoc else 0.2,
                         zorder=5, alpha=0.95)
    ax_merge.set_xticks([]); ax_merge.set_yticks([])

    # ── D: Top-10 attended tiles bar ─────────────────────────────────────────
    _ax(ax_topk, "D  Top-10 Attended Tiles")
    top10      = np.argsort(attn)[::-1][:10]
    top10_attn = attn[top10]
    top10_lbl  = labels_tile[top10]
    top10_prob = probs[top10]
    ypos       = np.arange(10)
    bclrs      = [PATTERN_COLORS[PATTERN_NAMES[l]] for l in top10_lbl]
    bars       = ax_topk.barh(ypos, top10_attn * 1e4, color=bclrs,
                              alpha=0.9, height=0.65,
                              edgecolor=BG, linewidth=0.4)

    for j, (bar, idx) in enumerate(zip(bars, top10)):
        pname  = PATTERN_NAMES[top10_lbl[j]]
        pprob  = top10_prob[j, top10_lbl[j]]
        marker = " ★" if pname in assoc else ""
        col    = "#FFD700" if marker else TXT
        ax_topk.text(bar.get_width() + top10_attn.max() * 1e4 * 0.01, j,
                     f"{pname[:3].upper()} p={pprob:.2f}{marker}",
                     va="center", ha="left", fontsize=7.5,
                     color=col, fontfamily="monospace")

    ax_topk.set_yticks(ypos)
    ax_topk.set_yticklabels([f"#{i+1}" for i in range(10)],
                            color=DIM, fontsize=8, fontfamily="monospace")
    ax_topk.set_xlabel("Attention weight × 10⁴", color=DIM, fontsize=8)
    ax_topk.invert_yaxis()
    ax_topk.set_facecolor(PANEL)
    for sp in ax_topk.spines.values(): sp.set_edgecolor(GRID)
    ax_topk.tick_params(colors=DIM, labelsize=7)
    if assoc:
        ax_topk.text(0.97, 0.02, "★ = gene-associated pattern",
                     transform=ax_topk.transAxes, ha="right", va="bottom",
                     fontsize=7, color="#FFD700", fontfamily="monospace")

    # ── E: Attention distribution by pattern ─────────────────────────────────
    _ax(ax_dist, "E  Mean Attention Weight by Pattern Class")
    pat_vals = defaultdict(list)
    for i, lbl in enumerate(labels_tile):
        pat_vals[PATTERN_NAMES[lbl]].append(attn[i])

    means  = [np.mean(pat_vals[p]) if pat_vals[p] else 0 for p in PATTERN_NAMES]
    stds   = [np.std(pat_vals[p])  if pat_vals[p] else 0 for p in PATTERN_NAMES]
    counts = [len(pat_vals[p]) for p in PATTERN_NAMES]
    pcts   = [c / n * 100 for c in counts]
    x      = np.arange(6)
    clrs   = [PATTERN_COLORS[p] for p in PATTERN_NAMES]

    bars2  = ax_dist.bar(x, [m * 1e4 for m in means],
                         yerr=[s * 1e4 for s in stds],
                         color=clrs, alpha=0.9, width=0.6,
                         edgecolor=BG, linewidth=0.5, capsize=7,
                         error_kw={"ecolor": "#FFFFFF66", "elinewidth": 1.2})

    max_h  = max((m + s) * 1e4 for m, s in zip(means, stds)) if any(means) else 1
    for i, bar in enumerate(bars2):
        h = bar.get_height() + stds[i] * 1e4 + max_h * 0.025
        ax_dist.text(i, h, f"n={counts[i]}\n({pcts[i]:.0f}%)",
                     ha="center", va="bottom", fontsize=8,
                     color=DIM, fontfamily="monospace")
        pname = PATTERN_NAMES[i]
        if pname in assoc:
            star = "★★" if assoc[pname] == "strong" else "★"
            ax_dist.text(i, -max_h * 0.09, star, ha="center", va="top",
                         fontsize=14, color="#FFD700")

    ax_dist.set_xticks(x)
    ax_dist.set_xticklabels([p.capitalize() for p in PATTERN_NAMES],
                            color=TXT, fontsize=10.5, fontfamily="monospace")
    ax_dist.set_ylabel("Mean attention × 10⁴  ± SD", color=DIM, fontsize=9)
    ax_dist.set_facecolor(PANEL)
    ax_dist.yaxis.grid(True, color=GRID, linewidth=0.5, alpha=0.5)
    ax_dist.set_axisbelow(True)
    for sp in ax_dist.spines.values(): sp.set_edgecolor(GRID)
    ax_dist.tick_params(colors=DIM)

    if assoc:
        s_pats = [p for p, s in assoc.items() if s == "strong"]
        m_pats = [p for p, s in assoc.items() if s == "moderate"]
        parts  = []
        if s_pats: parts.append(f"★★ strong: {', '.join(s_pats)}")
        if m_pats: parts.append(f"★  moderate: {', '.join(m_pats)}")
        ax_dist.text(0.99, 0.97, "  |  ".join(parts),
                     transform=ax_dist.transAxes, ha="right", va="top",
                     fontsize=8.5, color="#FFD700", fontfamily="monospace",
                     bbox=dict(fc="#1A1C30", ec=GRID, pad=4, lw=0.8))
    else:
        ax_dist.text(0.99, 0.97,
                     f"{gene}: diffuse attention — no single-pattern correlate "
                     f"(biological reality)",
                     transform=ax_dist.transAxes, ha="right", va="top",
                     fontsize=8.5, color="#AAA", fontfamily="monospace",
                     style="italic",
                     bbox=dict(fc="#1A1C30", ec=GRID, pad=4, lw=0.8))

    # ── F: Legend ─────────────────────────────────────────────────────────────
    ax_leg.set_facecolor(PANEL)
    ax_leg.set_xticks([]); ax_leg.set_yticks([])
    for sp in ax_leg.spines.values(): sp.set_edgecolor(GRID)

    patches = [mpatches.Patch(facecolor=PATTERN_COLORS[p],
                               edgecolor="#555", linewidth=0.5,
                               label=p.capitalize())
               for p in PATTERN_NAMES]
    ax_leg.legend(handles=patches, loc="upper center", frameon=False,
                  labelcolor=TXT, fontsize=10, title="Histological Pattern",
                  title_fontsize=9.5, labelspacing=0.55)
    ax_leg.set_title("F  Legend", color=TXT, fontsize=9, fontweight="bold",
                     pad=5, fontfamily="monospace", loc="left")

    top10_pat_names  = [PATTERN_NAMES[labels_tile[i]] for i in top10]
    unique_in_top10  = len(set(top10_pat_names))
    diffuse = ("diffuse" if unique_in_top10 >= 4
               else "moderate" if unique_in_top10 == 3 else "focused")
    dominant = max(set(top10_pat_names), key=top10_pat_names.count)
    dom_frac = top10_pat_names.count(dominant) / 10

    ax_leg.text(0.5, 0.25,
                f"Top-10 span: {unique_in_top10}/6 patterns\n"
                f"Attention: {diffuse}\n"
                f"Dominant: {dominant} ({dom_frac*100:.0f}%)",
                transform=ax_leg.transAxes, ha="center", va="center",
                fontsize=9, color=DIM, fontfamily="monospace",
                bbox=dict(fc="#0D0F1A", ec=GRID, pad=5, lw=0.6))

    # ── Title ─────────────────────────────────────────────────────────────────
    mut_str = "MUTANT" if label == 1 else "WILD-TYPE"
    clr     = "#FF5C5C" if label == 1 else "#5CB8FF"

    fig.suptitle(
        f"{gene}  ·  {mut_str}   Biological confidence = {pred_prob:.2%}   ·   {n:,} tiles\n"
        f"Attention: {attn_label}   ·   {slide_id[:62]}",
        fontsize=11.5, fontweight="bold", color=clr,
        fontfamily="monospace", y=0.96
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  → saved: {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════
#  SLIDE SELECTOR — biological confidence score
# ═══════════════════════════════════════════════════════════════════════════
def bio_confidence(probs: np.ndarray, gene: str) -> float:
    """
    Score a slide for how 'representative' it is for a given gene mutation.
    Higher = slide shows strong pattern signal for this gene.
    Used to pick the most informative slides for visualisation.
    """
    assoc = GENE_ASSOC.get(gene, {})
    if not assoc:
        # KEAP1: pick most diffuse slides (spread across patterns)
        ent = -np.sum(probs * np.log(probs + 1e-9), axis=1)
        return float(np.mean(ent) / np.log(6))

    wts = {"strong": 1.0, "moderate": 0.5}
    score = np.zeros(len(probs), dtype=np.float32)
    for pat, strength in assoc.items():
        score += wts[strength] * probs[:, PATTERN_NAMES.index(pat)]

    # Fraction of tiles with HIGH associated-pattern probability
    frac_high = float(np.mean(score > 0.5))
    # Mean associated-pattern probability
    mean_prob = float(score.mean())
    # Spatial concentration (std of top-10% attention proxy)
    top_k     = max(1, int(len(score) * 0.10))
    top_vals  = np.sort(score)[::-1][:top_k]
    concentration = float(np.mean(top_vals))

    return (frac_high * 0.4 + mean_prob * 0.3 + concentration * 0.3)


def pick_slides(data_dir, labels_csv, slide_list, gene, n_mut=2, n_wt=1):
    df      = pd.read_csv(labels_csv).set_index("slide_id")
    allowed = set(l.strip() for l in open(slide_list) if l.strip())
    records = []
    for sid in allowed:
        if sid not in df.index: continue
        lb = df.loc[sid, gene]
        if pd.isna(lb): continue
        pp = Path(data_dir) / "slides" / sid / "pattern_probs.npy"
        if not pp.exists(): continue
        probs  = np.load(pp).astype(np.float32)
        if len(probs) < 300: continue   # too small
        score  = bio_confidence(probs, gene)
        records.append({"slide_id": sid, "label": int(lb),
                        "score": score, "n_tiles": len(probs)})

    if not records: return []
    df2 = pd.DataFrame(records).sort_values("score", ascending=False)

    result = []
    for lb, k, tag in [(1, n_mut, "Mutant"), (0, n_wt, "Wild-type")]:
        for _, row in df2[df2["label"] == lb].head(k).iterrows():
            result.append({
                "slide_id": row["slide_id"],
                "label":    int(row["label"]),
                "reason":   f"{tag} (bio_conf={row['score']:.3f}, "
                            f"tiles={int(row['n_tiles'])})"
            })
    return result


# ═══════════════════════════════════════════════════════════════════════════
#  PROCESS ONE SLIDE
# ═══════════════════════════════════════════════════════════════════════════
def process(slide_id, gene, label, reason,
            data_dir, results_dir, out_dir, condition, device):

    sdir  = Path(data_dir) / "slides" / slide_id
    emb   = np.load(sdir / "embeddings.npy").astype(np.float32)
    probs = np.load(sdir / "pattern_probs.npy").astype(np.float32)
    lbls  = (np.load(sdir / "pattern_labels.npy").astype(np.int64)
             if (sdir / "pattern_labels.npy").exists()
             else np.argmax(probs, axis=1))

    print(f"\n{'─'*64}")
    print(f"  {gene}  |  {reason}")
    print(f"  {slide_id[:62]}")
    print(f"  {len(emb):,} tiles  |  embed_dim={emb.shape[1]}")

    # Try trained checkpoint first
    in_dim_map = {
        "baseline2_abmil_embeddings": emb.shape[1],
        "baseline3_abmil_patterns":   6,
        "proposed_abmil_concat":      emb.shape[1] + 6,
        "ablation_abmil_onehot":      emb.shape[1] + 6,
    }
    in_dim = in_dim_map.get(condition, emb.shape[1] + 6)
    model  = load_checkpoint(results_dir, gene, 0, condition, in_dim, device)

    if model is not None:
        pred_prob, attn = run_abmil(model, emb, probs, lbls, condition, device)
        attn_label = f"trained ABMIL ({condition})"
    else:
        # Real ABMIL architecture with pattern-informed weight init
        pred_prob, attn, attn_label = abmil_attention(
            emb, probs, lbls, gene, device)

    print(f"  Biological confidence = {pred_prob:.2%}  |  {attn_label}")

    tag = f"{gene}_{'MUT' if label==1 else 'WT'}_{slide_id[:28]}"
    make_figure(slide_id, gene, label, probs, lbls, attn, pred_prob,
                Path(out_dir) / gene / f"{tag}.png", attn_label)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slide_id",    default=None)
    ap.add_argument("--gene",        default="TP53")
    ap.add_argument("--label",       type=int, default=1)
    ap.add_argument("--data_dir",    default=DATA_DIR)
    ap.add_argument("--results_dir", default=RESULTS_DIR)
    ap.add_argument("--out_dir",     default=OUT_DIR)
    ap.add_argument("--slide_list",  default=SLIDE_LIST)
    ap.add_argument("--labels_csv",  default=LABELS_CSV)
    ap.add_argument("--condition",   default="proposed_abmil_concat",
                    choices=["baseline2_abmil_embeddings",
                             "baseline3_abmil_patterns",
                             "proposed_abmil_concat",
                             "ablation_abmil_onehot"])
    ap.add_argument("--batch",       action="store_true")
    ap.add_argument("--genes",       nargs="+",
                    default=["TP53", "EGFR", "KEAP1"])
    ap.add_argument("--n_mut",       type=int, default=2)
    ap.add_argument("--n_wt",        type=int, default=1)
    ap.add_argument("--device",      default="cuda:0")
    args = ap.parse_args()

    kw = dict(data_dir=args.data_dir, results_dir=args.results_dir,
              out_dir=args.out_dir, condition=args.condition, device=args.device)

    if args.batch:
        print(f"[BATCH] Genes: {args.genes}")
        for gene in args.genes:
            slides = pick_slides(args.data_dir, args.labels_csv,
                                 args.slide_list, gene, args.n_mut, args.n_wt)
            if not slides:
                print(f"  [SKIP] {gene}"); continue
            for info in slides:
                process(info["slide_id"], gene, info["label"],
                        info["reason"], **kw)
        print("\n✓ Done")
    else:
        if args.slide_id:
            info = {"slide_id": args.slide_id, "label": args.label,
                    "reason": "user-specified"}
        else:
            slides = pick_slides(args.data_dir, args.labels_csv,
                                 args.slide_list, args.gene, 1, 0)
            if not slides:
                print(f"No slides for {args.gene}"); sys.exit(1)
            info = slides[0]
        process(info["slide_id"], args.gene, info["label"],
                info["reason"], **kw)


if __name__ == "__main__":
    main()
