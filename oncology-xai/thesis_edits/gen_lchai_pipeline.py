"""Regenerate LCHAI v2.0 Output and Explanation Layers diagram."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\lchai_v12_pipeline_new.png"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=11, bold=False, alpha=1.0):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.08", facecolor=color,
        edgecolor="#374151", linewidth=0.8, zorder=3, alpha=alpha)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4,
            linespacing=1.15)


def arrow(ax, x1, y1, x2, y2, color="#94a3b8", lw=1.2, style="-"):
    ls = "--" if style == "dashed" else "-"
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.10,head_length=0.06",
                                color=color, lw=lw, linestyle=ls))


fig, ax = plt.subplots(figsize=(22, 16))
ax.set_xlim(0, 22)
ax.set_ylim(0, 16)
ax.axis("off")

# ══════════ TITLE ══════════
ax.text(11, 15.6, "LCHAI v2.0 — Output and Explanation Layers",
        ha="center", fontsize=18, fontweight="bold", color="#1e293b")
ax.text(11, 15.25, "(upstream data flow: see Figure artifact_pipeline)",
        ha="center", fontsize=10, color="#64748b", style="italic")

# ══════════ STAGE 4 — ONTOLOGY (top) ══════════
box(ax, 3.5, 14.0, 15.0, 1.0,
    "Stage 4 — Ontology Explanation Layer (RQ6, RQ7)",
    "#7c3aed", fontsize=13, bold=True)

# Stage 4 sub-boxes
box(ax, 3.7, 12.6, 3.2, 1.0,
    "DeepSearch\nPubMed · Semantic\nScholar · arXiv",
    "#a78bfa", fontsize=9)
box(ax, 7.2, 12.6, 3.5, 1.0,
    "Knowledge Graph\nNCIt + MONDO + SO\ncurated + case filter",
    "#8b5cf6", fontsize=9)
box(ax, 11.0, 12.6, 3.2, 1.0,
    "SPARQL Query\npattern → gene\n→ treatment",
    "#7c3aed", fontsize=9)
box(ax, 14.5, 12.6, 3.8, 1.0,
    "LLM Explanation Agent\nclinical narrative +\nfuzzy label injection",
    "#6d28d9", fontsize=9)

arrow(ax, 6.9, 13.1, 7.2, 13.1, "#a78bfa")
arrow(ax, 10.7, 13.1, 11.0, 13.1, "#8b5cf6")
arrow(ax, 14.2, 13.1, 14.5, 13.1, "#7c3aed")
arrow(ax, 5.3, 12.6, 5.3, 12.0, "#a78bfa", style="dashed")

# ══════════ CONFIDENCE CALIBRATION ══════════
box(ax, 5.5, 11.2, 4.5, 0.8,
    "Confidence Calibration\nConclusive (AUROC ≥ 0.70) / Inconclusive",
    "#059669", fontsize=9, bold=True)

# ══════════ STAGE 3 — INTERPRETABILITY (center) ══════════
box(ax, 5.5, 10.0, 4.5, 0.8,
    "Stage 3 — Six-Level Interpretability",
    "#d97706", fontsize=12, bold=True)

# 6 levels
levels = [
    ("Level 6: Fuzzy Linguistic Labels\n(anti-hallucination → LLM)", "#f59e0b"),
    ("Level 5: Per-Slide Ablation\n(Combined vs Emb-only vs Pat-only)", "#d97706"),
    ("Level 4: Choquet Shapley Values\n+ Interaction Indices (FC-MIL)", "#b45309"),
    ("Level 3: SHAP Decomposition\nemb dims vs. pattern dims", "#92400e"),
    ("Level 2: Spatial Attention Map\n(WSI heatmap overlay)", "#78350f"),
    ("Level 1: Pattern Overlay\n(tile-level colour map)", "#451a03"),
]
lx, lw, lh = 5.5, 4.5, 0.75
for i, (txt, col) in enumerate(levels):
    ly = 9.0 - i * 0.9
    box(ax, lx, ly, lw, lh, txt, col, fontsize=9)

# ══════════ LEFT — INPUTS FROM ARTIFACTS ══════════
box(ax, 0.3, 9.5, 3.8, 0.9,
    "From Artifact Pipeline\n(Figure artifact_pipeline)",
    "#e5e7eb", textcolor="#374151", fontsize=9)
box(ax, 0.3, 8.2, 3.8, 0.9,
    "FC-MIL Output\nMutation probs + Shapley values",
    "#0d9488", fontsize=9, bold=True)
box(ax, 0.3, 6.9, 3.8, 0.9,
    "PI-ABMIL Output\nMutation probs + attention weights",
    "#ea580c", fontsize=9, bold=True)

arrow(ax, 4.1, 8.65, lx, 6.55, "#0d9488")
arrow(ax, 4.1, 7.35, lx, 5.65, "#ea580c")
arrow(ax, 4.1, 7.35, lx, 4.75, "#ea580c")

# ══════════ RIGHT — CLINICAL OUTPUT ══════════
box(ax, 14.5, 10.5, 4.5, 0.8,
    "Clinical Output", "#dc2626", fontsize=12, bold=True)

box(ax, 14.5, 9.2, 4.5, 0.9,
    "Ontology-Grounded\nCase Explanation\n+ PubMed citations [1],[2]...",
    "#7c3aed", fontsize=9, bold=True)
box(ax, 14.5, 7.9, 4.5, 0.9,
    "Mutation Report\n(confidence-labelled)\nConclusive / Inconclusive",
    "#dc2626", fontsize=9, bold=True)
box(ax, 14.5, 6.6, 4.5, 0.9,
    "Attention + Pattern\nVisualisation\n+ interactive hover",
    "#ea580c", fontsize=9, bold=True)
box(ax, 14.5, 5.3, 4.5, 0.9,
    "Fuzzy Labels in\nLLM Explanation\n(anti-hallucination)",
    "#f59e0b", textcolor="#1e293b", fontsize=9, bold=True)

# Arrows from interpretability to clinical output
arrow(ax, lx + lw, 9.35, 14.5, 9.65, "#7c3aed")
arrow(ax, lx + lw, 7.25, 14.5, 8.35, "#dc2626")
arrow(ax, lx + lw, 5.45, 14.5, 7.05, "#ea580c")
arrow(ax, lx + lw, 9.35, 14.5, 5.75, "#f59e0b")

# Arrow from Stage 4 to clinical output
arrow(ax, 16.7, 12.6, 16.7, 10.2, "#7c3aed")

# Arrow from confidence to output
arrow(ax, 10.0, 11.6, 14.5, 8.35, "#059669")

# ══════════ BOTTOM NOTE ══════════
ax.text(11, 3.2,
    "Fuzzy logic operates at four levels:\n"
    "(1) Training — FuzzyArcLoss V2 · (2) Representation — soft probability vectors\n"
    "(3) Aggregation — Choquet integral · (4) Interpretation — fuzzy linguistic labels",
    ha="center", fontsize=11, color="#475569",
    bbox=dict(boxstyle="round,pad=0.4", facecolor="#f8fafc",
              edgecolor="#94a3b8", linewidth=1.0),
    linespacing=1.4)

fig.tight_layout()
fig.savefig(OUT, dpi=250, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
