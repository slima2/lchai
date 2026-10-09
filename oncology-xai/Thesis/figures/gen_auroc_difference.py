"""AUROC difference vs the B2 ceiling baseline (thesis Figure 6.8), regenerated from summary_table.csv."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from summary_data import load_summary, parse_args, GENES, LABELS

args = parse_args("auroc_difference_vs_b2.png")
S = load_summary(args.summary)

genes = GENES
B2 = "B2: ABMIL-emb"
b2 = np.array([S[B2][g]["auroc_mean"] for g in genes])

cond_names = [c for c in LABELS if c != B2]
deltas = np.array([[S[c][g]["auroc_mean"] for g in genes] for c in cond_names]) - b2

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
out = args.out_dir / args.out_name
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
