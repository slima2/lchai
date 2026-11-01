"""Regenerate AUROC difference vs B2 heatmap with PI-ABMIL/FC-MIL labels."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

genes = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

b2 = np.array([.718, .701, .607, .684, .597, .642])

others = {
    "B1: XGB":          np.array([.518, .634, .522, .545, .489, .474]),
    "B3: ABMIL-pat":    np.array([.616, .625, .545, .617, .588, .653]),
    "PI-ABMIL (ours)":  np.array([.716, .694, .590, .695, .610, .640]),
    "Abl: one-hot":     np.array([.716, .695, .594, .691, .594, .623]),
    "FC-MIL (ours)":    np.array([.716, .684, .609, .658, .589, .661]),
}

cond_names = list(others.keys())
deltas = np.array([others[c] - b2 for c in cond_names])

vmax = max(abs(deltas.min()), abs(deltas.max())) + 0.01
cmap = plt.cm.RdBu

fig, ax = plt.subplots(figsize=(10, 4.5))
im = ax.imshow(deltas, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")

for i in range(len(cond_names)):
    for j in range(len(genes)):
        val = deltas[i, j]
        sign = "+" if val > 0 else ""
        color = "white" if abs(val) > 0.10 else "black"
        ax.text(j, i, f"{sign}{val:.3f}", ha="center", va="center",
                fontsize=10, fontweight="bold" if abs(val) > 0.01 else "normal",
                color=color)

ax.set_xticks(range(len(genes)))
ax.set_xticklabels(genes, fontsize=11, fontweight="bold")
ax.set_yticks(range(len(cond_names)))
ax.set_yticklabels(cond_names, fontsize=10)
ax.set_title("AUROC Difference vs. B2 Baseline (ABMIL Embeddings)",
             fontsize=13, fontweight="bold")

cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
cbar.set_label("delta AUROC vs B2", fontsize=10)

plt.tight_layout()
out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\auroc_difference_vs_b2.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
