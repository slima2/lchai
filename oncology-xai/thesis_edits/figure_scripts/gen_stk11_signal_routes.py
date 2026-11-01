"""Generate the "two routes" diagram for the STK11 Interpretation block.

The figure visualises the two routes by which STK11 biology can reach the
LCHAI v2.0 classifier on slide TCGA-49-AAR0:

  - Route 1 (microenvironment): TILs reduction + stromal texture
    changes are captured weakly by the CTransPath embedding pathway
    (Emb-only -> 10.1%). PARTIAL.
  - Route 2 (growth pattern): STK11 does not reorganise tissue into
    any of the six ANORAK growth patterns. On this slide (98.68%
    micropapillary) the 6-d pattern vector is ~one-hot and adds
    noise to the Choquet aggregator (Combined -> 4.6%). CLOSED.

The combined-vs-embeddings gap (-5.5 pp) and the Inconclusive flag
close the diagram.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ---------- Palette (consistent with kras_two_routes.png and tp53_two_scales.png) ----------
OK = "#2A8C4A"        # green: open route
KO = "#C0392B"        # red: closed route
WARN = "#B58E00"      # amber: partial route
NEUTRAL = "#1B3A5C"   # dark blue: nodes
SOFT = "#F2EFE9"      # paper background for soft boxes
INK = "#222222"

# ---------- Figure ----------
FIG_W, FIG_H = 12.5, 7.4
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")


def box(x, y, w, h, text, fc=SOFT, ec=NEUTRAL, fontsize=10,
        fontweight="normal", color=INK, lw=1.4, radius=0.12):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        linewidth=lw, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, fontweight=fontweight, color=color, wrap=True,
    )


def arrow(x1, y1, x2, y2, color=NEUTRAL, lw=1.6, style="-|>", mut=18):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=mut,
        linewidth=lw, color=color,
    )
    ax.add_patch(a)


# ---------- Title ----------
ax.text(
    FIG_W / 2, FIG_H - 0.25,
    "Where does the STK11 signal go in LCHAI v2.0?",
    ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK,
)
ax.text(
    FIG_W / 2, FIG_H - 0.55,
    "STK11 biology splits into two routes: one captured weakly, one not at all -- "
    "and on a near-homogeneous slide the second route adds noise.",
    ha="center", va="center", fontsize=10.5, style="italic", color="#555555",
)

# ---------- Source node ----------
box(
    4.6, 5.95, 3.3, 0.75,
    "STK11 mutation\n(LKB1 / immune modulator)",
    fc="#FFF6D6", ec=WARN, fontsize=10.5, fontweight="bold",
)

# Two arrows from source to the two route headers
arrow(5.8, 5.95, 2.6, 5.35, color=NEUTRAL, lw=1.8)
arrow(6.7, 5.95, 9.9, 5.35, color=NEUTRAL, lw=1.8)
ax.text(3.7, 5.65, "Route 1: microenvironment", fontsize=10, color=NEUTRAL,
        fontweight="bold", ha="center")
ax.text(8.85, 5.65, "Route 2: growth pattern reorganisation",
        fontsize=10, color=NEUTRAL, fontweight="bold", ha="center")

# ============================================================
# ROUTE 1 (LEFT): microenvironment route -- PARTIAL
# ============================================================
box(
    0.4, 4.15, 4.6, 1.10,
    "Tumour-infiltrating lymphocytes  \u2193\n"
    "Stromal / supporting-tissue\n"
    "texture changes",
    fc="#FFF6D6", ec=WARN, fontsize=10,
)

box(
    0.4, 2.70, 4.6, 1.20,
    "CTransPath embedding\n(512-d tile features)\n"
    "captures fine-grained texture",
    fc="#EAF6EE", ec=NEUTRAL, fontsize=10,
)
arrow(2.7, 4.15, 2.7, 3.90, color=NEUTRAL, lw=1.8)

# Outcome of route 1
box(
    1.25, 1.60, 2.90, 0.55,
    "PARTIAL",
    fc=WARN, ec=WARN, fontsize=11, fontweight="bold", color="white",
)
ax.text(2.70, 1.30,
        "faint STK11 signal preserved\n(Emb-only $= 10.1\\%$)",
        fontsize=9.3, color="#555555", style="italic", ha="center", va="center",
        )
arrow(2.7, 2.70, 2.7, 2.20, color=WARN, lw=1.8)

# ============================================================
# ROUTE 2 (RIGHT): growth-pattern route -- CLOSED
# ============================================================
box(
    7.5, 4.15, 4.6, 1.10,
    "STK11 does NOT reorganise tissue\n"
    "into any of the 6 ANORAK patterns\n"
    "(unlike TP53 / EGFR)",
    fc="#FBECEA", ec=KO, fontsize=10,
)

box(
    7.5, 2.70, 4.6, 1.20,
    "ANORAK 6-d vector on TCGA-49-AAR0:\n"
    "98.68% micropapillary\n"
    "$\\Rightarrow$ vector $\\approx$ one-hot $\\Rightarrow$ adds noise",
    fc="#FBECEA", ec=KO, fontsize=10,
)
arrow(9.8, 4.15, 9.8, 3.90, color=KO, lw=1.8)

# Outcome of route 2
box(
    8.35, 1.60, 2.90, 0.55,
    "CLOSED",
    fc=KO, ec=KO, fontsize=11, fontweight="bold", color="white",
)
ax.text(9.80, 1.30,
        "adds noise to the Choquet aggregator\n(Combined $= 4.6\\%$)",
        fontsize=9.3, color="#555555", style="italic", ha="center", va="center",
        )
arrow(9.8, 2.70, 9.8, 2.20, color=KO, lw=1.8)

# ============================================================
# OUTCOME STRIP -- two layered bands:
#   (1) cohort label (given by gene-level AUROC)
#   (2) slide-level mechanism (this slide explains the cohort behaviour)
# ============================================================
# --- Band 1: gene-level (given) ---
band1_y = 0.55
box(
    0.4, band1_y, 11.7, 0.42,
    "",
    fc="#F4ECDC", ec=WARN, fontsize=10, lw=1.2, radius=0.08,
)
ax.text(0.65, band1_y + 0.21,
        "Population-level (given by cohort AUROC):",
        fontsize=9.5, color="#7A5A00", fontweight="bold",
        ha="left", va="center",
        )
ax.text(4.55, band1_y + 0.21,
        r"STK11 mean 5-fold AUROC $= 0.695 < 0.70$",
        fontsize=9.7, color=INK, ha="left", va="center",
        )
ax.text(9.05, band1_y + 0.21,
        r"$\Rightarrow$",
        fontsize=11, color=INK, ha="center", va="center",
        )
box(
    9.30, band1_y + 0.04, 1.65, 0.34,
    "Inconclusive",
    fc=WARN, ec=WARN, fontsize=10, fontweight="bold", color="white",
)

# --- Band 2: slide-level mechanism (explains, does not produce, the label) ---
band2_y = 0.05
box(
    0.4, band2_y, 11.7, 0.42,
    "",
    fc="#F8F8F8", ec="#BBBBBB", fontsize=10, lw=1.0, radius=0.08,
)
ax.text(0.65, band2_y + 0.21,
        "This slide (mechanism, post-hoc):",
        fontsize=9.5, color=NEUTRAL, fontweight="bold",
        ha="left", va="center",
        )
ax.text(4.55, band2_y + 0.21,
        r"$\Delta\,P(\mathrm{mut}) = -5.5$ pp on TCGA-49-AAR0",
        fontsize=9.7, color=INK, ha="left", va="center",
        )
ax.text(8.05, band2_y + 0.21,
        r"$\Rightarrow$ explains the cohort AUROC, does not produce the label",
        fontsize=8.8, color="#555555", style="italic",
        ha="left", va="center",
        )


plt.tight_layout()
out = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\stk11_signal_routes.png"
)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
