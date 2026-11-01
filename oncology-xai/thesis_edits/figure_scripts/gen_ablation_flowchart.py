"""Generate a causal chain diagram showing how the 3 ablation models produce P(mut)."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import os

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\ablation_causal_chain.png"


def rounded_box(ax, xy, w, h, text, color, textcolor="white", fontsize=7.5, bold=False):
    box = mpatches.FancyBboxPatch(
        xy, w, h, boxstyle="round,pad=0.12", facecolor=color,
        edgecolor="#374151", linewidth=0.8, zorder=3,
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(xy[0] + w / 2, xy[1] + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4)


def arrow(ax, start, end, color="#6b7280"):
    ax.annotate("", xy=end, xytext=start,
                arrowprops=dict(arrowstyle="->,head_width=0.15,head_length=0.1",
                                color=color, lw=1.2, connectionstyle="arc3,rad=0"),
                zorder=2)


def label_above(ax, xy, text, fontsize=6.5, color="#6b7280"):
    ax.text(xy[0], xy[1], text, ha="center", va="bottom", fontsize=fontsize,
            color=color, style="italic", zorder=4)


fig, ax = plt.subplots(figsize=(7.0, 4.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 6.5)
ax.axis("off")

# Title
ax.text(5, 6.2, "Causal Chain: From Tile Features to $P(\\mathrm{mut})$",
        ha="center", va="center", fontsize=11, fontweight="bold", color="#1e293b")
ax.text(5, 5.85, "Three independently trained models — not components of a single prediction",
        ha="center", va="center", fontsize=7.5, color="#64748b", style="italic")

# ─── Input layer ───
rounded_box(ax, (0.3, 4.5), 2.0, 0.65, "$\\mathbf{x}_i \\in \\mathbb{R}^{512}$\nCTransPath\nEmbeddings", "#3b82f6", fontsize=6.5)
rounded_box(ax, (0.3, 3.3), 2.0, 0.65, "$\\mathbf{p}_i \\in \\Delta^5$\nFuzzy Pattern\nProbabilities", "#ef4444", fontsize=6.5)

# ─── Model P (Combined) ───
rounded_box(ax, (3.5, 4.9), 2.4, 0.55, "ABMIL  $[\\mathbf{x}_i \\| \\mathbf{p}_i]$", "#2563eb", fontsize=7)
label_above(ax, (4.7, 5.55), "Model P (Combined, 518-d)", fontsize=6.5, color="#2563eb")
arrow(ax, (2.3, 4.82), (3.5, 5.17))
arrow(ax, (2.3, 3.62), (3.5, 5.05))

# ─── Model B2 (Emb-only) ───
rounded_box(ax, (3.5, 3.7), 2.4, 0.55, "ABMIL  $\\mathbf{x}_i$ only", "#f97316", fontsize=7)
label_above(ax, (4.7, 4.35), "Model B2 (Emb-only, 512-d)", fontsize=6.5, color="#f97316")
arrow(ax, (2.3, 4.82), (3.5, 3.97))

# ─── Model B3 (Pat-only) ───
rounded_box(ax, (3.5, 2.5), 2.4, 0.55, "ABMIL  $\\mathbf{p}_i$ only", "#7c3aed", fontsize=7)
label_above(ax, (4.7, 3.15), "Model B3 (Pat-only, 6-d)", fontsize=6.5, color="#7c3aed")
arrow(ax, (2.3, 3.62), (3.5, 2.77))

# ─── Sigmoid + P(mut) outputs ───
sx = 6.8
rounded_box(ax, (sx, 4.9), 1.0, 0.55, "$\\sigma(\\cdot)$", "#e5e7eb", textcolor="#374151", fontsize=8)
rounded_box(ax, (sx, 3.7), 1.0, 0.55, "$\\sigma(\\cdot)$", "#e5e7eb", textcolor="#374151", fontsize=8)
rounded_box(ax, (sx, 2.5), 1.0, 0.55, "$\\sigma(\\cdot)$", "#e5e7eb", textcolor="#374151", fontsize=8)

arrow(ax, (5.9, 5.17), (sx, 5.17))
arrow(ax, (5.9, 3.97), (sx, 3.97))
arrow(ax, (5.9, 2.77), (sx, 2.77))

# ─── P(mut) outputs ───
px = 8.4
rounded_box(ax, (px, 4.9), 1.3, 0.55, "$P_{\\mathrm{comb}}$", "#2563eb", fontsize=8, bold=True)
rounded_box(ax, (px, 3.7), 1.3, 0.55, "$P_{\\mathrm{emb}}$", "#f97316", fontsize=8, bold=True)
rounded_box(ax, (px, 2.5), 1.3, 0.55, "$P_{\\mathrm{pat}}$", "#7c3aed", fontsize=8, bold=True)

arrow(ax, (sx + 1.0, 5.17), (px, 5.17))
arrow(ax, (sx + 1.0, 3.97), (px, 3.97))
arrow(ax, (sx + 1.0, 2.77), (px, 2.77))

# ─── Delta annotation ───
ax.annotate("", xy=(9.05, 4.9), xytext=(9.05, 4.25),
            arrowprops=dict(arrowstyle="<->", color="#dc2626", lw=1.5))
ax.text(9.5, 4.55, "$\\Delta_{\\mathrm{pat}}$", fontsize=9, color="#dc2626",
        fontweight="bold", ha="center", va="center")

# ─── Bottom explanation ───
ax.text(5, 1.7, "$\\Delta_{\\mathrm{pat}} = P_{\\mathrm{comb}} - P_{\\mathrm{emb}}$",
        ha="center", fontsize=10, color="#1e293b", fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#fef3c7", edgecolor="#f59e0b", linewidth=0.8))

ax.text(5, 1.1,
        "$\\Delta_{\\mathrm{pat}} > 0$: patterns help (constructive)     "
        "$\\Delta_{\\mathrm{pat}} < 0$: patterns hurt (destructive interference)",
        ha="center", fontsize=7, color="#64748b")

ax.text(5, 0.65,
        "Note: $P(\\mathrm{mut})$ in the gene header comes from the gene-optimal model,\n"
        "which may be any of these three or a different architecture (FC-MIL).",
        ha="center", fontsize=6.5, color="#94a3b8", style="italic")

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
