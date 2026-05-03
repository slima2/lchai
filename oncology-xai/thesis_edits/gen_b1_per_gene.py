"""Generate Figure 6.X for Finding 5: B1 (XGBoost on slide-level pattern
frequencies) AUROC by gene.

Visualises three observations that motivate the section:
  - heterogeneity across genes (range 0.474-0.634)
  - EGFR sits at the top (concentrated-signal regime; Finding 4)
  - KEAP1 and RBM10 fall below the random line (naive aggregation fails)
  - mean 0.530 sits well below B3 (0.607) and B2 (0.658)
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

THESIS_DIR = Path(r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9")
OUT = THESIS_DIR / "chapters" / "figures" / "b1_per_gene.png"

INK = "#222222"
SOFT = "#666666"
AMBER = "#B58E00"
GREEN = "#2E7D32"
B2c = "#1565C0"
RED = "#B00020"
NEUTRAL = "#9DA3AC"

# Data sorted ascending by AUROC so highest is at top in horizontal bar chart
data = [
    ("RBM10", 0.474, "below"),
    ("KEAP1", 0.489, "below"),
    ("TP53",  0.518, "neutral"),
    ("KRAS",  0.522, "neutral"),
    ("STK11", 0.545, "neutral"),
    ("EGFR",  0.634, "top"),
]
B1_MEAN = 0.530
B3_MEAN = 0.607
B2_MEAN = 0.658
RANDOM = 0.500

color_map = {
    "below":   RED,
    "neutral": NEUTRAL,
    "top":     AMBER,
}

fig, ax = plt.subplots(figsize=(12, 5.6))

# Bars
y_pos = np.arange(len(data))
bar_h = 0.62
for i, (gene, auc, kind) in enumerate(data):
    ax.barh(i, auc, height=bar_h, color=color_map[kind],
            edgecolor="none", zorder=2)
    # AUROC value at end of bar
    ax.text(auc + 0.005, i, f"{auc:.3f}",
            va="center", ha="left", fontsize=10, color=INK,
            fontweight="bold", zorder=3)

ax.set_yticks(y_pos)
ax.set_yticklabels([g for g, _, _ in data], fontsize=11, color=INK)
ax.tick_params(axis="y", length=0)

# x-axis
ax.set_xlim(0.40, 0.78)
ax.set_xlabel("B1 AUROC (5-fold CV)", fontsize=10.5, color=INK)
ax.tick_params(axis="x", labelsize=9.5, colors=SOFT)

# Reference lines: random, B1 mean, B3 mean, B2 mean
def vline(x, color, label_top, label_bottom, lw=1.2, ls="--"):
    ax.axvline(x, color=color, lw=lw, ls=ls, zorder=1)
    ax.text(x, len(data) - 0.30, label_top,
            ha="center", va="bottom", fontsize=8.8, color=color,
            fontweight="bold", rotation=0)
    ax.text(x, -0.65, label_bottom,
            ha="center", va="top", fontsize=8.6, color=color)

vline(RANDOM, "#888888", "random", "0.500", ls=":")
vline(B1_MEAN, INK, "B1 mean", "0.530")
vline(B3_MEAN, GREEN, "B3 mean", "0.607")
vline(B2_MEAN, B2c, "B2 mean", "0.658")

# Highlight regions / annotations
# EGFR annotation
ax.annotate(
    "concentrated-signal regime\n(Finding 4: lepidic-predominant)",
    xy=(0.634, 5), xytext=(0.690, 4.55),
    fontsize=9.0, color=AMBER, ha="left", va="center", style="italic",
    arrowprops=dict(arrowstyle="-", color=AMBER, lw=1.0),
)

# Below-random annotation
ax.annotate(
    "below random:\nno single-pattern correlate,\nnaive aggregation fails",
    xy=(0.482, 0.5), xytext=(0.560, 1.10),
    fontsize=9.0, color=RED, ha="left", va="center", style="italic",
    arrowprops=dict(arrowstyle="-", color=RED, lw=1.0),
)

# Title
ax.set_title(
    "B1 (XGBoost on slide-level pattern frequencies) AUROC by gene",
    fontsize=12.5, fontweight="bold", color=INK, pad=14, loc="left",
)

# Axes cosmetics
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color(SOFT)
ax.spines["bottom"].set_color(SOFT)
ax.set_axisbelow(True)
ax.grid(axis="x", color="#EEEEEE", lw=0.8, zorder=0)

# Margin so vertical-line labels at top fit
ax.set_ylim(-0.9, len(data) + 0.2)

plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches="tight")
plt.close()
print(f"Saved: {OUT}")
