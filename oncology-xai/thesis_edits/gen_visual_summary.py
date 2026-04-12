"""Generate visual summary diagram for Chapter 1."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\thesis_visual_summary.png"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=13, bold=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.08", facecolor=color,
        edgecolor="#374151", linewidth=0.8, zorder=3)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4,
            linespacing=1.15)


def arrow(ax, x1, y1, x2, y2, color="#94a3b8", lw=1.2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.12,head_length=0.07",
                                color=color, lw=lw))


fig, ax = plt.subplots(figsize=(22, 16))
ax.set_xlim(0, 22)
ax.set_ylim(0, 16)
ax.axis("off")

# ─── Title ───
ax.text(11, 15.7, "Visual Summary of the Thesis", ha="center",
        fontsize=22, fontweight="bold", color="#1e293b")

# ─── Hypothesis (white box, blue border, verdict inside) ───
hyp = mpatches.FancyBboxPatch((1.5, 14.2), 19.0, 1.3, boxstyle="round,pad=0.12",
                               facecolor="#f8fafc", edgecolor="#1e40af", linewidth=2.5, zorder=3)
ax.add_patch(hyp)
ax.text(11, 15.05, "H: Structured domain knowledge — histological growth patterns encoded through",
        ha="center", fontsize=12, color="#1e293b", fontweight="bold", zorder=4)
ax.text(11, 14.7, "fuzzy set theory — can achieve (a) competitive performance (<700 slides)",
        ha="center", fontsize=12, color="#1e293b", fontweight="bold", zorder=4)
ax.text(11, 14.35, "and (b) multi-level, clinically verifiable explanations.  "
        "Verdict: partially supported (Finding 2)",
        ha="center", fontsize=12, color="#1e293b", zorder=4)
ax.text(18.2, 14.35, "partially supported (Finding 2)",
        ha="center", fontsize=12, color="#dc2626", fontweight="bold", zorder=5)

# ─── Column headers ───
hdr_y = 13.5
ax.text(2.3, hdr_y, "Research Questions", ha="center", fontsize=15, fontweight="bold", color="#1e40af")
ax.text(9.0, hdr_y, "Chapters", ha="center", fontsize=15, fontweight="bold", color="#166534")
ax.text(15.3, hdr_y, "Contributions", ha="center", fontsize=15, fontweight="bold", color="#7c2d12")
ax.text(20.0, hdr_y, "Publications", ha="center", fontsize=15, fontweight="bold", color="#7c3aed")

# ─── RQs ───
rqs = [
    ("RQ1\nFuzzy repr. learning", "#3b82f6"),
    ("RQ2\nPattern-informed MIL", "#2563eb"),
    ("RQ3\nFuzzy Choquet aggr.", "#1d4ed8"),
    ("RQ4\nSix-level interpret.", "#7c3aed"),
    ("RQ5\nData scarcity utility", "#6d28d9"),
    ("RQ6\nOntology explanations", "#0891b2"),
    ("RQ7\nKG enrichment", "#0e7490"),
]
rq_w, rq_h = 4.0, 1.15
rq_x = 0.3
rq_ys = []
for i, (txt, col) in enumerate(rqs):
    y = 12.8 - i * 1.55
    box(ax, rq_x, y, rq_w, rq_h, txt, col, fontsize=13, bold=True)
    rq_ys.append(y)

# ─── Chapters ───
chs = [
    ("Ch. 2 — Background\nFuzzy sets, MIL, Choquet, CTransPath", "#16a34a", 12.8),
    ("Ch. 3 — Use Case\nLUAD, 6 patterns, 6 genes, TCGA", "#15803d", 11.25),
    ("Ch. 4 — Methodology\nFuzzyArcLoss V2, ABMIL, Choquet, 6-level", "#166534", 9.35),
    ("Ch. 5 — Implementation\nLCHAI v2.0, fuzzy labels, KG, active learning", "#14532d", 7.15),
    ("Ch. 6 — Evaluation\n18-loss benchmark, 6-gene AUROC, ablation", "#0f766e", 5.25),
    ("Ch. 7 — Discussion\nRQ answers, limitations, fuzzy coherence", "#115e59", 3.35),
]
ch_w, ch_h = 5.5, 1.35
ch_x = 6.2
ch_ys = []
for txt, col, y in chs:
    box(ax, ch_x, y, ch_w, ch_h, txt, col, fontsize=12)
    ch_ys.append(y)

# ─── Contributions ───
cs = [
    ("C1: FuzzyArcLoss V2\n(Artefact 1)", "#dc2626", 12.4),
    ("C2: Pattern-Informed\nABMIL (Artefact 2)", "#ea580c", 10.85),
    ("C3: Fuzzy Choquet\nMIL (Artefact 3)", "#d97706", 9.3),
    ("C4: Comprehensive\nBenchmark", "#ca8a04", 7.75),
    ("C5: Ontology\nExplanation Layer", "#65a30d", 6.2),
    ("C6: LCHAI v2.0\nPrototype", "#0d9488", 4.65),
]
c_w, c_h = 3.5, 1.15
c_x = 13.5
c_ys = []
for txt, col, y in cs:
    box(ax, c_x, y, c_w, c_h, txt, col, fontsize=13, bold=True)
    c_ys.append(y)

# ─── Publications ───
ps = [
    ("Lima et al.\n(2025) ESWA\nFuzzyArcLoss", "#7c3aed", 11.8),
    ("Lima et al.\n(2020) IEEE\nExplainable\nfuzzy DL", "#6d28d9", 8.8),
    ("Lima et al.\n(2025) IEEE\nOntology\nretrieval", "#5b21b6", 5.7),
]
p_w, p_h = 2.8, 1.6
p_x = 18.6
p_ys = []
for txt, col, y in ps:
    box(ax, p_x, y, p_w, p_h, txt, col, fontsize=12, bold=True)
    p_ys.append(y)

# ─── Arrows: RQ -> Ch ───
rq_r = rq_x + rq_w
for i in range(3):
    arrow(ax, rq_r, rq_ys[i] + rq_h/2, ch_x, ch_ys[2] + ch_h/2)
arrow(ax, rq_r, rq_ys[3] + rq_h/2, ch_x, ch_ys[3] + ch_h/2)
arrow(ax, rq_r, rq_ys[3] + rq_h*0.3, ch_x, ch_ys[4] + ch_h/2, "#a78bfa")
arrow(ax, rq_r, rq_ys[4] + rq_h/2, ch_x, ch_ys[4] + ch_h/2)
arrow(ax, rq_r, rq_ys[4] + rq_h*0.3, ch_x, ch_ys[5] + ch_h/2, "#a78bfa")
arrow(ax, rq_r, rq_ys[5] + rq_h*0.7, ch_x, ch_ys[2] + ch_h*0.3)
arrow(ax, rq_r, rq_ys[5] + rq_h/2, ch_x, ch_ys[3] + ch_h/2)
arrow(ax, rq_r, rq_ys[6] + rq_h*0.7, ch_x, ch_ys[3] + ch_h*0.3)
arrow(ax, rq_r, rq_ys[6] + rq_h/2, ch_x, ch_ys[4] + ch_h/2, "#a78bfa")

# ─── Arrows: Ch -> Contributions ───
ch_r = ch_x + ch_w
arrow(ax, ch_r, ch_ys[2] + ch_h*0.8, c_x, c_ys[0] + c_h/2, "#dc2626")
arrow(ax, ch_r, ch_ys[2] + ch_h/2, c_x, c_ys[1] + c_h/2, "#ea580c")
arrow(ax, ch_r, ch_ys[2] + ch_h*0.2, c_x, c_ys[2] + c_h/2, "#d97706")
arrow(ax, ch_r, ch_ys[4] + ch_h/2, c_x, c_ys[3] + c_h/2, "#ca8a04")
arrow(ax, ch_r, ch_ys[3] + ch_h*0.3, c_x, c_ys[4] + c_h/2, "#65a30d")
arrow(ax, ch_r, ch_ys[3] + ch_h/2, c_x, c_ys[5] + c_h/2, "#0d9488")

# ─── Arrows: Contributions -> Publications ───
c_r = c_x + c_w
arrow(ax, c_r, c_ys[0] + c_h/2, p_x, p_ys[0] + p_h/2, "#7c3aed")
arrow(ax, c_r, c_ys[1] + c_h/2, p_x, p_ys[1] + p_h/2, "#6d28d9")
arrow(ax, c_r, c_ys[2] + c_h/2, p_x, p_ys[1] + p_h/2, "#6d28d9")
arrow(ax, c_r, c_ys[4] + c_h/2, p_x, p_ys[2] + p_h/2, "#5b21b6")

# ─── Bottom ───
ax.text(11, 1.8, "LCHAI v2.0: Lung Cancer Histologic Analysis with AI",
        ha="center", fontsize=16, fontweight="bold", color="#1e293b",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f9ff",
                  edgecolor="#3b82f6", linewidth=1.5))
ax.text(11, 1.1, "Servio F. Lima Reina — University of Fribourg, Switzerland",
        ha="center", fontsize=12, color="#64748b")

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
