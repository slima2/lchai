"""Generate the "two routes" diagram for the KRAS / B3 collapse explanation.

The figure visualises why B3 (ABMIL on the 6-d pattern vector + linear head)
collapses to chance on KRAS:
  - Route 1 (direct):   a dedicated mucinous channel does not exist in ANORAK.
  - Route 2 (indirect): a joint lepidic AND solid reading exists in principle,
    but additive heads (B3, PI-ABMIL) cannot perform it. Only FC-MIL's
    Choquet aggregator opens this route (I_{lepidic, solid} = +0.032).
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OK = "#2A8C4A"        # green: open route
KO = "#C0392B"        # red:   closed route
NEUTRAL = "#1B3A5C"   # dark blue: nodes
SOFT = "#F2EFE9"      # paper background for soft boxes
INK = "#222222"

fig, ax = plt.subplots(figsize=(12.5, 7.6))
ax.set_xlim(0, 12.5)
ax.set_ylim(0, 8.0)
ax.axis("off")


def box(x, y, w, h, text, fc=SOFT, ec=NEUTRAL, fontsize=10,
        fontweight="normal", color=INK, lw=1.4, radius=0.12):
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
    6.25, 7.65,
    "Why B3 (patterns only + additive head) collapses to chance on KRAS",
    ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK,
)
ax.text(
    6.25, 7.30,
    "Two routes from KRAS morphology to the classifier "
    "— both must be closed for B3 to fail, and both are.",
    ha="center", va="center", fontsize=10.5, style="italic", color="#555555",
)

# ---------- Source node ----------
box(
    4.5, 6.25, 3.5, 0.75,
    "KRAS-driven morphology\ninvasive mucinous adenocarcinoma (IMA)",
    fc="#FFF6D6", ec="#B58E00", fontsize=10.5, fontweight="bold",
)

# Two arrows from source to the two route headers
arrow(5.5, 6.25, 2.6, 5.50, color=NEUTRAL, lw=1.8)
arrow(7.0, 6.25, 9.9, 5.50, color=NEUTRAL, lw=1.8)
ax.text(3.7, 5.95, "Route 1: direct", fontsize=10, color=NEUTRAL,
        fontweight="bold", ha="center")
ax.text(8.85, 5.95, "Route 2: indirect (joint reading)", fontsize=10,
        color=NEUTRAL, fontweight="bold", ha="center")

# ---------- Route 1: dedicated mucinous channel ----------
box(
    0.6, 4.30, 4.2, 1.20,
    "A dedicated  mucinous  channel\nin the 6-d pattern vector",
    fc="#FBECEA", ec=KO, fontsize=10.5,
)

# 6-d vector representation under route 1
ax.text(
    0.6, 4.05, "ANORAK output  =",
    fontsize=9.5, color=INK, ha="left", va="top",
)
ch_labels = ["lepidic", "papillary", "micropap.", "acinar", "cribriform", "solid"]
ch_x0 = 0.6
ch_y0 = 3.45
ch_w = 0.66
ch_h = 0.45
for i, lab in enumerate(ch_labels):
    box(
        ch_x0 + i * ch_w, ch_y0, ch_w - 0.05, ch_h,
        lab, fc="#EAF2FA", ec=NEUTRAL, fontsize=8, radius=0.06, lw=1.0,
    )
# "no slot for mucinous" annotation
ax.text(
    ch_x0 + 3 * ch_w - ch_w / 2, ch_y0 - 0.18,
    "no  mucinous  slot in this vector",
    fontsize=9, color=KO, fontweight="bold", va="top", ha="center",
)

# Subtext explaining why
ax.text(
    2.70, 2.65,
    "ANORAK has 6 classes;\nIMA is not one of them\n(see Section 3.2)",
    fontsize=9.0, color="#555555", ha="center", va="center", style="italic",
)
# Status stamp aligned with right-side CLOSED / OPEN stamps
box(
    1.95, 1.40, 1.50, 0.45,
    "CLOSED",
    fc=KO, ec=KO, fontsize=10, fontweight="bold", color="white",
)

# ---------- Route 2: joint lepidic AND solid ----------
box(
    7.7, 4.30, 4.2, 1.20,
    "A joint reading of two channels:\n  lepidic  AND  solid  on the same slide",
    fc="#EAF6EE", ec=NEUTRAL, fontsize=10.5,
)

# Highlight lepidic and solid in a small mini-vector under route 2
mini_x0 = 7.95
mini_y0 = 3.45
mini_w = 0.62
for i, lab in enumerate(ch_labels):
    fc = "#FFE08A" if lab in {"lepidic", "solid"} else "#EAF2FA"
    ec = "#B58E00" if lab in {"lepidic", "solid"} else NEUTRAL
    fw = "bold" if lab in {"lepidic", "solid"} else "normal"
    box(
        mini_x0 + i * mini_w, mini_y0, mini_w - 0.05, ch_h,
        lab, fc=fc, ec=ec, fontsize=8, fontweight=fw, radius=0.06, lw=1.0,
    )
ax.text(
    mini_x0 + 3 * mini_w - mini_w / 2, mini_y0 - 0.18,
    "do  lepidic  and  solid  fire together?",
    fontsize=9, color="#B58E00", fontweight="bold",
    va="top", ha="center",
)

# Two consumers of the 6-d vector: additive head vs Choquet
# Additive head -> closed
box(
    7.00, 2.10, 2.20, 1.05,
    "ABMIL + linear head\n(B3, PI-ABMIL)\nadds channels independently\n"
    + r"$\rightarrow$ cannot ask  AND",
    fc="#FBECEA", ec=KO, fontsize=8.4,
)
box(
    7.45, 1.40, 1.30, 0.45,
    "CLOSED",
    fc=KO, ec=KO, fontsize=10, fontweight="bold", color="white",
)

# Choquet -> open
box(
    9.50, 2.10, 2.20, 1.05,
    "FC-MIL (Choquet)\naggregates jointly over the 6-d vector\n"
    + r"$\rightarrow$ learns  $I_{\,\mathrm{lep},\,\mathrm{sol}} = +0.032$",
    fc="#E5F3EB", ec=OK, fontsize=8.4,
)
box(
    9.95, 1.40, 1.30, 0.45,
    "OPEN",
    fc=OK, ec=OK, fontsize=10, fontweight="bold", color="white",
)

# ---------- Outcome strip (KRAS AUROC, 5-fold CV) ----------
box(
    0.6, 0.30, 11.3, 0.95,
    "",
    fc="#F8F8F8", ec="#BBBBBB", fontsize=10, lw=1.0,
)
ax.text(
    0.85, 0.95,
    "KRAS  (5-fold CV, mean AUROC, Table 6.5):",
    fontsize=9.8, color=INK, fontweight="bold", va="center", ha="left",
)

results = [
    ("B3 (patterns only, additive)",        0.545, KO, "both routes closed"),
    ("PI-ABMIL (patterns + embedding, additive)", 0.590, KO, "Route 2 still closed"),
    ("B2 (embedding only)",                 0.607, NEUTRAL, "embedding picks up signal"),
    ("FC-MIL (patterns + Choquet)",         0.609, OK, "Route 2 opens"),
]
xres = 0.85
for i, (name, auroc, c, note) in enumerate(results):
    rx = 0.85 + i * 2.78
    ax.text(rx, 0.65,  name,            fontsize=8.4, color=INK, ha="left", va="center")
    ax.text(rx, 0.45,  f"AUROC = {auroc:.3f}", fontsize=9.8,
            color=c, fontweight="bold", ha="left", va="center")
    ax.text(rx, 0.27,  note,            fontsize=8.0, color="#555555",
            style="italic", ha="left", va="center")

plt.tight_layout()
out = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\kras_two_routes.png"
)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
