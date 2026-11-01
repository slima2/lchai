"""Regenerate Choquet Shapley plots for KRAS and RBM10 with non-overlapping labels."""
import matplotlib.pyplot as plt
import numpy as np
import os

OUT_DIR = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures"

PATTERNS = ["Lepidic", "Papillary", "Micropapillary", "Acinar", "Solid", "Cribriform"]
COLORS = ["#0000FF", "#FFFF00", "#00FF00", "#FF0000", "#800000", "#00FFFF"]

UNIFORM = 1.0 / 6


def plot_choquet(gene, slide, shapley, interactions, out_name):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.2), gridspec_kw={"width_ratios": [1, 1.2]})

    # ─── Left: Shapley values ───
    sorted_idx = np.argsort([shapley[p] for p in PATTERNS])
    s_patterns = [PATTERNS[i] for i in sorted_idx]
    s_values = [shapley[PATTERNS[i]] for i in sorted_idx]
    s_colors = [COLORS[i] for i in sorted_idx]
    s_deltas = [(v - UNIFORM) / UNIFORM * 100 for v in s_values]

    y_pos = np.arange(len(s_patterns))
    bars = ax1.barh(y_pos, s_values, color=s_colors, height=0.6, edgecolor="#374151", linewidth=0.5)
    ax1.axvline(x=UNIFORM, color="#9ca3af", linestyle="--", linewidth=1, label=f"Uniform (1/6)")
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(s_patterns, fontsize=8)
    ax1.set_xlabel("Shapley value ($\\phi$)", fontsize=8)
    ax1.set_title(f"Pattern Shapley Values — {gene}\n(Singleton Importance)", fontsize=9, fontweight="bold")
    ax1.legend(fontsize=7, loc="lower right")

    for i, (v, d) in enumerate(zip(s_values, s_deltas)):
        sign = "+" if d >= 0 else ""
        ax1.text(v + 0.0002, i, f"$\\phi$={v:.4f} ({sign}{d:.2f}%)",
                 va="center", fontsize=6.5, color="#374151")

    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.tick_params(labelsize=7)

    # ─── Right: Interaction indices ───
    pairs = sorted(interactions.keys(), key=lambda k: interactions[k])
    i_values = [interactions[p] for p in pairs]
    i_colors = ["#ef4444" if v < 0 else "#2563eb" for v in i_values]
    i_labels_type = ["Redundancy" if v < 0 else "Synergy" for v in i_values]

    pair_labels = [p.replace("_", " × ") for p in pairs]
    y_pos2 = np.arange(len(pairs))

    ax2.barh(y_pos2, [abs(v) for v in i_values], color=i_colors, height=0.55,
             edgecolor="#374151", linewidth=0.5)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(pair_labels, fontsize=7)
    ax2.set_xlabel("Interaction Index ($|I|$)", fontsize=8)
    ax2.set_title(f"Interaction Indices — {gene}\n(Pairwise Synergy / Redundancy)", fontsize=9, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.tick_params(labelsize=7)

    for i, (v, lt) in enumerate(zip(i_values, i_labels_type)):
        sign = "+" if v > 0 else ""
        ax2.text(abs(v) + 0.0003, i, f"{lt} ({sign}{v:.3f})",
                 va="center", fontsize=6.5, color="#374151")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, out_name)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")


# ─── KRAS (TCGA-55-7815) ───
kras_shapley = {
    "Lepidic": 0.1651, "Papillary": 0.1646, "Micropapillary": 0.1646,
    "Acinar": 0.1671, "Solid": 0.1684, "Cribriform": 0.1703,
}
kras_interactions = {
    "Lepidic_Solid": +0.0321,
    "Solid_Acinar": +0.0254,
    "Micropapillary_Cribriform": -0.0245,
    "Cribriform_Papillary": -0.0224,
    "Cribriform_Acinar": -0.0194,
}

# ─── RBM10 (TCGA-78-7148) ───
rbm10_shapley = {
    "Lepidic": 0.1664, "Papillary": 0.1664, "Micropapillary": 0.1665,
    "Acinar": 0.1668, "Solid": 0.1668, "Cribriform": 0.1671,
}
rbm10_interactions = {
    "Papillary_Lepidic": +0.0080,
    "Cribriform_Lepidic": +0.0030,
    "Micropapillary_Lepidic": +0.0030,
    "Micropapillary_Cribriform": -0.0030,
    "Redundancy_pair": -0.0019,
}
# Fix: use proper pair names for RBM10
rbm10_interactions = {
    "Papillary_Lepidic": +0.0080,
    "Cribriform_Lepidic": +0.0030,
    "Micropap._Lepidic": +0.0030,
    "Micropap._Cribriform": -0.0030,
    "Solid_Acinar": -0.0019,
}


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    plot_choquet("KRAS", "TCGA-55-7815", kras_shapley, kras_interactions, "choquet_kras_55_7815.png")
    plot_choquet("RBM10", "TCGA-78-7148", rbm10_shapley, rbm10_interactions, "choquet_rbm10_78_7148.png")
    print("Done.")
