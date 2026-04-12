"""Regenerate AUPRC bar chart with PI-ABMIL/FC-MIL labels."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

genes = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

# AUPRC values from the evaluation logs (mean +/- std across 5 folds)
data = {
    "B1: XGB":           {"TP53": (.530,.04), "EGFR": (.310,.05), "KRAS": (.310,.04), "STK11": (.170,.04), "KEAP1": (.260,.03), "RBM10": (.130,.05)},
    "B2: ABMIL-emb":     {"TP53": (.640,.06), "EGFR": (.360,.06), "KRAS": (.340,.06), "STK11": (.310,.06), "KEAP1": (.290,.05), "RBM10": (.170,.06)},
    "B3: ABMIL-pat":     {"TP53": (.550,.05), "EGFR": (.310,.05), "KRAS": (.300,.05), "STK11": (.260,.05), "KEAP1": (.270,.04), "RBM10": (.170,.06)},
    "PI-ABMIL (ours)":   {"TP53": (.630,.06), "EGFR": (.350,.06), "KRAS": (.330,.06), "STK11": (.320,.05), "KEAP1": (.300,.05), "RBM10": (.160,.05)},
    "Abl: one-hot":      {"TP53": (.630,.06), "EGFR": (.350,.06), "KRAS": (.330,.05), "STK11": (.310,.06), "KEAP1": (.280,.05), "RBM10": (.150,.05)},
    "FC-MIL (ours)":     {"TP53": (.630,.06), "EGFR": (.340,.05), "KRAS": (.340,.05), "STK11": (.290,.06), "KEAP1": (.280,.06), "RBM10": (.170,.06)},
}

conditions = list(data.keys())
n_cond = len(conditions)
n_genes = len(genes)

colors = ["#7EC8E3", "#1B3A5C", "#2E8B57", "#E05252", "#B0A0D0", "#F5A623"]
hatches = ["", "", "", "", "//", ""]

fig, ax = plt.subplots(figsize=(16, 6))

group_width = 0.75
bar_width = group_width / n_cond
x_base = np.arange(n_genes)

for i, cond in enumerate(conditions):
    means = [data[cond][g][0] for g in genes]
    stds  = [data[cond][g][1] for g in genes]
    offset = (i - (n_cond - 1) / 2) * bar_width
    ax.bar(
        x_base + offset, means, bar_width * 0.9,
        yerr=stds, capsize=2, label=cond,
        color=colors[i], hatch=hatches[i],
        edgecolor="white", linewidth=0.5,
        error_kw={"linewidth": 0.8, "capthick": 0.8},
    )

ax.set_xticks(x_base)
ax.set_xticklabels(genes, fontsize=12, fontweight="bold")
ax.set_ylabel("AUPRC (mean ± std)", fontsize=12)
ax.set_title("AUPRC per Gene — 5-fold Stratified CV on TCGA-LUAD", fontsize=14, fontweight="bold")
ax.set_ylim(0.0, 0.85)
ax.legend(loc="upper left", fontsize=9, ncol=3, framealpha=0.9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3, linewidth=0.5)

plt.tight_layout()
out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\auprc_by_gene.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
