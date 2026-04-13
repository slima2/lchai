"""Regenerate LCHAI v2.0 Output and Explanation Layers diagram — v2 with larger fonts, curved arrows."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\lchai_v12_pipeline_new.png"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=12, bold=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.10", facecolor=color,
        edgecolor="#374151", linewidth=0.8, zorder=3)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4,
            linespacing=1.15)


def curved_arrow(ax, x1, y1, x2, y2, color="#94a3b8", lw=1.3, rad=0.2, dashed=False):
    style = "Simple,tail_width=0.4,head_width=5,head_length=4"
    ls = "--" if dashed else "-"
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        connectionstyle=f"arc3,rad={rad}",
        arrowstyle="->", color=color, lw=lw, linestyle=ls, zorder=2,
        mutation_scale=12)
    ax.add_patch(arrow)


def straight_arrow(ax, x1, y1, x2, y2, color="#94a3b8", lw=1.3, dashed=False):
    ls = "--" if dashed else "-"
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="->", color=color, lw=lw, linestyle=ls, zorder=2,
        mutation_scale=12)
    ax.add_patch(arrow)


fig, ax = plt.subplots(figsize=(26, 19))
ax.set_xlim(0, 26)
ax.set_ylim(0, 19)
ax.axis("off")

# ══════════ TITLE ══════════
ax.text(13, 18.5, "LCHAI v2.0 — Output and Explanation Layers",
        ha="center", fontsize=20, fontweight="bold", color="#1e293b")
ax.text(13, 18.1, "(upstream data flow: see Figure artifact_pipeline)",
        ha="center", fontsize=12, color="#64748b", style="italic")

# ══════════ STAGE 4 — ONTOLOGY (top) ══════════
box(ax, 3.5, 16.5, 19.0, 1.1,
    "Stage 4 — Ontology Explanation Layer (RQ6, RQ7)",
    "#7c3aed", fontsize=15, bold=True)

# Stage 4 sub-boxes — wider with bigger font
s4y = 14.9
box(ax, 3.7, s4y, 3.8, 1.1,
    "DeepSearch\nPubMed · Semantic\nScholar · arXiv", "#a78bfa", fontsize=11)
box(ax, 8.0, s4y, 4.0, 1.1,
    "Knowledge Graph\nNCIt + MONDO + SO\ncurated + case filter", "#8b5cf6", fontsize=11)
box(ax, 12.5, s4y, 3.8, 1.1,
    "SPARQL Query\npattern → gene\n→ treatment", "#7c3aed", fontsize=11)
box(ax, 16.8, s4y, 4.5, 1.1,
    "LLM Explanation Agent\nclinical narrative +\nfuzzy label injection", "#6d28d9", fontsize=11)

straight_arrow(ax, 7.5, s4y+0.55, 8.0, s4y+0.55, "#d8b4fe")
straight_arrow(ax, 12.0, s4y+0.55, 12.5, s4y+0.55, "#c4b5fd")
straight_arrow(ax, 16.3, s4y+0.55, 16.8, s4y+0.55, "#a78bfa")
curved_arrow(ax, 5.6, s4y, 5.6, 14.3, "#a78bfa", dashed=True, rad=0.0)

# ══════════ CONFIDENCE CALIBRATION ══════════
box(ax, 6.0, 13.2, 5.5, 0.9,
    "Confidence Calibration\nConclusive (AUROC ≥ 0.70) / Inconclusive",
    "#059669", fontsize=12, bold=True)

# ══════════ STAGE 3 — INTERPRETABILITY ══════════
box(ax, 6.0, 11.9, 5.5, 0.9,
    "Stage 3 — Six-Level Interpretability",
    "#d97706", fontsize=14, bold=True)

# 6 levels — larger boxes and font
levels = [
    ("Level 6: Fuzzy Linguistic Labels\n(anti-hallucination → LLM)", "#f59e0b"),
    ("Level 5: Per-Slide Ablation\n(Combined vs Emb-only vs Pat-only)", "#d97706"),
    ("Level 4: Choquet Shapley Values\n+ Interaction Indices (FC-MIL)", "#b45309"),
    ("Level 3: SHAP Decomposition\nemb dims vs. pattern dims", "#92400e"),
    ("Level 2: Spatial Attention Map\n(WSI heatmap overlay)", "#78350f"),
    ("Level 1: Pattern Overlay\n(tile-level colour map)", "#451a03"),
]
lx, lw, lh = 6.0, 5.5, 0.85
level_ys = []
for i, (txt, col) in enumerate(levels):
    ly = 10.8 - i * 1.05
    box(ax, lx, ly, lw, lh, txt, col, fontsize=12)
    level_ys.append(ly)

# ══════════ LEFT — INPUTS ══════════
box(ax, 0.3, 11.5, 4.2, 1.0,
    "From Artifact Pipeline\n(Figure artifact_pipeline)",
    "#e5e7eb", textcolor="#374151", fontsize=12)
box(ax, 0.3, 9.8, 4.2, 1.0,
    "FC-MIL Output\nMutation probs +\nShapley values",
    "#0d9488", fontsize=12, bold=True)
box(ax, 0.3, 8.1, 4.2, 1.0,
    "PI-ABMIL Output\nMutation probs +\nattention weights",
    "#ea580c", fontsize=12, bold=True)

# Arrows from left inputs to levels — curved to avoid crossing
curved_arrow(ax, 4.5, 10.3, lx, level_ys[2]+lh/2, "#0d9488", rad=-0.3)
curved_arrow(ax, 4.5, 8.6, lx, level_ys[3]+lh/2, "#ea580c", rad=-0.2)
curved_arrow(ax, 4.5, 8.3, lx, level_ys[4]+lh/2, "#ea580c", rad=-0.3)
curved_arrow(ax, 4.5, 8.9, lx, level_ys[5]+lh/2, "#ea580c", rad=-0.4)

# ══════════ RIGHT — CLINICAL OUTPUT ══════════
cx, cw = 16.8, 5.0
box(ax, cx, 12.5, cw, 0.9,
    "Clinical Output", "#dc2626", fontsize=14, bold=True)

box(ax, cx, 11.0, cw, 1.0,
    "Ontology-Grounded\nCase Explanation\n+ PubMed citations [1],[2]...",
    "#7c3aed", fontsize=12, bold=True)
box(ax, cx, 9.5, cw, 1.0,
    "Mutation Report\n(confidence-labelled)\nConclusive / Inconclusive",
    "#dc2626", fontsize=12, bold=True)
box(ax, cx, 8.0, cw, 1.0,
    "Attention + Pattern\nVisualisation\n+ interactive hover",
    "#ea580c", fontsize=12, bold=True)
box(ax, cx, 6.5, cw, 1.0,
    "Fuzzy Labels in\nLLM Explanation\n(anti-hallucination)",
    "#f59e0b", textcolor="#1e293b", fontsize=12, bold=True)

# Arrows from interpretability to clinical output — curved
curved_arrow(ax, lx+lw, level_ys[0]+lh/2, cx, 11.5, "#7c3aed", rad=0.15)
curved_arrow(ax, lx+lw, level_ys[3]+lh/2, cx, 10.0, "#dc2626", rad=0.2)
curved_arrow(ax, lx+lw, level_ys[4]+lh/2, cx, 8.5, "#ea580c", rad=0.2)
curved_arrow(ax, lx+lw, level_ys[0]+lh/2, cx, 7.0, "#f59e0b", rad=0.35)

# Arrow from Stage 4 to ontology output
straight_arrow(ax, 19.3, s4y, 19.3, 12.1, "#7c3aed")

# Arrow from confidence to mutation report
curved_arrow(ax, 11.5, 13.2, cx, 10.0, "#059669", rad=0.2)

# ══════════ BOTTOM NOTE ══════════
ax.text(13, 3.5,
    "Fuzzy logic operates at four levels:\n"
    "(1) Training — FuzzyArcLoss V2  ·  (2) Representation — soft probability vectors\n"
    "(3) Aggregation — Choquet integral  ·  (4) Interpretation — fuzzy linguistic labels",
    ha="center", fontsize=13, color="#475569",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8fafc",
              edgecolor="#94a3b8", linewidth=1.0),
    linespacing=1.4)

fig.tight_layout()
fig.savefig(OUT, dpi=250, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
