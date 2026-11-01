"""Generate the "two scales" diagram for the TP53 interpretation
(slide TCGA-99-8025).

The figure visualises why TP53 is correctly predicted (P = 0.951) on a
slide where the architectural signature is only partially present:

  * Architectural scale: micropapillary 91.5%, solid 0.56% (signature
    only partially present; favoured high-grade pattern is dominant
    but not exclusive). Reaches the model through the pattern channel
    (slot in the PI-ABMIL / FC-MIL inputs).
  * Sub-cellular scale: nuclear pleomorphism (enlarged, dark, irregular
    nuclei). Reaches the model through the CTransPath embeddings.

SHAP attributes 61% to embeddings vs 39% to patterns, but the ablation
shows the pattern channel actually *hurts* prediction by 16.1 pp.
The two routes diverge sharply: the model "looks at" both, but only
the sub-cellular route carries useful signal on this slide.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OK = "#2A8C4A"        # green: route that helps
KO = "#C0392B"        # red:   route that hurts
NEUTRAL = "#1B3A5C"   # dark blue: nodes / structural elements
SOFT = "#F4F1EC"      # paper background for soft boxes
LIGHT_OK = "#E5F1E6"
LIGHT_KO = "#F6E2DE"
INK = "#222222"
GREY = "#666666"

fig, ax = plt.subplots(figsize=(13.5, 8.4))
ax.set_xlim(0, 13.5)
ax.set_ylim(0, 8.4)
ax.axis("off")


def box(x, y, w, h, text, fc=SOFT, ec=NEUTRAL, fontsize=10,
        fontweight="normal", color=INK, lw=1.3, radius=0.10):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        linewidth=lw, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fontsize, fontweight=fontweight, color=color, wrap=True,
    )


def arrow(x1, y1, x2, y2, color=NEUTRAL, lw=1.6, style="-|>", mut=18):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=mut,
        linewidth=lw, color=color,
    )
    ax.add_patch(a)


# ---------- Title ----------
ax.text(
    6.75, 8.05,
    "TP53 detection on slide TCGA-99-8025: two scales of evidence, two routes through the model",
    ha="center", va="center", fontsize=13, fontweight="bold", color=INK,
)
ax.text(
    6.75, 7.65,
    "Pattern attention is high (SHAP 39%) but counterproductive ($-16.1$ pp); the embeddings carry the signal.",
    ha="center", va="center", fontsize=10.5, color=GREY, style="italic",
)

# ---------- Source: TP53 mutation ----------
box(5.0, 6.55, 3.5, 0.75,
    "TP53 mutation\nslide TCGA-99-8025",
    fc="#FCEFE0", ec="#A85800",
    fontsize=11, fontweight="bold")

# Two diverging arrows from source to scale headers
arrow(6.0, 6.55, 3.1, 5.85, color=NEUTRAL, lw=1.6)
arrow(7.5, 6.55, 10.4, 5.85, color=NEUTRAL, lw=1.6)

# ---------- Scale headers ----------
box(0.6, 5.55, 5.1, 0.55,
    "Architectural scale (low magnification)",
    fc=LIGHT_KO, ec=KO,
    fontsize=10.5, fontweight="bold", color=KO)
box(7.8, 5.55, 5.1, 0.55,
    "Sub-cellular scale (high magnification)",
    fc=LIGHT_OK, ec=OK,
    fontsize=10.5, fontweight="bold", color=OK)

# ---------- Evidence on this slide ----------
box(0.6, 4.20, 5.1, 1.20,
    "What is visible?\n"
    "Micropapillary 91.5% (favoured)\n"
    "Solid 0.56% (favoured but absent)\n"
    "→ architectural signature partially present",
    fc=SOFT, ec=NEUTRAL, fontsize=9.7)

box(7.8, 4.20, 5.1, 1.20,
    "What is visible?\n"
    "Nuclear pleomorphism throughout the slide\n"
    "(enlarged, dark, irregularly shaped nuclei,\n"
    "Mendoza et al. 2024) → signature fully present",
    fc=SOFT, ec=NEUTRAL, fontsize=9.7)

arrow(3.15, 5.55, 3.15, 5.40, color=NEUTRAL, lw=1.4)
arrow(10.35, 5.55, 10.35, 5.40, color=NEUTRAL, lw=1.4)

# ---------- Model channel ----------
box(0.6, 2.85, 5.1, 1.10,
    "Pattern channel\n"
    "(6-d ANORAK probability vector → PI-ABMIL / FC-MIL slot)",
    fc=SOFT, ec=NEUTRAL, fontsize=9.7)

box(7.8, 2.85, 5.1, 1.10,
    "CTransPath embeddings\n"
    "(512-d tile features → ABMIL pooling → linear head)",
    fc=SOFT, ec=NEUTRAL, fontsize=9.7)

arrow(3.15, 4.20, 3.15, 3.95, color=NEUTRAL, lw=1.4)
arrow(10.35, 4.20, 10.35, 3.95, color=NEUTRAL, lw=1.4)

# ---------- SHAP / Ablation outcome per route ----------
box(0.6, 1.30, 5.1, 1.30,
    "What the model does with it\n"
    "SHAP attribution: 39%  (high attention)\n"
    "Ablation: combined 79.0% vs emb-only 95.1%\n"
    "→ pattern channel HURTS by $-16.1$ pp",
    fc=LIGHT_KO, ec=KO, fontsize=9.7, color="#7A1A12")

box(7.8, 1.30, 5.1, 1.30,
    "What the model does with it\n"
    "SHAP attribution: 61%  (dominant)\n"
    "Ablation: emb-only 95.1% (best)\n"
    "→ embeddings carry the TP53 signal",
    fc=LIGHT_OK, ec=OK, fontsize=9.7, color="#1F5F30")

arrow(3.15, 2.85, 3.15, 2.60, color=KO, lw=1.6)
arrow(10.35, 2.85, 10.35, 2.60, color=OK, lw=1.6)

# ---------- Final prediction ----------
arrow(3.15, 1.30, 6.0, 0.75, color=KO, lw=1.6, style="-|>")
arrow(10.35, 1.30, 7.5, 0.75, color=OK, lw=2.0, style="-|>")

box(5.0, 0.30, 3.5, 0.65,
    "P(TP53 mut) = 0.951\n(true positive, via sub-cellular route)",
    fc="#E8F0E5", ec=OK,
    fontsize=10.5, fontweight="bold", color="#1F5F30")

# ---------- "SHAP vs ablation" legend / takeaway ----------
ax.text(
    6.75, -0.10,
    "SHAP shows where the model looks; ablation shows what actually helps. "
    "On this slide the two diverge: the pattern channel attracts 39% of the attention but degrades the prediction.",
    ha="center", va="center", fontsize=9.5, color=GREY, style="italic",
)

plt.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)

OUT = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\tp53_two_scales.png"
)
plt.savefig(OUT, dpi=220, bbox_inches="tight")
print(f"Saved: {OUT}")
