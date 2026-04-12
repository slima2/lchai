"""Generate visual summary diagram for Chapter 1 — clean version."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

OUT = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures\thesis_visual_summary.png"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=13, bold=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.1", facecolor=color,
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


fig, ax = plt.subplots(figsize=(24, 18))
ax.set_xlim(0, 24)
ax.set_ylim(0, 20)
ax.axis("off")

# ══════════ TITLE ══════════
ax.text(12, 19.6, "Visual Summary of the Thesis", ha="center",
        fontsize=24, fontweight="bold", color="#1e293b")

# ══════════ HYPOTHESIS BOX (well above content) ══════════
hyp_box = mpatches.FancyBboxPatch((2, 18.0), 20.0, 1.3, boxstyle="round,pad=0.12",
                                   facecolor="#f8fafc", edgecolor="#1e40af",
                                   linewidth=2.5, zorder=3)
ax.add_patch(hyp_box)
ax.text(12, 18.9, "H: Structured domain knowledge — histological growth patterns encoded through "
        "fuzzy set theory —", ha="center", fontsize=13, color="#1e293b", fontweight="bold", zorder=4)
ax.text(12, 18.5, "can achieve (a) competitive performance under data scarcity (<700 slides) "
        "and (b) multi-level, clinically verifiable explanations.",
        ha="center", fontsize=13, color="#1e293b", zorder=4)
ax.text(12, 18.15, "Verdict: partially supported — pattern utility is gene-dependent (Finding 2)",
        ha="center", fontsize=13, color="#dc2626", fontweight="bold", zorder=4)

# ══════════ COLUMN HEADERS (with clear gap below hypothesis) ══════════
hdr_y = 17.0
ax.text(2.5, hdr_y, "Research Questions", ha="center", fontsize=16, fontweight="bold", color="#1e40af")
ax.text(9.5, hdr_y, "Chapters", ha="center", fontsize=16, fontweight="bold", color="#166534")
ax.text(16.0, hdr_y, "Contributions", ha="center", fontsize=16, fontweight="bold", color="#7c2d12")
ax.text(21.5, hdr_y, "Publications", ha="center", fontsize=16, fontweight="bold", color="#7c3aed")

# ══════════ RQs (left column) ══════════
rqs = [
    ("RQ1\nFuzzy repr. learning", "#3b82f6"),
    ("RQ2\nPattern-informed MIL", "#2563eb"),
    ("RQ3\nFuzzy Choquet aggr.", "#1d4ed8"),
    ("RQ4\nSix-level interpret.", "#7c3aed"),
    ("RQ5\nData scarcity utility", "#6d28d9"),
    ("RQ6\nOntology explanations", "#0891b2"),
    ("RQ7\nKG enrichment", "#0e7490"),
]
rq_w, rq_h = 4.2, 1.2
rq_x = 0.3
rq_ys = []
for i, (txt, col) in enumerate(rqs):
    y = 16.2 - i * 1.7
    box(ax, rq_x, y, rq_w, rq_h, txt, col, fontsize=14, bold=True)
    rq_ys.append(y)

# ══════════ CHAPTERS (center column) — well spaced ══════════
chs = [
    ("Ch. 2 — Background\nFuzzy sets, MIL, Choquet, CTransPath", "#16a34a"),
    ("Ch. 3 — Use Case\nLUAD, 6 patterns, 6 genes, TCGA", "#15803d"),
    ("Ch. 4 — Methodology\nFuzzyArcLoss V2, ABMIL, Choquet, 6-level", "#166534"),
    ("Ch. 5 — Implementation\nLCHAI v2.0, fuzzy labels, KG, active learning", "#14532d"),
    ("Ch. 6 — Evaluation\n18-loss benchmark, 6-gene AUROC, ablation", "#0f766e"),
    ("Ch. 7 — Discussion\nRQ answers, limitations, fuzzy coherence", "#115e59"),
]
ch_w, ch_h = 5.8, 1.4
ch_x = 6.5
ch_ys = [16.2, 14.3, 12.0, 9.5, 7.2, 5.0]
for (txt, col), y in zip(chs, ch_ys):
    box(ax, ch_x, y, ch_w, ch_h, txt, col, fontsize=13)

# ══════════ CONTRIBUTIONS (right-center) ══════════
cs = [
    ("C1: FuzzyArcLoss V2\n(Artefact 1)", "#dc2626"),
    ("C2: Pattern-Informed\nABMIL (Artefact 2)", "#ea580c"),
    ("C3: Fuzzy Choquet\nMIL (Artefact 3)", "#d97706"),
    ("C4: Comprehensive\nBenchmark", "#ca8a04"),
    ("C5: Ontology\nExplanation Layer", "#65a30d"),
    ("C6: LCHAI v2.0\nPrototype", "#0d9488"),
]
c_w, c_h = 3.8, 1.2
c_x = 14.0
c_ys = [15.7, 14.0, 12.3, 10.6, 8.9, 7.2]
for (txt, col), y in zip(cs, c_ys):
    box(ax, c_x, y, c_w, c_h, txt, col, fontsize=13, bold=True)

# ══════════ PUBLICATIONS (far right) — shifted right with gap ══════════
ps = [
    ("Lima et al.\n(2025) ESWA\nFuzzyArcLoss", "#7c3aed"),
    ("Lima et al.\n(2020) IEEE\nExplainable\nfuzzy DL", "#6d28d9"),
    ("Lima et al.\n(2025) IEEE\nOntology\nretrieval", "#5b21b6"),
]
p_w, p_h = 3.0, 1.7
p_x = 19.8
p_ys = [15.0, 11.5, 8.2]
for (txt, col), y in zip(ps, p_ys):
    box(ax, p_x, y, p_w, p_h, txt, col, fontsize=12, bold=True)

# ══════════ ARROWS: RQ -> Ch ══════════
rq_r = rq_x + rq_w
for i in range(3):
    arrow(ax, rq_r, rq_ys[i] + rq_h/2, ch_x, ch_ys[2] + ch_h/2)
arrow(ax, rq_r, rq_ys[3] + rq_h/2, ch_x, ch_ys[3] + ch_h/2)
arrow(ax, rq_r, rq_ys[3] + rq_h*0.25, ch_x, ch_ys[4] + ch_h/2, "#a78bfa")
arrow(ax, rq_r, rq_ys[4] + rq_h/2, ch_x, ch_ys[4] + ch_h/2)
arrow(ax, rq_r, rq_ys[4] + rq_h*0.25, ch_x, ch_ys[5] + ch_h/2, "#a78bfa")
arrow(ax, rq_r, rq_ys[5] + rq_h*0.75, ch_x, ch_ys[2] + ch_h*0.25)
arrow(ax, rq_r, rq_ys[5] + rq_h/2, ch_x, ch_ys[3] + ch_h/2)
arrow(ax, rq_r, rq_ys[6] + rq_h*0.75, ch_x, ch_ys[3] + ch_h*0.25)
arrow(ax, rq_r, rq_ys[6] + rq_h/2, ch_x, ch_ys[4] + ch_h/2, "#a78bfa")

# ══════════ ARROWS: Ch -> Contributions ══════════
ch_r = ch_x + ch_w
arrow(ax, ch_r, ch_ys[2] + ch_h*0.8, c_x, c_ys[0] + c_h/2, "#dc2626")
arrow(ax, ch_r, ch_ys[2] + ch_h/2, c_x, c_ys[1] + c_h/2, "#ea580c")
arrow(ax, ch_r, ch_ys[2] + ch_h*0.2, c_x, c_ys[2] + c_h/2, "#d97706")
arrow(ax, ch_r, ch_ys[4] + ch_h/2, c_x, c_ys[3] + c_h/2, "#ca8a04")
arrow(ax, ch_r, ch_ys[3] + ch_h*0.3, c_x, c_ys[4] + c_h/2, "#65a30d")
arrow(ax, ch_r, ch_ys[3] + ch_h/2, c_x, c_ys[5] + c_h/2, "#0d9488")

# ══════════ ARROWS: Contributions -> Publications ══════════
c_r = c_x + c_w
arrow(ax, c_r, c_ys[0] + c_h/2, p_x, p_ys[0] + p_h/2, "#7c3aed")
arrow(ax, c_r, c_ys[1] + c_h/2, p_x, p_ys[1] + p_h/2, "#6d28d9")
arrow(ax, c_r, c_ys[2] + c_h/2, p_x, p_ys[1] + p_h/2, "#6d28d9")
arrow(ax, c_r, c_ys[4] + c_h/2, p_x, p_ys[2] + p_h/2, "#5b21b6")

# ══════════ BOTTOM ══════════
ax.text(12, 3.0, "LCHAI v2.0: Lung Cancer Histologic Analysis with AI",
        ha="center", fontsize=17, fontweight="bold", color="#1e293b",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#f0f9ff",
                  edgecolor="#3b82f6", linewidth=1.5))
ax.text(12, 2.3, "Servio F. Lima Reina — University of Fribourg, Switzerland",
        ha="center", fontsize=13, color="#64748b")

fig.tight_layout()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print(f"Saved: {OUT}")
