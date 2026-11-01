"""Generate a 2x2 quadrant diagram: SHAP attribution vs Ablation utility."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\shap_ablation_quadrant.png"

fig, ax = plt.subplots(figsize=(6.5, 4.5))
ax.set_xlim(-60, 60)
ax.set_ylim(-5, 75)
ax.set_xlabel("$\\Delta_{\\mathrm{pat}}$ (pp) — Pattern Utility", fontsize=9, fontweight="bold")
ax.set_ylabel("SHAP Pattern Attribution (%)", fontsize=9, fontweight="bold")

# Quadrant backgrounds
ax.axhline(y=30, color="#d1d5db", linewidth=0.8, linestyle="--", zorder=1)
ax.axvline(x=0, color="#d1d5db", linewidth=0.8, linestyle="--", zorder=1)

# Q1: top-right (high SHAP + positive delta) — green
ax.fill_between([0, 60], 30, 75, color="#dcfce7", alpha=0.5, zorder=0)
# Q2: top-left (high SHAP + negative delta) — red
ax.fill_between([-60, 0], 30, 75, color="#fef2f2", alpha=0.5, zorder=0)
# Q3: bottom-left (low SHAP + negative delta) — orange
ax.fill_between([-60, 0], -5, 30, color="#fff7ed", alpha=0.5, zorder=0)
# Q4: bottom-right (low SHAP + positive delta) — blue
ax.fill_between([0, 60], -5, 30, color="#eff6ff", alpha=0.5, zorder=0)

# Quadrant labels
ax.text(30, 68, "Patterns attend\n& help", ha="center", va="top", fontsize=8,
        color="#166534", fontweight="bold", style="italic")
ax.text(-30, 68, "Patterns attend\nbut hurt", ha="center", va="top", fontsize=8,
        color="#991b1b", fontweight="bold", style="italic")
ax.text(-30, 2, "Patterns ignored\n& hurt anyway", ha="center", va="bottom", fontsize=8,
        color="#9a3412", fontweight="bold", style="italic")
ax.text(30, 2, "Patterns ignored\nbut help", ha="center", va="bottom", fontsize=8,
        color="#1e40af", fontweight="bold", style="italic")

# Data points — the 6 genes
genes = [
    # (delta_pp, shap_pat_pct, gene_name, color, marker)
    (+7.6,  41, "KRAS",  "#2563eb", "o"),
    (-36.1, 29, "TP53",  "#dc2626", "s"),
    (-0.5,  24, "EGFR",  "#f97316", "D"),
    (-5.5,  10, "STK11", "#8b5cf6", "^"),
    (-44.7, 60, "KEAP1", "#ef4444", "p"),
    (+0.3,  21, "RBM10", "#06b6d4", "v"),
]

for dx, shap, name, color, marker in genes:
    ax.scatter(dx, shap, c=color, s=120, marker=marker, zorder=5,
              edgecolors="#374151", linewidth=0.8)
    # offset labels to avoid overlap
    offsets = {
        "KRAS": (3, 3), "TP53": (3, -5), "EGFR": (8, 5),
        "STK11": (3, -5), "KEAP1": (-5, 3), "RBM10": (8, -7),
    }
    ox, oy = offsets.get(name, (3, 3))
    ax.annotate(
        f"{name}\n({shap}%, {dx:+.1f}pp)",
        xy=(dx, shap), xytext=(dx + ox, shap + oy),
        fontsize=6.5, fontweight="bold", color=color,
        ha="left" if ox > 0 else "right", va="bottom" if oy > 0 else "top",
        arrowprops=dict(arrowstyle="-", color=color, lw=0.6) if abs(ox) > 4 else None,
        zorder=6,
    )

# Axis annotations
ax.text(55, -3, "Patterns\nhelp →", ha="right", va="bottom", fontsize=6.5, color="#166534")
ax.text(-55, -3, "← Patterns\nhurt", ha="left", va="bottom", fontsize=6.5, color="#991b1b")
ax.text(58, 32, "High\nattribution →", ha="right", va="bottom", fontsize=6.5,
        color="#6b7280", rotation=90)
ax.text(58, 8, "← Low\nattribution", ha="right", va="bottom", fontsize=6.5,
        color="#6b7280", rotation=90)

# Threshold annotation
ax.text(-58, 30.5, "30% threshold", fontsize=6, color="#9ca3af", va="bottom")

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(labelsize=7.5)

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
