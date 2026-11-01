"""Generate tile filtering pipeline flowchart for thesis Chapter 5."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\tile_filtering_pipeline.png"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=7, bold=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.1", facecolor=color,
        edgecolor="#374151", linewidth=0.7, zorder=3)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4,
            linespacing=1.3)


def diamond(ax, cx, cy, w, h, text, color="#fef3c7", edgecolor="#f59e0b"):
    pts = [(cx, cy+h/2), (cx+w/2, cy), (cx, cy-h/2), (cx-w/2, cy)]
    poly = plt.Polygon(pts, facecolor=color, edgecolor=edgecolor, linewidth=0.8, zorder=3)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=6.5,
            color="#92400e", fontweight="bold", zorder=4)


def arrow(ax, x1, y1, x2, y2, color="#6b7280", text=None, textcolor="#6b7280"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.12,head_length=0.08",
                                color=color, lw=1.0))
    if text:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.15, my, text, fontsize=5.5, color=textcolor, va="center")


def reject_label(ax, x, y, text, color="#ef4444"):
    ax.text(x, y, text, fontsize=5.5, color=color, ha="center", va="center",
            style="italic", zorder=4)


fig, ax = plt.subplots(figsize=(7.5, 6.8))
ax.set_xlim(0, 10)
ax.set_ylim(0, 11)
ax.axis("off")

# Title
ax.text(5, 10.7, "Tile Filtering Pipeline", ha="center", fontsize=12,
        fontweight="bold", color="#1e293b")
ax.text(5, 10.3, "Three-stage quality control from WSI to accepted tiles",
        ha="center", fontsize=7.5, color="#64748b", style="italic")

# ─── WSI Input ───
box(ax, 0.5, 9.2, 2.0, 0.65, "Whole Slide Image\n(WSI / SVS / BIF)", "#1e40af", fontsize=6.5, bold=True)

arrow(ax, 2.5, 9.52, 3.3, 9.52)

# ─── Stage 0 ───
box(ax, 3.3, 9.0, 3.4, 1.05, "Stage 0: Global Tissue Mask\n─────────────────────\n"
    "1. Thumbnail (1/32 resolution)\n"
    "2. Greyscale → Otsu threshold\n"
    "3. Dark pixel exclusion (<80)\n"
    "4. H&E hue check\n"
    "5. Downsample to tile grid",
    "#dbeafe", textcolor="#1e3a5f", fontsize=5.5)

# Reject from Stage 0
reject_label(ax, 8.2, 9.52, "Rejected: glass,\nnon-tissue, ink\n(~60-70%)", "#3b82f6")
ax.annotate("", xy=(7.5, 9.52), xytext=(6.7, 9.52),
            arrowprops=dict(arrowstyle="->,head_width=0.1", color="#93c5fd", lw=0.8))

arrow(ax, 5.0, 9.0, 5.0, 8.3)
ax.text(5.15, 8.65, "tile candidates", fontsize=5.5, color="#6b7280")

# ─── Stage 1 ───
box(ax, 2.5, 6.6, 5.0, 1.55, "Stage 1: Per-Tile Quality Checks\n"
    "───────────────────────────\n"
    "• Background rejection (>85% pixels intensity >220)\n"
    "• Very dark tile rejection (>30% pixels intensity <50)\n"
    "• Tissue fold detection (>40% intensity <100)\n"
    "• Low texture rejection (std dev <12)\n"
    "• Low saturation rejection (HSV sat <0.03)\n"
    "• H&E hue compatibility (≥30% H&E-compatible pixels)",
    "#f0fdf4", textcolor="#14532d", fontsize=5.5)

# Reject from Stage 1
reject_label(ax, 9.0, 7.37, "Rejected:\nbackground,\nfolds, artifacts", "#16a34a")
ax.annotate("", xy=(8.3, 7.37), xytext=(7.5, 7.37),
            arrowprops=dict(arrowstyle="->,head_width=0.1", color="#86efac", lw=0.8))

arrow(ax, 5.0, 6.6, 5.0, 6.0)

# ─── Decision diamond ───
diamond(ax, 5.0, 5.5, 2.8, 0.8, "Clinical slide?\n(pen marks expected)")

# Yes branch → Stage 2
arrow(ax, 5.0, 5.1, 5.0, 4.4, text="Yes")

# No branch → skip to output
ax.annotate("", xy=(8.0, 5.5), xytext=(6.4, 5.5),
            arrowprops=dict(arrowstyle="->,head_width=0.1", color="#6b7280", lw=1.0))
ax.text(7.0, 5.65, "No (TCGA)", fontsize=5.5, color="#6b7280")

# ─── Stage 2 ───
box(ax, 2.5, 2.8, 5.0, 1.45, "Stage 2: Pen Marker & Artefact Rejection\n"
    "────────────────────────────────\n"
    "• Blue pen (B>R+40, B>G+30, B>120)\n"
    "• Red pen (R>180, R>G+50, R>B+50)\n"
    "• Green / olive / yellow markers\n"
    "• India ink, light blue / teal\n"
    "• Straight-edge detection (barcodes, labels)\n"
    "• Non-H&E colour cast rejection",
    "#fef2f2", textcolor="#7f1d1d", fontsize=5.5)

# Reject from Stage 2
reject_label(ax, 9.0, 3.52, "Rejected:\npen marks,\nlabels (+25-40%)", "#ef4444")
ax.annotate("", xy=(8.3, 3.52), xytext=(7.5, 3.52),
            arrowprops=dict(arrowstyle="->,head_width=0.1", color="#fca5a5", lw=0.8))

arrow(ax, 5.0, 2.8, 5.0, 2.1)

# ─── TCGA skip arrow joins here ───
ax.annotate("", xy=(5.5, 1.8), xytext=(8.0, 5.5),
            arrowprops=dict(arrowstyle="->,head_width=0.12", color="#6b7280", lw=1.0,
                            connectionstyle="arc3,rad=0.3"))

# ─── Output ───
box(ax, 3.2, 1.2, 3.6, 0.65, "Accepted Tissue Tiles\ne.g., 8,468 / 22,692 (37%)", "#16a34a",
    fontsize=7, bold=True)

# Example annotation
ax.text(5.0, 0.8, "→ CTransPath embedding → ABMIL / Choquet → P(mut)",
        ha="center", fontsize=6, color="#64748b", style="italic")

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
