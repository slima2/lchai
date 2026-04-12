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


fig, ax = plt.subplots(figsize=(18, 11))
ax.set_xlim(0, 18)
ax.set_ylim(0, 13)
ax.axis("off")

# ─── Title ───
ax.text(9, 12.7, "Visual Summary of the Thesis",
        ha="center", fontsize=18, fontweight="bold", color="#1e293b")
ax.text(9, 12.25, "Research Questions, Chapters, Contributions, and Publications",
        ha="center", fontsize=11, color="#64748b", style="italic")

# ─── Column headers ───
ax.text(2.0, 11.7, "Research Questions", ha="center", fontsize=12,
        fontweight="bold", color="#1e40af")
ax.text(7.5, 11.7, "Chapters", ha="center", fontsize=12,
        fontweight="bold", color="#166534")
ax.text(12.5, 11.7, "Contributions", ha="center", fontsize=12,
        fontweight="bold", color="#7c2d12")
ax.text(16.2, 11.7, "Publications", ha="center", fontsize=12,
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
y_start = 11.0
for i, (rq_id, rq_text, color) in enumerate(rqs):
    y = y_start - i * 1.4
    box(ax, 0.2, y, 3.5, 1.05, f"{rq_id}\n{rq_text}", color, fontsize=9, bold=True)
    rq_positions.append((0.2, y, 3.5, 1.05))

# ─── Chapters (center column) ───
chapters = [
    ("Ch. 2 — Background", "Fuzzy sets, MIL,\nChoquet, CTransPath", "#16a34a", 11.0),
    ("Ch. 3 — Use Case", "LUAD, 6 patterns,\n6 genes, TCGA", "#15803d", 9.6),
    ("Ch. 4 — Methodology", "FuzzyArcLoss V2, ABMIL,\nChoquet, 6-level framework", "#166534", 7.8),
    ("Ch. 5 — Implementation", "LCHAI v2.0, Analysis tab,\nfuzzy labels, KG, active learning", "#14532d", 5.8),
    ("Ch. 6 — Evaluation", "18-loss benchmark, 6-gene\nAUROC, ablation, Shapley", "#0f766e", 4.0),
    ("Ch. 7 — Discussion", "RQ answers, limitations,\nfour-level fuzzy coherence", "#115e59", 2.2),
]

ch_positions = []
for title, desc, color, y in chapters:
    box(ax, 5.2, y, 4.5, 1.3, f"{title}\n{desc}", color, fontsize=8.5)
    ch_positions.append((5.2, y, 4.5, 1.3))

# ─── Contributions (right-center column) ───
contribs = [
    ("C1: FuzzyArcLoss V2\n(Artefact 1)", "#dc2626", 10.5),
    ("C2: Pattern-Informed\nABMIL (Artefact 2)", "#ea580c", 9.1),
    ("C3: Fuzzy Choquet\nMIL (Artefact 3)", "#d97706", 7.7),
    ("C4: Comprehensive\nBenchmark", "#ca8a04", 6.3),
    ("C5: Ontology\nExplanation Layer", "#65a30d", 4.9),
    ("C6: LCHAI v2.0\nPrototype", "#0d9488", 3.5),
]

for text, color, y in contribs:
    box(ax, 10.8, y, 3.2, 1.05, text, color, fontsize=9, bold=True)

# ─── Publications (far right column) ───
pubs = [
    ("Lima et al. (2025)\nESWA\nFuzzyArcLoss", "#7c3aed", 10.0),
    ("Lima et al. (2020)\nIEEE ICEDEG\nExplainable fuzzy DL\nfor skin cancer", "#6d28d9", 7.2),
    ("Lima et al. (2025)\nIEEE ICEDEG\nOntology retrieval\nwith angular loss", "#5b21b6", 4.4),
]

for text, color, y in pubs:
    box(ax, 15.0, y, 2.7, 1.5, text, color, fontsize=8, bold=True)

# ─── Arrows: RQs -> Chapters ───
rq_r = 3.7  # right edge of RQ boxes
ch_l = 5.2  # left edge of ch boxes
for i in range(3):  # RQ1-3 -> Ch4
    arrow(ax, rq_r, rq_positions[i][1]+0.52, ch_l, ch_positions[2][1]+0.65)
# RQ4 -> Ch5, Ch6
arrow(ax, rq_r, rq_positions[3][1]+0.52, ch_l, ch_positions[3][1]+0.65)
arrow(ax, rq_r, rq_positions[3][1]+0.35, ch_l, ch_positions[4][1]+0.65, "#a78bfa")
# RQ5 -> Ch6, Ch7
arrow(ax, rq_r, rq_positions[4][1]+0.52, ch_l, ch_positions[4][1]+0.65)
arrow(ax, rq_r, rq_positions[4][1]+0.35, ch_l, ch_positions[5][1]+0.65, "#a78bfa")
# RQ6 -> Ch4, Ch5
arrow(ax, rq_r, rq_positions[5][1]+0.7, ch_l, ch_positions[2][1]+0.4)
arrow(ax, rq_r, rq_positions[5][1]+0.52, ch_l, ch_positions[3][1]+0.65)
# RQ7 -> Ch5, Ch6
arrow(ax, rq_r, rq_positions[6][1]+0.7, ch_l, ch_positions[3][1]+0.4)
arrow(ax, rq_r, rq_positions[6][1]+0.52, ch_l, ch_positions[4][1]+0.65, "#a78bfa")

# ─── Arrows: Chapters -> Contributions ───
ch_r = 9.7  # right edge of ch boxes
ct_l = 10.8  # left edge of contrib boxes
arrow(ax, ch_r, ch_positions[2][1]+1.0, ct_l, contribs[0][2]+0.52, "#dc2626")
arrow(ax, ch_r, ch_positions[2][1]+0.65, ct_l, contribs[1][2]+0.52, "#ea580c")
arrow(ax, ch_r, ch_positions[2][1]+0.3, ct_l, contribs[2][2]+0.52, "#d97706")
arrow(ax, ch_r, ch_positions[4][1]+0.65, ct_l, contribs[3][2]+0.52, "#ca8a04")
arrow(ax, ch_r, ch_positions[3][1]+0.4, ct_l, contribs[4][2]+0.52, "#65a30d")
arrow(ax, ch_r, ch_positions[3][1]+0.65, ct_l, contribs[5][2]+0.52, "#0d9488")

# ─── Arrows: Contributions -> Publications ───
ct_r = 14.0  # right edge of contrib boxes
pb_l = 15.0  # left edge of pub boxes
arrow(ax, ct_r, contribs[0][2]+0.52, pb_l, pubs[0][2]+0.75, "#7c3aed")
arrow(ax, ct_r, contribs[1][2]+0.52, pb_l, pubs[1][2]+0.75, "#6d28d9")
arrow(ax, ct_r, contribs[2][2]+0.52, pb_l, pubs[1][2]+0.75, "#6d28d9")
arrow(ax, ct_r, contribs[4][2]+0.52, pb_l, pubs[2][2]+0.75, "#5b21b6")

# ─── Bottom: Thesis title ───
ax.text(9, 0.8, "LCHAI v2.0: Lung Cancer Histologic Analysis with AI",
        ha="center", fontsize=13, fontweight="bold", color="#1e293b",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f9ff",
                  edgecolor="#3b82f6", linewidth=1))
ax.text(9, 0.25, "Servio F. Lima Reina — University of Fribourg, Switzerland",
        ha="center", fontsize=9, color="#64748b")

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
