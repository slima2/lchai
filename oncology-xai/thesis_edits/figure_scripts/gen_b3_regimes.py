"""Generate Figure 6.X: When does the pattern-only stream (B3) catch up?

Three regimes explain all B3 anomalies:
  1. Low prevalence (RBM10): B3 > B2 (implicit regulariser)
  2. Concentrated signal (EGFR): B1 approx B3 (slide-level means suffice)
  3. Default: B2 > B3 > B1
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

THESIS_DIR = Path(r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9")
OUT = THESIS_DIR / "chapters" / "figures" / "b3_regimes.png"

# Palette
B1c = "#7B7B7B"
B2c = "#1565C0"
B3c = "#2E7D32"
GREEN = "#2E7D32"
RED = "#B00020"
AMBER = "#B58E00"
INK = "#222222"
SOFT = "#666666"
PANEL_BG = ["#EAF4EE", "#FBF6E6", "#EEF2F8"]
PANEL_EC = ["#9CC8AB", "#D8C886", "#9DB3D8"]

fig, ax = plt.subplots(figsize=(14, 6.2))
ax.set_xlim(0, 14)
ax.set_ylim(0, 6.2)
ax.axis("off")

# Title block
ax.text(
    7, 5.85,
    "When does the pattern-only stream (B3) catch up?",
    ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK,
)
ax.text(
    7, 5.50,
    "two regimes explain all exceptions; everywhere else, B2 > B3 > B1",
    ha="center", va="center", fontsize=10, style="italic", color=SOFT,
)

# Panel geometry
margin = 0.35
gap = 0.22
total_w = 14 - 2 * margin - 2 * gap
p_w = total_w / 3
p_y = 0.30
p_h = 4.85
xs = [margin + i * (p_w + gap) for i in range(3)]


def panel_box(x, fc, ec):
    ax.add_patch(
        FancyBboxPatch(
            (x, p_y), p_w, p_h,
            boxstyle="round,pad=0.04,rounding_size=0.10",
            fc=fc, ec=ec, lw=1.0,
        )
    )


# ============================================================
# Panel 1: RBM10 — Low-prevalence regime
# ============================================================
panel_box(xs[0], PANEL_BG[0], PANEL_EC[0])
cx = xs[0] + p_w / 2

ax.text(cx, p_y + p_h - 0.32, "Low-prevalence regime",
        ha="center", va="center", fontsize=11, fontweight="bold", color=GREEN)
ax.text(cx, p_y + p_h - 0.62,
        "RBM10 — 37 / 687 mutated (5.4%)",
        ha="center", va="center", fontsize=9.5, color=INK)

# Prevalence grid: 30 squares, 2 red
grid_cols = 10
grid_rows = 3
sq = (p_w - 0.7) / grid_cols
g_x0 = cx - (grid_cols * sq) / 2
g_y0 = p_y + p_h - 1.20
mut_idx = {0, 11}  # 2 of 30 highlighted as mutated
for r in range(grid_rows):
    for c in range(grid_cols):
        i = r * grid_cols + c
        fc = RED if i in mut_idx else "#D8D8D8"
        ax.add_patch(
            plt.Rectangle(
                (g_x0 + c * sq, g_y0 - r * sq * 0.85),
                sq * 0.82, sq * 0.65, fc=fc, ec="none",
            )
        )

ax.text(cx, p_y + p_h - 2.05,
        "few positives  $\\rightarrow$  high-d models overfit",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Input-dimension comparison
ax.text(cx, p_y + p_h - 2.55, "input dimension at the head",
        ha="center", va="center", fontsize=9.5, fontweight="bold", color=INK)

bar_full_w = p_w - 0.9
# B2: 512-d (full bar)
ax.add_patch(plt.Rectangle((cx - bar_full_w / 2, p_y + 1.50),
                            bar_full_w, 0.32, fc=B2c, ec="none"))
ax.text(cx, p_y + 1.66, "B2: 512-d",
        ha="center", va="center", fontsize=9, color="white", fontweight="bold")

# B3: 6-d (tiny, with explicit ~85x note)
b3_w = max(bar_full_w * 6 / 512 * 30, 0.22)
ax.add_patch(plt.Rectangle((cx - b3_w / 2, p_y + 1.05),
                            b3_w, 0.32, fc=B3c, ec="none"))
ax.text(cx + b3_w / 2 + 0.10, p_y + 1.21, "B3: 6-d",
        ha="left", va="center", fontsize=9, color=B3c, fontweight="bold")
ax.text(cx, p_y + 0.85,
        r"$\sim$85$\times$ smaller  $\rightarrow$  implicit regulariser",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Result
ax.add_patch(FancyBboxPatch((xs[0] + 0.18, p_y + 0.18),
                             p_w - 0.36, 0.50,
                             boxstyle="round,pad=0.02,rounding_size=0.06",
                             fc="white", ec=GREEN, lw=1.2))
ax.text(cx, p_y + 0.43,
        r"B3 $=$ 0.653  $>$  B2 $=$ 0.642",
        ha="center", va="center", fontsize=10.5, fontweight="bold", color=GREEN)


# ============================================================
# Panel 2: EGFR — Concentrated-signal regime
# ============================================================
panel_box(xs[1], PANEL_BG[1], PANEL_EC[1])
cx2 = xs[1] + p_w / 2

ax.text(cx2, p_y + p_h - 0.32, "Concentrated-signal regime",
        ha="center", va="center", fontsize=11, fontweight="bold", color=AMBER)
ax.text(cx2, p_y + p_h - 0.62,
        "EGFR — signal lives in 1--2 patterns",
        ha="center", va="center", fontsize=9.5, color=INK)

# 6-d ANORAK profile (lepidic + papillary tall)
labels = ["lep", "pap", "micro", "acin", "crib", "sol"]
heights = [0.92, 0.78, 0.10, 0.14, 0.08, 0.06]
b_count = len(labels)
b_w_total = p_w - 0.7
b_w = b_w_total / b_count
bx0 = cx2 - b_w_total / 2
by0 = p_y + p_h - 2.50
b_max_h = 1.30
for i, (lab, h) in enumerate(zip(labels, heights)):
    bh = h * b_max_h
    color = AMBER if h > 0.5 else "#C8C8C8"
    ax.add_patch(plt.Rectangle((bx0 + i * b_w + 0.05, by0),
                                b_w - 0.10, bh, fc=color, ec="none"))
    ax.text(bx0 + i * b_w + b_w / 2, by0 - 0.12, lab,
            ha="center", va="top", fontsize=8, color=SOFT)

ax.text(cx2, by0 + b_max_h + 0.18,
        "two channels carry most of the signal",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

ax.text(cx2, p_y + 1.55,
        r"argmax($\mathbf{p}$) $\approx$ full $\mathbf{p}$",
        ha="center", va="center", fontsize=9.5, color=INK)
ax.text(cx2, p_y + 1.25,
        "slide-level mean of \"% lepidic\" suffices",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Result
ax.add_patch(FancyBboxPatch((xs[1] + 0.18, p_y + 0.18),
                             p_w - 0.36, 0.78,
                             boxstyle="round,pad=0.02,rounding_size=0.06",
                             fc="white", ec=AMBER, lw=1.2))
ax.text(cx2, p_y + 0.72,
        r"B1 $=$ 0.634  $\approx$  B3 $=$ 0.625",
        ha="center", va="center", fontsize=10.5, fontweight="bold", color=AMBER)
ax.text(cx2, p_y + 0.38,
        "(B2 $=$ 0.701 still wins on its embedding)",
        ha="center", va="center", fontsize=9, color=SOFT, style="italic")


# ============================================================
# Panel 3: Default regime
# ============================================================
panel_box(xs[2], PANEL_BG[2], PANEL_EC[2])
cx3 = xs[2] + p_w / 2

ax.text(cx3, p_y + p_h - 0.32, "Default regime",
        ha="center", va="center", fontsize=11, fontweight="bold", color=B2c)
ax.text(cx3, p_y + p_h - 0.62,
        "TP53, STK11, KEAP1, KRAS",
        ha="center", va="center", fontsize=9.5, color=INK)

# distributed bar profile
heights3 = [0.55, 0.42, 0.65, 0.48, 0.38, 0.58]
for i, (lab, h) in enumerate(zip(labels, heights3)):
    bh = h * b_max_h
    ax.add_patch(plt.Rectangle((bx0 - xs[1] + xs[2] + i * b_w + 0.05, by0),
                                b_w - 0.10, bh, fc="#7C97C7", ec="none"))
    ax.text(bx0 - xs[1] + xs[2] + i * b_w + b_w / 2, by0 - 0.12, lab,
            ha="center", va="top", fontsize=8, color=SOFT)

ax.text(cx3, by0 + b_max_h + 0.18,
        "signal spread across patterns",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

ax.text(cx3, p_y + 1.55,
        "embedding adds discriminative bits",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)
ax.text(cx3, p_y + 1.25,
        "within-slide attention beats slide means",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Result
ax.add_patch(FancyBboxPatch((xs[2] + 0.18, p_y + 0.18),
                             p_w - 0.36, 0.78,
                             boxstyle="round,pad=0.02,rounding_size=0.06",
                             fc="white", ec=B2c, lw=1.2))
ax.text(cx3, p_y + 0.72,
        r"B2 $\;>\;$ B3 $\;>\;$ B1",
        ha="center", va="center", fontsize=12, fontweight="bold", color=B2c)
ax.text(cx3, p_y + 0.38,
        "(systematic gap on five of six genes)",
        ha="center", va="center", fontsize=9, color=SOFT, style="italic")


plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches="tight")
plt.close()
print(f"Saved: {OUT}")
