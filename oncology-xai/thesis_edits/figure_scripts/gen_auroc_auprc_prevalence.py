"""Generate AUROC vs AUPRC vs prevalence figure for ch06 evaluation chapter.

Visualises why the AUROC-AUPRC gap correlates inversely with mutation
prevalence: the per-gene "best AUROC" stays in a narrow band (0.61-0.72)
regardless of prevalence, while AUPRC tracks the random baseline
(= prevalence/100) closely and is therefore much lower for rare mutations.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Genes sorted by ascending prevalence in TCGA-LUAD (5-fold CV cohort)
# Sources:
#   - prevalence: ch04_methodology.tex (RBM10, STK11, EGFR), ch06 (TP53),
#                 ch07 (KRAS), ch06 fig:auroc_by_gene caption (KEAP1)
#   - AUROC (mean, 5-fold CV): tab:mutation_luad column-wise maxima
#   - AUPRC (mean, 5-fold CV): fig:auprc_by_gene values for the same
#     condition that achieves the best AUROC
genes = ["RBM10", "STK11", "EGFR", "KEAP1", "KRAS", "TP53"]
prevalence = np.array([5.4, 9.9, 11.4, 14.3, 20.4, 46.0])
auroc = np.array([0.661, 0.695, 0.701, 0.610, 0.609, 0.718])
auprc = np.array([0.170, 0.320, 0.360, 0.300, 0.340, 0.640])
best_method = ["FC-MIL", "PI-ABMIL", "B2", "PI-ABMIL", "FC-MIL", "B2"]

baseline = prevalence / 100.0
gap = auroc - auprc

# Use categorical x positions so spacing is uniform; annotate prevalence below
x = np.arange(len(genes))

fig, ax = plt.subplots(figsize=(11, 6.2))

# Shade the AUROC-AUPRC gap as a vertical band per gene
for xi, hi, lo in zip(x, auroc, auprc):
    ax.fill_between(
        [xi - 0.18, xi + 0.18],
        [lo, lo],
        [hi, hi],
        color="#7EC8E3",
        alpha=0.35,
        linewidth=0,
    )
    ax.annotate(
        f"{hi - lo:+.2f}",
        xy=(xi + 0.22, (hi + lo) / 2),
        ha="left",
        va="center",
        fontsize=9,
        color="#1B3A5C",
        fontweight="bold",
    )

# AUROC markers (best per gene)
ax.plot(
    x,
    auroc,
    "o",
    color="#1B3A5C",
    markersize=11,
    markeredgecolor="white",
    markeredgewidth=1.2,
    label="Mean AUROC (best condition per gene)",
    zorder=3,
)

# AUPRC markers (same condition)
ax.plot(
    x,
    auprc,
    "s",
    color="#E05252",
    markersize=11,
    markeredgecolor="white",
    markeredgewidth=1.2,
    label="Mean AUPRC (same condition)",
    zorder=3,
)

# AUPRC random baseline (= prevalence) as gray triangles + connecting line
ax.plot(
    x,
    baseline,
    "^--",
    color="#888888",
    markersize=8,
    linewidth=1.0,
    alpha=0.85,
    label="AUPRC random baseline (= prevalence)",
    zorder=2,
)

# Reference line: AUROC random = 0.50
ax.axhline(0.50, color="#666666", linestyle=":", linewidth=0.9, alpha=0.7)
ax.text(
    len(genes) - 0.5,
    0.51,
    "AUROC random = 0.50",
    fontsize=8,
    color="#666666",
    ha="right",
    va="bottom",
)

# Best-method annotation above each AUROC marker
for xi, hi, m in zip(x, auroc, best_method):
    ax.annotate(
        m,
        xy=(xi, hi),
        xytext=(0, 12),
        textcoords="offset points",
        ha="center",
        fontsize=8,
        color="#1B3A5C",
    )

# X-axis: gene name + prevalence
xtick_labels = [f"{g}\n({p:.1f}%)" for g, p in zip(genes, prevalence)]
ax.set_xticks(x)
ax.set_xticklabels(xtick_labels, fontsize=11)
ax.set_xlabel(
    "Target gene (sorted by ascending mutation prevalence in TCGA-LUAD)",
    fontsize=12,
)
ax.set_ylabel("Metric value (mean over 5-fold CV)", fontsize=12)
ax.set_title(
    "AUROC, AUPRC and the prevalence-driven gap on TCGA-LUAD",
    fontsize=13,
    fontweight="bold",
)

ax.set_ylim(0.0, 0.85)
ax.set_xlim(-0.5, len(genes) - 0.5)
ax.legend(loc="upper left", fontsize=9, framealpha=0.92)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3, linewidth=0.5)

# Footer: explanatory text
fig.text(
    0.5,
    -0.02,
    "Blue band = AUROC-AUPRC gap. As prevalence increases, the gap shrinks because"
    " the AUPRC random baseline rises towards AUROC, while AUROC stays in a narrow"
    " band (0.61-0.72) independent of prevalence.",
    ha="center",
    fontsize=8.5,
    color="#444444",
    style="italic",
    wrap=True,
)

plt.tight_layout()
out = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\auroc_auprc_prevalence.png"
)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
