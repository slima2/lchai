"""Generate Figure 6.X for Finding 6 -- Variance subsection.

A 2D engagement map of FC-MIL relative to B2:
  x-axis: Delta AUROC (FC-MIL - B2) -- does the Choquet branch help?
  y-axis: Delta std across folds (FC-MIL - B2) -- does it engage fold-specifically?

Four quadrants:
  TR (gain>0, var>0): productive + exploratory  (RBM10)
  BR (gain>0, var<0): productive + stable       (KRAS)
  TL (gain<=0, var>0): engagement without conversion (STK11)
  BL (gain<=0, var<0): not engaged              (TP53, EGFR)

Points coloured by the regime from Figure choquet_regimes.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

THESIS_DIR = Path(r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9")
OUT = THESIS_DIR / "chapters" / "figures" / "choquet_variance_map.png"

# Palette - matches choquet_regimes for thesis-wide consistency
GREEN = "#2E7D32"
RED = "#B00020"
B2c = "#1565C0"
INK = "#222222"
SOFT = "#666666"

# Quadrant tints
TR_TINT = "#EAF4EE"
BR_TINT = "#D7EADD"
TL_TINT = "#FBECEA"
BL_TINT = "#EEF2F8"

# Gene data: (name, dAUROC, dstd, regime_color, regime_label)
# regime_color matches the regime-of-mean classification:
#   GREEN -> pair-interaction
#   RED   -> spread
#   B2c   -> embedding-dominant
genes = [
    ("RBM10", +0.019, +0.009, GREEN, "pair-interaction"),
    ("KRAS",  +0.002, -0.019, GREEN, "pair-interaction"),
    ("KEAP1", -0.008, -0.001, RED,   "spread"),
    ("STK11", -0.026, +0.035, B2c,   "embedding-dominant"),
    ("EGFR",  -0.017, -0.012, B2c,   "embedding-dominant"),
    ("TP53",  -0.002, -0.006, B2c,   "embedding-dominant"),
]

fig, ax = plt.subplots(figsize=(11.5, 6.2))

x_min, x_max = -0.040, +0.040
y_min, y_max = -0.030, +0.045

# Quadrant backgrounds
ax.add_patch(plt.Rectangle((0, 0), x_max, y_max,
                            fc=TR_TINT, ec="none", zorder=0))
ax.add_patch(plt.Rectangle((0, y_min), x_max, -y_min,
                            fc=BR_TINT, ec="none", zorder=0))
ax.add_patch(plt.Rectangle((x_min, 0), -x_min, y_max,
                            fc=TL_TINT, ec="none", zorder=0))
ax.add_patch(plt.Rectangle((x_min, y_min), -x_min, -y_min,
                            fc=BL_TINT, ec="none", zorder=0))

# Crosshair
ax.axvline(0, color="#888888", lw=1.0, zorder=1)
ax.axhline(0, color="#888888", lw=1.0, zorder=1)

# Quadrant labels (corners)
ax.text(x_max - 0.0015, y_max - 0.0015,
        "productive\n+ exploratory",
        ha="right", va="top", fontsize=10, color=GREEN,
        fontweight="bold", style="italic", zorder=2)
ax.text(x_max - 0.0015, y_min + 0.0015,
        "productive\n+ stable",
        ha="right", va="bottom", fontsize=10, color=GREEN,
        fontweight="bold", style="italic", zorder=2)
ax.text(x_min + 0.0015, y_max - 0.0015,
        "engagement\nwithout conversion",
        ha="left", va="top", fontsize=10, color=RED,
        fontweight="bold", style="italic", zorder=2)
ax.text(x_min + 0.0015, y_min + 0.0015,
        "not engaged",
        ha="left", va="bottom", fontsize=10, color=SOFT,
        fontweight="bold", style="italic", zorder=2)

# Axis-direction hints
ax.text(x_max - 0.001, -0.0008,
        r"FC-MIL helps $\rightarrow$",
        ha="right", va="top", fontsize=9, color=SOFT, style="italic")
ax.text(x_min + 0.001, -0.0008,
        r"$\leftarrow$ FC-MIL hurts",
        ha="left", va="top", fontsize=9, color=SOFT, style="italic")
ax.text(0.0008, y_max - 0.001,
        r"$\uparrow$ higher variance than B2",
        ha="left", va="top", fontsize=9, color=SOFT, style="italic")
ax.text(0.0008, y_min + 0.001,
        r"$\downarrow$ lower variance than B2",
        ha="left", va="bottom", fontsize=9, color=SOFT, style="italic")

# Plot points + labels
label_offsets = {
    "RBM10": (-0.0015, +0.0020, "right", "bottom"),
    "KRAS":  (-0.0015, -0.0020, "right", "top"),
    "KEAP1": (-0.0015, +0.0020, "right", "bottom"),
    "STK11": (+0.0020, -0.0010, "left",  "top"),
    "EGFR":  (+0.0020, +0.0010, "left",  "bottom"),
    "TP53":  (+0.0020, +0.0010, "left",  "bottom"),
}
for name, dx, dy, color, _ in genes:
    ax.scatter([dx], [dy], s=170, color=color, zorder=4,
               edgecolor="white", linewidth=1.5)
    ox, oy, ha, va = label_offsets[name]
    ax.text(dx + ox, dy + oy, name,
            ha=ha, va=va, fontsize=11, fontweight="bold",
            color=INK, zorder=5)

# Title and axis labels
ax.set_title(
    "FC-MIL engagement map: AUROC gain $\\times$ fold-to-fold variance vs. B2",
    fontsize=12.5, fontweight="bold", color=INK, pad=12, loc="left",
)
ax.set_xlabel(r"$\Delta$AUROC  (FC-MIL $-$ B2)",
              fontsize=10.5, color=INK)
ax.set_ylabel(r"$\Delta\sigma$ across folds  (FC-MIL $-$ B2)",
              fontsize=10.5, color=INK)


def fmt(x, _):
    if abs(x) < 1e-9:
        return "0"
    return f"{x:+.03f}"


ax.xaxis.set_major_formatter(plt.FuncFormatter(fmt))
ax.yaxis.set_major_formatter(plt.FuncFormatter(fmt))

ax.set_xticks(np.arange(-0.040, 0.041, 0.010))
ax.set_yticks(np.arange(-0.030, 0.046, 0.010))

ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)
ax.tick_params(axis="both", labelsize=9, colors=SOFT)

for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
ax.spines["left"].set_color(SOFT)
ax.spines["bottom"].set_color(SOFT)

plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches="tight")
plt.close()
print(f"Saved: {OUT}")
