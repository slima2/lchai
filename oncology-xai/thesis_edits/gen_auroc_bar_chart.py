"""Regenerate AUROC bar chart for ch06 with non-overlapping labels."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

genes = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

data = {
    "B1: XGB":        {"TP53": (.518,.025), "EGFR": (.634,.033), "KRAS": (.522,.057), "STK11": (.545,.055), "KEAP1": (.489,.034), "RBM10": (.474,.101)},
    "B2: ABMIL-emb":  {"TP53": (.718,.053), "EGFR": (.701,.049), "KRAS": (.607,.078), "STK11": (.684,.042), "KEAP1": (.597,.081), "RBM10": (.642,.054)},
    "B3: ABMIL-pat":  {"TP53": (.616,.043), "EGFR": (.625,.044), "KRAS": (.545,.076), "STK11": (.617,.050), "KEAP1": (.588,.031), "RBM10": (.653,.081)},
    "PI-ABMIL (ours)":  {"TP53": (.717,.058), "EGFR": (.694,.051), "KRAS": (.590,.071), "STK11": (.695,.023), "KEAP1": (.610,.071), "RBM10": (.640,.064)},
    "Abl: one-hot":      {"TP53": (.716,.050), "EGFR": (.695,.046), "KRAS": (.594,.071), "STK11": (.691,.050), "KEAP1": (.594,.082), "RBM10": (.623,.048)},
    "FC-MIL (ours)":     {"TP53": (.716,.047), "EGFR": (.684,.037), "KRAS": (.609,.059), "STK11": (.658,.077), "KEAP1": (.589,.080), "RBM10": (.661,.063)},
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
    bars = ax.bar(
        x_base + offset, means, bar_width * 0.9,
        yerr=stds, capsize=2, label=cond,
        color=colors[i], hatch=hatches[i],
        edgecolor="white", linewidth=0.5,
        error_kw={"linewidth": 0.8, "capthick": 0.8},
    )
    for bar, m, s in zip(bars, means, stds):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + s + 0.008,
            f"{m:.3f}",
            ha="center", va="bottom", fontsize=6,
            rotation=90, color="#333333",
        )

ax.axhline(y=0.5, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
ax.set_xticks(x_base)
ax.set_xticklabels(genes, fontsize=12, fontweight="bold")
ax.set_ylabel("AUROC (mean ± std)", fontsize=12)
ax.set_title("AUROC per Gene — 5-fold Stratified CV on TCGA-LUAD", fontsize=14, fontweight="bold")
ax.set_ylim(0.38, 0.85)
ax.legend(loc="upper left", fontsize=9, ncol=3, framealpha=0.9)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.grid(axis="y", alpha=0.3, linewidth=0.5)

plt.tight_layout()
out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\auroc_by_gene_ver_15_mar_2026.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
