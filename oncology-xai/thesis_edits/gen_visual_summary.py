"""Generate visual summary diagram for Chapter 1: RQs -> Chapters -> Publications."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\thesis_visual_summary.png"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=7, bold=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.08", facecolor=color,
        edgecolor="#374151", linewidth=0.7, zorder=3)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4,
            linespacing=1.25)


def arrow(ax, x1, y1, x2, y2, color="#94a3b8", lw=1.0):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.1,head_length=0.06",
                                color=color, lw=lw))


fig, ax = plt.subplots(figsize=(14, 8.5))
ax.set_xlim(0, 14)
ax.set_ylim(0, 10.5)
ax.axis("off")

# ─── Title ───
ax.text(7, 10.2, "Visual Summary of the Thesis",
        ha="center", fontsize=14, fontweight="bold", color="#1e293b")
ax.text(7, 9.85, "Research Questions, Chapters, Contributions, and Publications",
        ha="center", fontsize=8, color="#64748b", style="italic")

# ─── Column headers ───
ax.text(1.5, 9.4, "Research Questions", ha="center", fontsize=9,
        fontweight="bold", color="#1e40af")
ax.text(6.0, 9.4, "Chapters", ha="center", fontsize=9,
        fontweight="bold", color="#166534")
ax.text(10.0, 9.4, "Contributions", ha="center", fontsize=9,
        fontweight="bold", color="#7c2d12")
ax.text(12.8, 9.4, "Publications", ha="center", fontsize=9,
        fontweight="bold", color="#7c3aed")

# ─── Research Questions (left column) ───
rqs = [
    ("RQ1", "Fuzzy representation\nlearning", "#3b82f6"),
    ("RQ2", "Pattern-informed\nMIL", "#2563eb"),
    ("RQ3", "Fuzzy Choquet\naggregation", "#1d4ed8"),
    ("RQ4", "Six-level\ninterpretability", "#7c3aed"),
    ("RQ5", "Data scarcity\nutility", "#6d28d9"),
    ("RQ6", "Ontology-grounded\nexplanations", "#0891b2"),
    ("RQ7", "KG enrichment", "#0e7490"),
]

rq_positions = []
y_start = 8.8
for i, (rq_id, rq_text, color) in enumerate(rqs):
    y = y_start - i * 1.15
    box(ax, 0.1, y, 2.8, 0.85, f"{rq_id}\n{rq_text}", color, fontsize=6.5, bold=True)
    rq_positions.append((0.1, y, 2.8, 0.85))

# ─── Chapters (center column) ───
chapters = [
    ("Ch. 2\nBackground", "Fuzzy sets, MIL,\nChoquet, CTransPath", "#16a34a", 8.8),
    ("Ch. 3\nUse Case", "LUAD, 6 patterns,\n6 genes, TCGA", "#15803d", 7.65),
    ("Ch. 4\nMethodology", "FuzzyArcLoss V2,\nABMIL, Choquet,\n6-level framework", "#166534", 6.25),
    ("Ch. 5\nImplementation", "LCHAI v2.0, Analysis tab,\nfuzzy labels, KG,\nactive learning", "#14532d", 4.6),
    ("Ch. 6\nEvaluation", "18-loss benchmark,\n6-gene AUROC,\nablation, Shapley", "#0f766e", 3.2),
    ("Ch. 7\nDiscussion", "RQ answers, limitations,\nfour-level fuzzy\ncoherence, future work", "#115e59", 1.8),
]

ch_positions = []
for title, desc, color, y in chapters:
    box(ax, 4.2, y, 3.6, 1.05, f"{title}\n{desc}", color, fontsize=6, bold=False)
    ch_positions.append((4.2, y, 3.6, 1.05))

# ─── Contributions (right-center column) ───
contribs = [
    ("C1: FuzzyArcLoss V2\n(Artefact 1)", "#dc2626", 8.4),
    ("C2: Pattern-Informed\nABMIL (Artefact 2)", "#ea580c", 7.25),
    ("C3: Fuzzy Choquet\nMIL (Artefact 3)", "#d97706", 6.1),
    ("C4: Comprehensive\nBenchmark", "#ca8a04", 4.95),
    ("C5: Ontology\nExplanation Layer", "#65a30d", 3.8),
    ("C6: LCHAI v2.0\nPrototype", "#0d9488", 2.65),
]

for text, color, y in contribs:
    box(ax, 8.6, y, 2.6, 0.85, text, color, fontsize=6.5, bold=True)

# ─── Publications (far right column) ───
pubs = [
    ("Lima et al. (2025)\nESWA\nFuzzyArcLoss", "#7c3aed", 8.0),
    ("Lima et al. (2020)\nIEEE ICEDEG\nExplainable fuzzy DL\nfor skin cancer", "#6d28d9", 5.8),
    ("Lima et al. (2025)\nIEEE ICEDEG\nOntology retrieval\nwith angular loss", "#5b21b6", 3.4),
]

for text, color, y in pubs:
    box(ax, 11.8, y, 2.0, 1.2, text, color, fontsize=5.5, bold=True)

# ─── Arrows: RQs -> Chapters ───
# RQ1 -> Ch4
arrow(ax, 2.9, rq_positions[0][1]+0.42, 4.2, ch_positions[2][1]+0.52)
# RQ2 -> Ch4
arrow(ax, 2.9, rq_positions[1][1]+0.42, 4.2, ch_positions[2][1]+0.52)
# RQ3 -> Ch4
arrow(ax, 2.9, rq_positions[2][1]+0.42, 4.2, ch_positions[2][1]+0.52)
# RQ4 -> Ch5, Ch6
arrow(ax, 2.9, rq_positions[3][1]+0.42, 4.2, ch_positions[3][1]+0.52)
arrow(ax, 2.9, rq_positions[3][1]+0.30, 4.2, ch_positions[4][1]+0.52, "#a78bfa")
# RQ5 -> Ch6, Ch7
arrow(ax, 2.9, rq_positions[4][1]+0.42, 4.2, ch_positions[4][1]+0.52)
arrow(ax, 2.9, rq_positions[4][1]+0.30, 4.2, ch_positions[5][1]+0.52, "#a78bfa")
# RQ6 -> Ch4, Ch5
arrow(ax, 2.9, rq_positions[5][1]+0.55, 4.2, ch_positions[2][1]+0.30)
arrow(ax, 2.9, rq_positions[5][1]+0.42, 4.2, ch_positions[3][1]+0.52)
# RQ7 -> Ch5, Ch6
arrow(ax, 2.9, rq_positions[6][1]+0.55, 4.2, ch_positions[3][1]+0.30)
arrow(ax, 2.9, rq_positions[6][1]+0.42, 4.2, ch_positions[4][1]+0.52, "#a78bfa")

# ─── Arrows: Chapters -> Contributions ───
arrow(ax, 7.8, ch_positions[2][1]+0.8, 8.6, contribs[0][2]+0.42, "#dc2626")
arrow(ax, 7.8, ch_positions[2][1]+0.5, 8.6, contribs[1][2]+0.42, "#ea580c")
arrow(ax, 7.8, ch_positions[2][1]+0.3, 8.6, contribs[2][2]+0.42, "#d97706")
arrow(ax, 7.8, ch_positions[4][1]+0.5, 8.6, contribs[3][2]+0.42, "#ca8a04")
arrow(ax, 7.8, ch_positions[3][1]+0.3, 8.6, contribs[4][2]+0.42, "#65a30d")
arrow(ax, 7.8, ch_positions[3][1]+0.5, 8.6, contribs[5][2]+0.42, "#0d9488")

# ─── Arrows: Contributions -> Publications ───
arrow(ax, 11.2, contribs[0][2]+0.42, 11.8, pubs[0][2]+0.6, "#7c3aed")
arrow(ax, 11.2, contribs[1][2]+0.42, 11.8, pubs[1][2]+0.6, "#6d28d9")
arrow(ax, 11.2, contribs[2][2]+0.42, 11.8, pubs[1][2]+0.6, "#6d28d9")
arrow(ax, 11.2, contribs[4][2]+0.42, 11.8, pubs[2][2]+0.6, "#5b21b6")

# ─── Bottom: Thesis title ───
ax.text(7, 0.6, "LCHAI v2.0: Lung Cancer Histologic Analysis with AI",
        ha="center", fontsize=10, fontweight="bold", color="#1e293b",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f9ff",
                  edgecolor="#3b82f6", linewidth=1))
ax.text(7, 0.15, "Servio F. Lima Reina — University of Fribourg, Switzerland",
        ha="center", fontsize=7, color="#64748b")

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
