"""AUROC radar profile for four conditions (thesis Figure 6.9), regenerated from summary_table.csv."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from summary_data import load_summary, parse_args, GENES, COLORS

args = parse_args("auroc_radar_profile.png")
S = load_summary(args.summary)

genes = GENES
radar_conditions = ["B2: ABMIL-emb", "B3: ABMIL-pat", "PI-ABMIL (ours)", "FC-MIL (ours)"]
conditions = {c: [S[c][g]["auroc_mean"] for g in genes] for c in radar_conditions}

n = len(genes)
angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

for name, vals in conditions.items():
    vals_closed = vals + vals[:1]
    ax.plot(angles, vals_closed, "o-", linewidth=2, label=name, color=COLORS[name], markersize=6)
    ax.fill(angles, vals_closed, alpha=0.08, color=COLORS[name])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(genes, fontsize=13, fontweight="bold")
ax.set_ylim(0.48, 0.75)
ax.set_rticks([0.50, 0.55, 0.60, 0.65, 0.70])
ax.set_title("AUROC Profile Across Genes", fontsize=15, fontweight="bold", pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.25, 1.12), fontsize=10)

plt.tight_layout()
out = args.out_dir / args.out_name
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
