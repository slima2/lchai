"""Regenerate AUROC heatmap with PI-ABMIL/FC-MIL labels."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

genes = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]
conditions = ["B1: XGB", "B2: ABMIL-emb", "B3: ABMIL-pat",
              "PI-ABMIL (ours)", "Abl: one-hot", "FC-MIL (ours)"]

data = np.array([
    [.518, .634, .522, .545, .489, .474],
    [.718, .701, .607, .684, .597, .642],
    [.616, .625, .545, .617, .588, .653],
    [.716, .694, .590, .695, .610, .640],
    [.716, .695, .594, .691, .594, .623],
    [.716, .684, .609, .658, .589, .661],
])

best_per_gene = data.max(axis=0)

cmap = mcolors.LinearSegmentedColormap.from_list(
    "auroc", ["#d73027", "#fee08b", "#66bd63", "#1a9850"], N=256
)

fig, ax = plt.subplots(figsize=(10, 5))
im = ax.imshow(data, cmap=cmap, vmin=0.45, vmax=0.75, aspect="auto")

for i in range(len(conditions)):
    for j in range(len(genes)):
        val = data[i, j]
        is_best = abs(val - best_per_gene[j]) < 0.0005
        weight = "bold" if is_best else "normal"
        color = "black"
        ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                fontsize=10, fontweight=weight, color=color)
        if is_best:
            rect = plt.Rectangle((j - 0.45, i - 0.45), 0.9, 0.9,
                                  linewidth=2, edgecolor="black",
                                  facecolor="none")
            ax.add_patch(rect)

ax.set_xticks(range(len(genes)))
ax.set_xticklabels(genes, fontsize=11, fontweight="bold")
ax.set_yticks(range(len(conditions)))
ax.set_yticklabels(conditions, fontsize=10)
ax.set_title("AUROC Heatmap: Method x Gene Mutation", fontsize=13, fontweight="bold")

cbar = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
cbar.set_label("AUROC", fontsize=10)

plt.tight_layout()
out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\auroc_heatmap_ver_15_mar_2026.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
