"""AUROC bar chart per gene (thesis Figure 6.6), regenerated from summary_table.csv."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from summary_data import load_summary, parse_args, GENES, LABELS, COLORS, HATCHES

args = parse_args("auroc_by_gene.png")
S = load_summary(args.summary)

genes = GENES
conditions = LABELS
n_cond = len(conditions)
n_genes = len(genes)

fig, ax = plt.subplots(figsize=(18, 7))

group_width = 0.75
bar_width = group_width / n_cond
x_base = np.arange(n_genes)

for i, cond in enumerate(conditions):
    means = [S[cond][g]["auroc_mean"] for g in genes]
    stds  = [S[cond][g]["auroc_std"] for g in genes]
    offset = (i - (n_cond - 1) / 2) * bar_width
    bars = ax.bar(
        x_base + offset, means, bar_width * 0.9,
        yerr=stds, capsize=2, label=cond,
        color=COLORS[cond], hatch=HATCHES[cond],
        edgecolor="white", linewidth=0.5,
        error_kw={"linewidth": 0.8, "capthick": 0.8},
    )
    for bar, m, s in zip(bars, means, stds):
        label = f".{int(round(m*1000)):03d}±.{int(round(s*1000)):03d}"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + s + 0.005,
            label,
            ha="center", va="bottom", fontsize=5.5,
            rotation=90, color="#333333",
            fontfamily="monospace",
        )

ax.axhline(y=0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
ax.set_xticks(x_base)
ax.set_xticklabels(genes, fontsize=12, fontweight="bold")
ax.set_ylabel("AUROC (mean ± std)", fontsize=12)
ax.set_title("AUROC per Gene — 5-fold Stratified CV on TCGA-LUAD", fontsize=14, fontweight="bold")
ax.set_ylim(0.38, 0.88)
ax.legend(loc="upper left", fontsize=9, ncol=3, framealpha=0.9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3, linewidth=0.5)

plt.tight_layout()
out = args.out_dir / args.out_name
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
