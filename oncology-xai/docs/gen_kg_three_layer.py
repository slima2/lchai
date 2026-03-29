"""Generate the three-layer KG architecture diagram for the thesis."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

fig, axes = plt.subplots(3, 1, figsize=(14, 11.5), gridspec_kw={"height_ratios": [1.1, 0.7, 0.8]})
fig.subplots_adjust(hspace=0.08, left=0.02, right=0.98, top=0.97, bottom=0.02)

# Colors
C_PATTERN = "#F5A623"   # orange
C_GENE    = "#E74C3C"   # red
C_TREAT   = "#9B59B6"   # purple
C_DIAG    = "#27AE60"   # green (dark)
C_CASE    = "#3498DB"   # blue
C_PROV    = "#95A5A6"   # grey
C_FADED   = "#D5D5D5"   # faded/inactive

def draw_node(ax, x, y, label, color, size=0.045, fontsize=8, alpha=1.0, sublabel=None):
    circle = plt.Circle((x, y), size, color=color, alpha=alpha, ec="white", lw=1.5, zorder=3)
    ax.add_patch(circle)
    ax.text(x, y, label, ha="center", va="center", fontsize=fontsize, fontweight="bold", color="white", zorder=4)
    if sublabel:
        ax.text(x, y - size - 0.025, sublabel, ha="center", va="top", fontsize=6.5, color="#333", zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, label="", color="#555", style="-", lw=1.2, fontsize=6, dashed=False):
    ls = "--" if dashed else "-"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, ls=ls, shrinkA=8, shrinkB=8), zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2 + 0.02
        ax.text(mx, my, label, ha="center", va="bottom", fontsize=fontsize, color=color, style="italic", zorder=5)

# ============================================================
# LAYER 1: Curated Assertions
# ============================================================
ax1 = axes[0]
ax1.set_xlim(0, 1); ax1.set_ylim(0, 1)
ax1.set_aspect("equal")
ax1.axis("off")

# Background
rect = FancyBboxPatch((0.01, 0.02), 0.98, 0.94, boxstyle="round,pad=0.01", 
                       facecolor="#EDE7F6", edgecolor="#B39DDB", lw=1.5, zorder=0)
ax1.add_patch(rect)
ax1.text(0.03, 0.95, "Layer 1: Curated Assertions", fontsize=11, fontweight="bold", va="top", color="#4527A0")

# Patterns (left)
draw_node(ax1, 0.15, 0.75, "P", C_PATTERN, sublabel="Solid")
draw_node(ax1, 0.15, 0.50, "P", C_PATTERN, sublabel="Lepidic")
draw_node(ax1, 0.15, 0.25, "P", C_PATTERN, sublabel="Acinar")
ax1.text(0.065, 0.75, "WHO-2021", fontsize=5.5, color=C_PROV, ha="center")
ax1.text(0.065, 0.50, "WHO-2021", fontsize=5.5, color=C_PROV, ha="center")
ax1.text(0.065, 0.25, "WHO-2021", fontsize=5.5, color=C_PROV, ha="center")

# Central: Adenocarcinoma
draw_node(ax1, 0.42, 0.50, "D", C_DIAG, size=0.055, sublabel="Adenocarcinoma")

# Genes (right-center)
draw_node(ax1, 0.62, 0.78, "G", C_GENE, sublabel="KRAS")
draw_node(ax1, 0.62, 0.50, "G", C_GENE, sublabel="EGFR")
draw_node(ax1, 0.62, 0.22, "G", C_GENE, sublabel="TP53")

# Treatments (far right)
draw_node(ax1, 0.85, 0.82, "T", C_TREAT, sublabel="Sotorasib")
draw_node(ax1, 0.85, 0.55, "T", C_TREAT, sublabel="Osimertinib")

# Arrows: patterns -> adenocarcinoma
draw_arrow(ax1, 0.20, 0.75, 0.37, 0.55, "subtypeOf", lw=1.0)
draw_arrow(ax1, 0.20, 0.50, 0.37, 0.50, "subtypeOf", lw=1.0)
draw_arrow(ax1, 0.20, 0.25, 0.37, 0.45, "subtypeOf", lw=1.0)

# Arrows: adenocarcinoma -> genes (mutatedIn)
draw_arrow(ax1, 0.47, 0.55, 0.57, 0.75, "mutatedIn", color="#555", lw=1.0)
draw_arrow(ax1, 0.47, 0.50, 0.57, 0.50, "mutatedIn", color="#555", lw=1.0)
draw_arrow(ax1, 0.47, 0.45, 0.57, 0.25, "mutatedIn", color="#555", lw=1.0)

# Arrows: patterns -> genes (associatedWithMutation, dashed)
draw_arrow(ax1, 0.20, 0.73, 0.57, 0.78, "associatedWithMutation", dashed=True, color="#999", lw=0.8)
draw_arrow(ax1, 0.20, 0.27, 0.57, 0.24, "associatedWithMutation", dashed=True, color="#999", lw=0.8)

# Arrows: genes -> treatments
draw_arrow(ax1, 0.67, 0.80, 0.80, 0.82, "treatedWith", color="#7B1FA2", lw=1.0)
ax1.text(0.90, 0.87, "OncoKB/FDA", fontsize=5, color=C_PROV, ha="center")
draw_arrow(ax1, 0.67, 0.52, 0.80, 0.55, "treatedWith", color="#7B1FA2", lw=1.0)
ax1.text(0.90, 0.60, "OncoKB/FDA", fontsize=5, color=C_PROV, ha="center")

# Provenance labels
ax1.text(0.67, 0.17, "TCGA/CIViC", fontsize=5, color=C_PROV)
ax1.text(0.67, 0.13, "COSMIC", fontsize=5, color=C_PROV)

# ============================================================
# LAYER 2: Dynamic Case Filtering — TCGA-55-7815
# ============================================================
ax2 = axes[1]
ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
ax2.set_aspect("equal")
ax2.axis("off")

rect2 = FancyBboxPatch((0.01, 0.02), 0.98, 0.94, boxstyle="round,pad=0.01",
                        facecolor="#E8F5E9", edgecolor="#81C784", lw=1.5, zorder=0)
ax2.add_patch(rect2)
ax2.text(0.03, 0.95, "Layer 2: Dynamic Case Filtering", fontsize=11, fontweight="bold", va="top", color="#2E7D32")

# Case node
draw_node(ax2, 0.12, 0.50, "C", C_CASE, size=0.065, fontsize=9)
ax2.text(0.12, 0.35, "Case\nTCGA-55-\n7815", ha="center", va="top", fontsize=7, fontweight="bold", color="#1565C0")

# Active patterns
draw_node(ax2, 0.32, 0.72, "P", C_PATTERN, sublabel="Acinar\n(81.8%)")
draw_node(ax2, 0.32, 0.28, "P", C_PATTERN, sublabel="Solid\n(14.1%)")

# Active genes
draw_node(ax2, 0.52, 0.72, "G", C_GENE, sublabel="TP53")
draw_node(ax2, 0.52, 0.28, "G", C_GENE, sublabel="EGFR")

# Active treatment
draw_node(ax2, 0.72, 0.28, "T", C_TREAT, sublabel="Osimertinib")

# Faded/inactive nodes
draw_node(ax2, 0.72, 0.72, "G", C_FADED, sublabel="KRAS", alpha=0.4)
draw_node(ax2, 0.85, 0.72, "T", C_FADED, sublabel="Sotorasib", alpha=0.4)
draw_node(ax2, 0.85, 0.28, "P", C_FADED, sublabel="Lepidic", alpha=0.4)

# Arrows
draw_arrow(ax2, 0.18, 0.55, 0.27, 0.70, "", C_CASE, lw=1.5)
draw_arrow(ax2, 0.18, 0.45, 0.27, 0.30, "", C_CASE, lw=1.5)
draw_arrow(ax2, 0.37, 0.72, 0.47, 0.72, "", "#555", lw=1.2)
draw_arrow(ax2, 0.37, 0.30, 0.47, 0.30, "", "#555", lw=1.2)
draw_arrow(ax2, 0.57, 0.30, 0.67, 0.28, "treatedWith", "#7B1FA2", lw=1.0)

# ============================================================
# LAYER 3: Literature DeepSearch
# ============================================================
ax3 = axes[2]
ax3.set_xlim(0, 1); ax3.set_ylim(0, 1)
ax3.set_aspect("equal")
ax3.axis("off")

rect3 = FancyBboxPatch((0.01, 0.02), 0.98, 0.94, boxstyle="round,pad=0.01",
                        facecolor="#E3F2FD", edgecolor="#64B5F6", lw=1.5, zorder=0)
ax3.add_patch(rect3)
ax3.text(0.03, 0.95, "Layer 3: Literature DeepSearch", fontsize=11, fontweight="bold", va="top", color="#1565C0")

# Sources box
src_rect = FancyBboxPatch((0.03, 0.25), 0.12, 0.55, boxstyle="round,pad=0.01",
                           facecolor="white", edgecolor="#90A4AE", lw=1, zorder=1)
ax3.add_patch(src_rect)
ax3.text(0.09, 0.72, "PubMed", fontsize=7, ha="center", fontweight="bold", color="#D32F2F")
ax3.text(0.09, 0.55, "Semantic\nScholar", fontsize=6.5, ha="center", fontweight="bold", color="#1976D2")
ax3.text(0.09, 0.38, "arXiv", fontsize=7, ha="center", fontweight="bold", color="#E65100")

# LLM Extraction box
llm_rect = FancyBboxPatch((0.19, 0.30), 0.14, 0.45, boxstyle="round,pad=0.01",
                           facecolor="#FFF9C4", edgecolor="#FBC02D", lw=1, zorder=1)
ax3.add_patch(llm_rect)
ax3.text(0.26, 0.65, "LLM\nExtraction", fontsize=8, ha="center", fontweight="bold", color="#F57F17")

# Triples box
tri_rect = FancyBboxPatch((0.37, 0.25), 0.22, 0.55, boxstyle="round,pad=0.01",
                           facecolor="white", edgecolor="#90A4AE", lw=1, zorder=1)
ax3.add_patch(tri_rect)
ax3.text(0.48, 0.73, "new relation triples", fontsize=7, ha="center", fontweight="bold", color="#333")
ax3.text(0.48, 0.60, "(KRAS, treatedWith, Adagrasib)", fontsize=5.5, ha="center", color="#555", family="monospace")
ax3.text(0.48, 0.50, "(Acinar, associatedWith\n  Mutation, TP53)", fontsize=5.5, ha="center", color="#555", family="monospace")
ax3.text(0.48, 0.35, "(Lepidic, associatedWith\n  Mutation, EGFR)", fontsize=5.5, ha="center", color="#555", family="monospace")

# Entity Linking box
el_rect = FancyBboxPatch((0.63, 0.30), 0.14, 0.45, boxstyle="round,pad=0.01",
                          facecolor="#E8F5E9", edgecolor="#66BB6A", lw=1, zorder=1)
ax3.add_patch(el_rect)
ax3.text(0.70, 0.65, "Entity Linking\n+ Validation", fontsize=7, ha="center", fontweight="bold", color="#2E7D32")

# Result graph nodes
draw_node(ax3, 0.83, 0.80, "P", C_PATTERN, size=0.03, fontsize=6, sublabel="Solid")
draw_node(ax3, 0.83, 0.55, "D", C_DIAG, size=0.03, fontsize=6, sublabel="Adenoca.")
draw_node(ax3, 0.93, 0.75, "G", C_GENE, size=0.03, fontsize=6, sublabel="KRAS")
draw_node(ax3, 0.93, 0.55, "G", C_GENE, size=0.03, fontsize=6, sublabel="EGFR")
draw_node(ax3, 0.93, 0.35, "G", C_GENE, size=0.03, fontsize=6, sublabel="TP53")
draw_node(ax3, 0.83, 0.30, "P", C_PATTERN, size=0.03, fontsize=6, sublabel="Acinar")

# Arrows between layers
draw_arrow(ax3, 0.15, 0.50, 0.19, 0.50, "", "#555", lw=1.5)
draw_arrow(ax3, 0.33, 0.50, 0.37, 0.50, "", "#555", lw=1.5)
draw_arrow(ax3, 0.59, 0.50, 0.63, 0.50, "", "#555", lw=1.5)

# Dashed arrows in result graph
draw_arrow(ax3, 0.86, 0.78, 0.90, 0.75, "", "#999", dashed=True, lw=0.8)
draw_arrow(ax3, 0.86, 0.32, 0.90, 0.37, "", "#999", dashed=True, lw=0.8)
draw_arrow(ax3, 0.86, 0.55, 0.90, 0.55, "", "#999", dashed=True, lw=0.8)

ax3.text(0.95, 0.82, "PMID:39284611", fontsize=4.5, color="#1976D2", ha="center")

# Save
out = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_8 ver 27 mar 2026\chapters\figures\kg_three_layer_architecture.png"
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved to {out}")
plt.close()
