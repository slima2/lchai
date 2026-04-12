"""Regenerate AUROC radar plot with PI-ABMIL/FC-MIL labels."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

genes = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]

conditions = {
    "B2: ABMIL-emb":    [.718, .701, .607, .684, .597, .642],
    "B3: ABMIL-pat":    [.616, .625, .545, .617, .588, .653],
    "PI-ABMIL (ours)":  [.716, .694, .590, .695, .610, .640],
    "FC-MIL (ours)":    [.716, .684, .609, .658, .589, .661],
}

colors = ["#1B3A5C", "#2E8B57", "#E05252", "#F5A623"]
n = len(genes)
angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

for (name, vals), color in zip(conditions.items(), colors):
    vals_closed = vals + vals[:1]
    ax.plot(angles, vals_closed, "o-", linewidth=2, label=name, color=color, markersize=6)
    ax.fill(angles, vals_closed, alpha=0.08, color=color)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(genes, fontsize=13, fontweight="bold")
ax.set_ylim(0.48, 0.75)
ax.set_rticks([0.50, 0.55, 0.60, 0.65, 0.70])
ax.set_title("AUROC Profile Across Genes", fontsize=15, fontweight="bold", pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), fontsize=10)

plt.tight_layout()
out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\auroc_radar_profile.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
