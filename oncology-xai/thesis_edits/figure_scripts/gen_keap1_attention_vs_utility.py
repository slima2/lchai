"""Generate the "pattern attention != pattern usefulness" scatter for the
KEAP1 Interpretation block.

The figure plots, for each of the six representative slides, the SHAP
pattern-channel attribution (x) against the slide-level pattern ablation
delta Delta_pat = P(combined) - P(emb-only) (y, in pp).

KEAP1 is the extreme outlier: highest pattern attention (60%) and the
largest negative Delta_pat (-44.7 pp), making it the most extreme
demonstration of the cohort-wide lesson that high SHAP attention to the
pattern channel does NOT predict whether patterns will help or hurt the
prediction.

Data points:
    Gene   SHAP_pat%   Delta_pat (pp)   Outcome   Population label
    TP53   39          -16.1            TP        Conclusive
    EGFR   24          -0.5             FN        Conclusive
    KRAS   41          +7.6             TP        Inconclusive
    STK11  10          -5.5             FN        Inconclusive
    KEAP1  60          -44.7            FN        Inconclusive
    RBM10  21          +0.3             FN        Inconclusive

Sources:
    SHAP %         : Table tab:enrichment_summary in ch06_evaluation.tex
    Delta_pat      : Bottom-right ablation panel of fig:attn_<gene>_tp
                     captions (Combined - Emb-only)
    Population lab : Hosmer-Lemeshow threshold AUROC >= 0.70
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# ---------- Palette (consistent with stk11_signal_routes.png / kras_two_routes.png) ----------
OK = "#2A8C4A"        # green: helpful / Conclusive
KO = "#C0392B"        # red: harmful / Inconclusive
WARN = "#B58E00"      # amber: near-zero
NEUTRAL = "#1B3A5C"   # dark blue: ink/nodes
SOFT = "#F2EFE9"      # paper background
INK = "#222222"
GRID = "#D5D2CB"

# ---------- Data ----------
GENES = [
    # name, shap_pat, delta_pat, outcome (TP/FN), pop_label (Conc/Incon)
    ("TP53",  39, -16.1, "TP", "Conclusive"),
    ("EGFR",  24, -0.5,  "FN", "Conclusive"),
    ("KRAS",  41, +7.6,  "TP", "Inconclusive"),
    ("STK11", 10, -5.5,  "FN", "Inconclusive"),
    ("KEAP1", 60, -44.7, "FN", "Inconclusive"),
    ("RBM10", 21, +0.3,  "FN", "Inconclusive"),
]

# ---------- Figure ----------
FIG_W, FIG_H = 12.5, 7.6
fig = plt.figure(figsize=(FIG_W, FIG_H))

# Outer axis (the canvas) for title strip + scatter panel
ax_title = fig.add_axes([0.0, 0.92, 1.0, 0.08])
ax_title.set_xlim(0, 1)
ax_title.set_ylim(0, 1)
ax_title.axis("off")
ax_title.text(
    0.5, 0.62,
    "Pattern attention $\\neq$ pattern usefulness",
    ha="center", va="center", fontsize=14.5, fontweight="bold", color=INK,
)
ax_title.text(
    0.5, 0.18,
    "SHAP attribution to the pattern channel does not predict whether "
    "patterns help or hurt the slide-level prediction.",
    ha="center", va="center", fontsize=10.5, style="italic", color="#555555",
)

# Main scatter axis
ax = fig.add_axes([0.085, 0.165, 0.78, 0.71])

# Axis ranges
X_MIN, X_MAX = 0, 70
Y_MIN, Y_MAX = -52, 14

# Quadrant shading: harmful zone (Delta_pat < 0)
ax.axhspan(Y_MIN, 0, facecolor="#FBEFEC", alpha=0.55, zorder=0)
ax.axhspan(0, Y_MAX, facecolor="#EAF4EE", alpha=0.55, zorder=0)

# Zero-line (separates HELP from HURT)
ax.axhline(0, color=NEUTRAL, lw=1.2, ls="--", alpha=0.7, zorder=1)

# Quadrant labels (top-left / bottom-left, away from data and callout)
ax.text(
    1.5, Y_MAX - 1.2, "PATTERNS HELP  ($\\Delta_{\\mathrm{pat}}>0$)",
    ha="left", va="top", fontsize=10, fontweight="bold", color=OK, alpha=0.95,
)
ax.text(
    1.5, Y_MIN + 1.2, "PATTERNS HURT  ($\\Delta_{\\mathrm{pat}}<0$)",
    ha="left", va="bottom", fontsize=10, fontweight="bold", color=KO, alpha=0.95,
)

# Diagonal reference: hypothetical "attention reflects utility" trend
# (would predict +Delta_pat at high SHAP%). Show as faint dotted line so the
# divergence at KEAP1 is visually obvious.
ax.plot(
    [0, X_MAX], [0, 0.18 * X_MAX],
    color=NEUTRAL, lw=0.9, ls=":", alpha=0.45, zorder=1,
)
ax.text(
    2.0, 0.6, "expected if attention $\\Rightarrow$ utility",
    ha="left", va="bottom", fontsize=8.3, color=NEUTRAL, alpha=0.7,
    style="italic", rotation=8,
)


# Marker style: filled circle for TP, hollow for FN; colour by population label
def marker_style(outcome, pop_label):
    if pop_label == "Conclusive":
        edge = OK
        face = OK if outcome == "TP" else "white"
    else:
        edge = KO
        face = KO if outcome == "TP" else "white"
    return face, edge


for name, shap_pat, dpat, outcome, pop_label in GENES:
    face, edge = marker_style(outcome, pop_label)
    size = 320 if name == "KEAP1" else 200
    ax.scatter(
        shap_pat, dpat,
        s=size, facecolor=face, edgecolor=edge, linewidth=2.0,
        zorder=4,
    )

# Per-gene labels (offsets tuned to avoid overlap)
LABEL_OFFSETS = {
    "TP53":  (+2.2, +2.0),
    "EGFR":  (+2.4, -1.2),  # below-right of marker
    "KRAS":  (+2.2, +1.8),
    "STK11": (+2.2, +2.4),
    "KEAP1": (-3.0, 0.0),   # left of marker, vertically centred; clear of arrow tip
    "RBM10": (+2.2, +2.0),  # above-right of marker (diagonal label kept far-left)
}
LABEL_HA = {
    "KEAP1": "right",
}
LABEL_VA = {
    "KEAP1": "center",
    "RBM10": "bottom",
    "TP53":  "bottom",
    "EGFR":  "top",
    "KRAS":  "bottom",
    "STK11": "bottom",
}

for name, shap_pat, dpat, outcome, pop_label in GENES:
    dx, dy = LABEL_OFFSETS[name]
    ha = LABEL_HA.get(name, "left")
    va = LABEL_VA.get(name, "bottom")
    label = f"{name}\n({shap_pat}%, {dpat:+.1f}\u202fpp)"
    weight = "bold" if name == "KEAP1" else "normal"
    ax.text(
        shap_pat + dx, dpat + dy, label,
        ha=ha, va=va, fontsize=9.5, color=INK, fontweight=weight,
    )

# KEAP1 callout: banner above-left of KEAP1, arrow points down-right to marker.
# Banner is sized generously so the bold title and the longest body line both
# fit with comfortable padding (text was previously overflowing the box).
callout_cx, callout_cy = 24.0, -28.0
banner_w, banner_h = 38.0, 9.8
banner = FancyBboxPatch(
    (callout_cx - banner_w / 2, callout_cy - banner_h / 2), banner_w, banner_h,
    boxstyle="round,pad=0.25,rounding_size=0.40",
    linewidth=1.2, edgecolor=KO, facecolor="#FFF5F2", zorder=3,
)
ax.add_patch(banner)
ax.text(
    callout_cx, callout_cy + 2.6,
    "KEAP1: most extreme attention $\\Rightarrow$ utility divergence",
    ha="center", va="center", fontsize=10, fontweight="bold", color=KO,
)
ax.text(
    callout_cx, callout_cy - 1.4,
    "Choquet pair-bias mismatch on a spread profile:\n"
    "no superadditive pair to lock onto $\\to$ the pattern channel\n"
    "adds noise that drowns the embedding signal.",
    ha="center", va="center", fontsize=8.7, color=INK, linespacing=1.3,
)
arrow_to_keap = FancyArrowPatch(
    (callout_cx + banner_w / 2 - 0.6, callout_cy - 3.0),
    (60.0, -42.5),
    arrowstyle="-|>", mutation_scale=14, lw=1.4, color=KO, alpha=0.9, zorder=3,
)
ax.add_patch(arrow_to_keap)

# Axis labels and ticks
ax.set_xlim(X_MIN, X_MAX)
ax.set_ylim(Y_MIN, Y_MAX)
ax.set_xlabel(
    "SHAP attribution to pattern channel  (% of total)",
    fontsize=11, color=INK,
)
ax.set_ylabel(
    "$\\Delta_{\\mathrm{pat}} = P_{\\mathrm{combined}} - P_{\\mathrm{emb\\text{-}only}}$  (slide-level, pp)",
    fontsize=11, color=INK,
)
ax.set_xticks([0, 10, 20, 30, 40, 50, 60, 70])
ax.set_yticks([-50, -40, -30, -20, -10, 0, 10])
ax.tick_params(axis="both", labelsize=9.5, colors=INK)

# Light grid
ax.grid(True, which="major", color=GRID, lw=0.7, alpha=0.7, zorder=0)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
for spine in ("left", "bottom"):
    ax.spines[spine].set_color(NEUTRAL)
    ax.spines[spine].set_linewidth(1.0)

# ---------- Legend (custom, right-side strip) ----------
ax_leg = fig.add_axes([0.875, 0.165, 0.115, 0.71])
ax_leg.set_xlim(0, 1)
ax_leg.set_ylim(0, 1)
ax_leg.axis("off")

ax_leg.text(0.5, 0.97, "Legend", ha="center", va="top",
            fontsize=10.5, fontweight="bold", color=INK)

# Population label colours
ax_leg.text(0.05, 0.88, "Population label", ha="left", va="center",
            fontsize=9, fontweight="bold", color=INK)
ax_leg.scatter(0.13, 0.81, s=110, facecolor=OK, edgecolor=OK, linewidth=1.5)
ax_leg.text(0.25, 0.81, "Conclusive", ha="left", va="center", fontsize=9, color=INK)
ax_leg.scatter(0.13, 0.74, s=110, facecolor=KO, edgecolor=KO, linewidth=1.5)
ax_leg.text(0.25, 0.74, "Inconclusive", ha="left", va="center", fontsize=9, color=INK)

# Outcome
ax_leg.text(0.05, 0.62, "Slide outcome", ha="left", va="center",
            fontsize=9, fontweight="bold", color=INK)
ax_leg.scatter(0.13, 0.55, s=110, facecolor=NEUTRAL, edgecolor=NEUTRAL, linewidth=1.5)
ax_leg.text(0.25, 0.55, "True positive", ha="left", va="center", fontsize=9, color=INK)
ax_leg.scatter(0.13, 0.48, s=110, facecolor="white", edgecolor=NEUTRAL, linewidth=1.5)
ax_leg.text(0.25, 0.48, "False negative", ha="left", va="center", fontsize=9, color=INK)

# Reading note
note = (
    "READING THE\nDIVERGENCE\n\n"
    "Genes above the\ndashed zero-line:\npatterns help.\n\n"
    "Genes below:\npatterns hurt.\n\n"
    "Lower-right corner\n= attention $\\gg$ utility."
)
ax_leg.text(
    0.5, 0.24, note, ha="center", va="center",
    fontsize=8.3, color="#555555", linespacing=1.35, style="italic",
)

# ---------- Save ----------
OUT = (
    r"d:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\keap1_attention_vs_utility.png"
)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved: {OUT}")
