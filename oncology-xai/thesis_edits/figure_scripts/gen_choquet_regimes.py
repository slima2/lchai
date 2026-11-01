"""Generate Figure 6.X for Finding 6: when does the Choquet branch help?

Three regimes across the six target genes:
  1. Pair-interaction regime (KRAS, RBM10): superadditive pair → FC-MIL > B2
  2. Spread regime (KEAP1): mass spread over all 6 patterns → FC-MIL < B2
  3. Embedding-dominant regime (TP53, EGFR, STK11): signal in embedding,
     Choquet ~= weighted average → FC-MIL ~= B2
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

THESIS_DIR = Path(r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9")
OUT = THESIS_DIR / "chapters" / "figures" / "choquet_regimes.png"

# Palette (matches b3_regimes for thesis-wide visual consistency)
GREEN = "#2E7D32"
AMBER = "#B58E00"
RED = "#B00020"
B2c = "#1565C0"
INK = "#222222"
SOFT = "#666666"
NEUTRAL = "#9DA3AC"
PANEL_BG = ["#EAF4EE", "#FBECEA", "#EEF2F8"]
PANEL_EC = ["#9CC8AB", "#E0A29A", "#9DB3D8"]
PANEL_HEAD = [GREEN, RED, B2c]

LABELS = ["lep", "pap", "mic", "aci", "cri", "sol"]

fig, ax = plt.subplots(figsize=(14, 6.4))
ax.set_xlim(0, 14)
ax.set_ylim(0, 6.4)
ax.axis("off")

# Title
ax.text(
    7, 6.05,
    "When does the Choquet branch (FC-MIL) help, hurt, or stay neutral?",
    ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK,
)
ax.text(
    7, 5.70,
    "three regimes across the six target genes",
    ha="center", va="center", fontsize=10, style="italic", color=SOFT,
)

# Panel geometry
margin = 0.35
gap = 0.22
total_w = 14 - 2 * margin - 2 * gap
p_w = total_w / 3
p_y = 0.30
p_h = 5.05
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
# Panel 1: Pair-interaction regime — KRAS, RBM10
# ============================================================
panel_box(xs[0], PANEL_BG[0], PANEL_EC[0])
cx = xs[0] + p_w / 2

ax.text(cx, p_y + p_h - 0.32, "Pair-interaction regime",
        ha="center", va="center", fontsize=11, fontweight="bold", color=GREEN)
ax.text(cx, p_y + p_h - 0.62,
        "KRAS, RBM10 — signal in a specific pair",
        ha="center", va="center", fontsize=9.5, color=INK)

# Six channel nodes in a horizontal line + two arcs for highlighted pairs
N_NODES = 6
node_y = p_y + 3.10
node_r = 0.16
node_spacing = (p_w - 1.20) / 5
xs_node = [cx - (p_w - 1.20) / 2 + i * node_spacing for i in range(N_NODES)]

# Two arcs: lep (0) -- sol (5) above; aci (3) -- sol (5) below
arc_top = FancyArrowPatch(
    (xs_node[0], node_y + node_r),
    (xs_node[5], node_y + node_r),
    connectionstyle="arc3,rad=-0.45",
    arrowstyle="-", color=GREEN, lw=2.0, zorder=1,
)
ax.add_patch(arc_top)
ax.text((xs_node[0] + xs_node[5]) / 2, node_y + 0.95, "+0.032",
        ha="center", va="center", fontsize=10, color=GREEN, fontweight="bold")
ax.text((xs_node[0] + xs_node[5]) / 2, node_y + 0.65,
        r"$I_{\mathrm{lep},\mathrm{sol}}$",
        ha="center", va="center", fontsize=8.5, color=GREEN, style="italic")

arc_bot = FancyArrowPatch(
    (xs_node[3], node_y - node_r),
    (xs_node[5], node_y - node_r),
    connectionstyle="arc3,rad=0.55",
    arrowstyle="-", color=GREEN, lw=1.6, zorder=1,
)
ax.add_patch(arc_bot)
ax.text((xs_node[3] + xs_node[5]) / 2, node_y - 0.85, "+0.025",
        ha="center", va="center", fontsize=10, color=GREEN, fontweight="bold")
ax.text((xs_node[3] + xs_node[5]) / 2, node_y - 0.55,
        r"$I_{\mathrm{aci},\mathrm{sol}}$",
        ha="center", va="center", fontsize=8.5, color=GREEN, style="italic")

# Nodes (highlight involved channels in green; rest in grey)
involved = {0, 3, 5}
for i, lab in enumerate(LABELS):
    fc = GREEN if i in involved else "#D8D8D8"
    ax.add_patch(plt.Circle((xs_node[i], node_y), node_r,
                             fc=fc, ec="white", lw=1.2, zorder=2))
    ax.text(xs_node[i], node_y - 0.40, lab,
            ha="center", va="center", fontsize=8.5, color=INK)

# Mechanism captions
ax.text(cx, p_y + 1.55,
        "Choquet captures superadditive pairs",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)
ax.text(cx, p_y + 1.25,
        "(IMA proxy reading: Finding 2)",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Result box
ax.add_patch(FancyBboxPatch((xs[0] + 0.18, p_y + 0.18),
                             p_w - 0.36, 0.78,
                             boxstyle="round,pad=0.02,rounding_size=0.06",
                             fc="white", ec=GREEN, lw=1.2))
ax.text(cx, p_y + 0.72,
        r"FC-MIL $>$ B2",
        ha="center", va="center", fontsize=11, fontweight="bold", color=GREEN)
ax.text(cx, p_y + 0.40,
        "KRAS $+0.002$, RBM10 $+0.019$",
        ha="center", va="center", fontsize=9.2, color=GREEN)


# ============================================================
# Panel 2: Spread regime — KEAP1
# ============================================================
panel_box(xs[1], PANEL_BG[1], PANEL_EC[1])
cx2 = xs[1] + p_w / 2

ax.text(cx2, p_y + p_h - 0.32, "Spread regime",
        ha="center", va="center", fontsize=11, fontweight="bold", color=RED)
ax.text(cx2, p_y + p_h - 0.62,
        "KEAP1 — mass diffused over all 6 patterns",
        ha="center", va="center", fontsize=9.5, color=INK)

# Flat 6-d bar profile (probability spread)
b_count = 6
b_w_total = p_w - 0.9
b_w = b_w_total / b_count
bx0 = cx2 - b_w_total / 2
by0 = p_y + p_h - 2.55
b_max_h = 1.55
heights2 = [0.18, 0.20, 0.16, 0.19, 0.15, 0.18]  # ~uniform around 1/6
for i, (lab, h) in enumerate(zip(LABELS, heights2)):
    bh = h * b_max_h * 4  # scale up for visibility while keeping flatness
    ax.add_patch(plt.Rectangle((bx0 + i * b_w + 0.05, by0),
                                b_w - 0.10, bh, fc=RED, ec="none", alpha=0.55))
    ax.text(bx0 + i * b_w + b_w / 2, by0 - 0.12, lab,
            ha="center", va="top", fontsize=8, color=SOFT)

# Reference line at 1/6
ax.plot([bx0, bx0 + b_w_total], [by0 + (1/6) * b_max_h * 4] * 2,
        color="#888888", lw=0.8, ls="--", zorder=3)
ax.text(bx0 + b_w_total + 0.03, by0 + (1/6) * b_max_h * 4,
        r"$1/6$", ha="left", va="center", fontsize=8.0, color="#888888")

ax.text(cx2, by0 + b_max_h * 4 * 0.20 + 0.30,
        r"per-tile $\mathbf{p}$ is uncertain across all 6",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Mechanism
ax.text(cx2, p_y + 1.55,
        "no superadditive pair to capture",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)
ax.text(cx2, p_y + 1.25,
        "Choquet's pair bias is the wrong inductive bias",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Result box
ax.add_patch(FancyBboxPatch((xs[1] + 0.18, p_y + 0.18),
                             p_w - 0.36, 0.78,
                             boxstyle="round,pad=0.02,rounding_size=0.06",
                             fc="white", ec=RED, lw=1.2))
ax.text(cx2, p_y + 0.72,
        r"FC-MIL $<$ B2 $<$ PI-ABMIL",
        ha="center", va="center", fontsize=10.5, fontweight="bold", color=RED)
ax.text(cx2, p_y + 0.40,
        r"KEAP1: $0.589 < 0.597 < 0.610$",
        ha="center", va="center", fontsize=9.2, color=RED)


# ============================================================
# Panel 3: Embedding-dominant regime — TP53, EGFR, STK11
# ============================================================
panel_box(xs[2], PANEL_BG[2], PANEL_EC[2])
cx3 = xs[2] + p_w / 2

ax.text(cx3, p_y + p_h - 0.32, "Embedding-dominant regime",
        ha="center", va="center", fontsize=11, fontweight="bold", color=B2c)
ax.text(cx3, p_y + p_h - 0.62,
        "TP53, EGFR, STK11 — signal in CTransPath",
        ha="center", va="center", fontsize=9.5, color=INK)

# Uniform Shapley bars + dim interaction matrix
heights3 = [1/6] * 6
bx0_3 = cx3 - b_w_total / 2
by0_3 = p_y + p_h - 2.55
for i, (lab, h) in enumerate(zip(LABELS, heights3)):
    bh = h * b_max_h * 4
    ax.add_patch(plt.Rectangle((bx0_3 + i * b_w + 0.05, by0_3),
                                b_w - 0.10, bh, fc=B2c, ec="none", alpha=0.45))
    ax.text(bx0_3 + i * b_w + b_w / 2, by0_3 - 0.12, lab,
            ha="center", va="top", fontsize=8, color=SOFT)

ax.plot([bx0_3, bx0_3 + b_w_total], [by0_3 + (1/6) * b_max_h * 4] * 2,
        color="#888888", lw=0.8, ls="--", zorder=3)
ax.text(bx0_3 + b_w_total + 0.03, by0_3 + (1/6) * b_max_h * 4,
        r"$1/6$", ha="left", va="center", fontsize=8.0, color="#888888")

ax.text(cx3, by0_3 + b_max_h * 4 * 0.20 + 0.30,
        r"learned $\phi_k \approx 1/6$,  $|I_{jk}| \ll 0.1$",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Mechanism
ax.text(cx3, p_y + 1.55,
        "Choquet branch reduces to weighted average",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)
ax.text(cx3, p_y + 1.25,
        "predictive signal lives in the embedding pathway",
        ha="center", va="center", fontsize=9, style="italic", color=SOFT)

# Result box
ax.add_patch(FancyBboxPatch((xs[2] + 0.18, p_y + 0.18),
                             p_w - 0.36, 0.78,
                             boxstyle="round,pad=0.02,rounding_size=0.06",
                             fc="white", ec=B2c, lw=1.2))
ax.text(cx3, p_y + 0.72,
        r"FC-MIL $\approx$ B2",
        ha="center", va="center", fontsize=11, fontweight="bold", color=B2c)
ax.text(cx3, p_y + 0.40,
        r"$|\Delta\mathrm{AUROC}| \leq 0.005$",
        ha="center", va="center", fontsize=9.2, color=B2c)


plt.tight_layout()
plt.savefig(OUT, dpi=200, bbox_inches="tight")
plt.close()
print(f"Saved: {OUT}")
