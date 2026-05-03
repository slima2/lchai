"""Generate the "lepidic x solid as a learned proxy for IMA" diagram.

Explains why the trained FC-MIL fuzzy measure encodes
I_{lepidic, solid} = +0.032 as the strongest synergy for KRAS, even though
KRAS is clinically linked to the solid pattern and to invasive mucinous
adenocarcinoma (IMA), not to lepidic tumours.

Visual logic:
  REALITY: a KRAS-driven IMA leaves three components on a slide
    (1) surface-growing layer along alveoli (architecturally = lepidic)
    (2) dense sheet-like masses                (architecturally = solid)
    (3) mucus content                          (cellular, NOT layout)
  ANORAK ontology (6 layout classes) keeps (1) and (2), drops (3).
  Forced projection lights up BOTH lepidic and solid simultaneously.
  FC-MIL learns I_{lepidic,solid} = +0.032 as a learned "mucinous proxy".
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Circle, Ellipse

NEUTRAL = "#1B3A5C"
ACCENT_LEP = "#E0A100"        # lepidic = warm yellow
ACCENT_SOL = "#7A3FB5"        # solid   = purple
MUCIN = "#39A6A3"             # teal for mucus content
KO = "#C0392B"
OK = "#2A8C4A"
PAPER = "#F2EFE9"
GRID = "#888888"
INK = "#222222"

fig, ax = plt.subplots(figsize=(12.8, 7.6))
ax.set_xlim(0, 12.8)
ax.set_ylim(0, 8.0)
ax.axis("off")


def rbox(x, y, w, h, text, fc=PAPER, ec=NEUTRAL, fs=10, fw="normal",
         color=INK, lw=1.4, radius=0.12):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0.02,rounding_size={radius}",
        linewidth=lw, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center",
        fontsize=fs, fontweight=fw, color=color,
    )


def arrow(x1, y1, x2, y2, color=NEUTRAL, lw=1.6, style="-|>", mut=18):
    a = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style, mutation_scale=mut,
        linewidth=lw, color=color,
    )
    ax.add_patch(a)


# =====================================================================
# Title
# =====================================================================
ax.text(
    6.4, 7.65,
    r"Why the model learns  $I_{\,\mathrm{lepidic,\,solid}} = +0.032$  for KRAS",
    ha="center", va="center", fontsize=13.5, fontweight="bold", color=INK,
)
ax.text(
    6.4, 7.30,
    "A KRAS-driven mucinous tumour has three components, "
    "but ANORAK only labels two of them.",
    ha="center", va="center", fontsize=10.5, style="italic", color="#555555",
)

# =====================================================================
# LEFT PANEL  -  REALITY:  what is on a KRAS-mutant IMA slide
# =====================================================================
rbox(
    0.30, 0.95, 4.95, 5.85,
    "", fc="#FBF8F1", ec="#BBBBBB", lw=1.0, radius=0.18,
)
ax.text(
    2.78, 6.50,
    "REALITY  -  a KRAS-mutant IMA slide",
    ha="center", va="center", fontsize=11, fontweight="bold", color=NEUTRAL,
)
ax.text(
    2.78, 6.18,
    "three observable components",
    ha="center", va="center", fontsize=9.5, style="italic", color="#666666",
)

# Component 1: surface-growing (lepidic-like)
ax.text(0.55, 5.70, "(1)  surface-growing layer along alveoli",
        fontsize=9.5, color=INK, fontweight="bold", ha="left", va="center")
ax.text(0.55, 5.45, "tumour cells creep along existing lung surfaces",
        fontsize=8.5, color="#666666", style="italic", ha="left", va="center")
# tiny iconography: a wavy "alveolar surface" with cells along it
xs = np.linspace(0.55, 5.05, 200)
ys = 4.95 + 0.10 * np.sin(2.0 * np.pi * (xs - 0.55) / 1.4)
ax.plot(xs, ys, color="#999999", lw=1.2)
for cx in np.linspace(0.75, 4.85, 14):
    ax.add_patch(Circle((cx, ys[np.argmin(np.abs(xs - cx))] + 0.10),
                        0.06, fc=ACCENT_LEP, ec=ACCENT_LEP))
ax.text(5.10, 4.95, "$\\rightarrow$  lepidic",
        fontsize=9, color=ACCENT_LEP, fontweight="bold", va="center")

# Component 2: dense sheet (solid-like)
ax.text(0.55, 4.35, "(2)  dense sheet-like masses",
        fontsize=9.5, color=INK, fontweight="bold", ha="left", va="center")
ax.text(0.55, 4.10, "tumour piles up into solid blocks",
        fontsize=8.5, color="#666666", style="italic", ha="left", va="center")
# blob iconography
ax.add_patch(Polygon(
    [(0.75, 3.75), (1.25, 3.55), (1.85, 3.55), (2.30, 3.75),
     (2.55, 3.55), (3.10, 3.50), (3.65, 3.60), (4.10, 3.55),
     (4.55, 3.65), (4.85, 3.75), (4.85, 3.30), (0.75, 3.30)],
    closed=True, fc=ACCENT_SOL, ec=ACCENT_SOL, alpha=0.85,
))
ax.text(5.10, 3.55, "$\\rightarrow$  solid",
        fontsize=9, color=ACCENT_SOL, fontweight="bold", va="center")

# Component 3: mucus content (cellular, not layout)
ax.text(0.55, 3.00, "(3)  mucus content (cellular, not architectural)",
        fontsize=9.5, color=INK, fontweight="bold", ha="left", va="center")
ax.text(0.55, 2.75, "the defining feature of mucinous tumours",
        fontsize=8.5, color="#666666", style="italic", ha="left", va="center")
# mucus iconography: scattered teal granules + a rounded "pool"
ax.add_patch(Ellipse((1.40, 2.30), 1.55, 0.45, fc=MUCIN, ec=MUCIN, alpha=0.45))
ax.add_patch(Ellipse((3.40, 2.30), 1.65, 0.45, fc=MUCIN, ec=MUCIN, alpha=0.45))
rng = np.random.default_rng(1)
for _ in range(45):
    cx = rng.uniform(0.75, 4.85)
    cy = rng.uniform(2.10, 2.50)
    ax.add_patch(Circle((cx, cy), 0.025, fc=MUCIN, ec=MUCIN, alpha=0.9))

# Outcome of left panel
rbox(
    0.55, 1.20, 4.45, 0.70,
    "Three components on the slide:\n"
    "two architectural (lepidic, solid) + one cellular (mucus)",
    fc="#FFFFFF", ec=NEUTRAL, fs=9.2, lw=1.0, radius=0.10,
)

# =====================================================================
# Bridge arrow: "ANORAK projects onto layout-only label space"
# =====================================================================
arrow(5.30, 4.05, 7.30, 4.05, color=NEUTRAL, lw=2.0, mut=22)
ax.text(
    6.30, 4.50,
    "ANORAK projection",
    ha="center", va="center", fontsize=10, fontweight="bold", color=NEUTRAL,
)
ax.text(
    6.30, 4.25,
    "(layout-only,\nno mucinous slot)",
    ha="center", va="center", fontsize=8.5, style="italic", color="#666666",
)

# =====================================================================
# RIGHT PANEL  -  ANORAK 6-class projection
# =====================================================================
rbox(
    7.35, 0.95, 5.15, 5.85,
    "", fc="#F4F8FB", ec="#BBBBBB", lw=1.0, radius=0.18,
)
ax.text(
    9.92, 6.50,
    "WHAT THE MODEL SEES  -  6-d ANORAK vector",
    ha="center", va="center", fontsize=11, fontweight="bold", color=NEUTRAL,
)
ax.text(
    9.92, 6.18,
    "only architectural layout, no mucinous channel",
    ha="center", va="center", fontsize=9.5, style="italic", color="#666666",
)

# 6 channels as vertical bars - lepidic and solid filled, rest grey
ch_names = ["lepidic", "papillary", "micropap.", "acinar", "cribriform", "solid"]
ch_active = [True, False, False, False, False, True]
ch_colors = [ACCENT_LEP, GRID, GRID, GRID, GRID, ACCENT_SOL]
ch_mass = [0.55, 0.05, 0.08, 0.10, 0.05, 0.50]    # illustrative masses

bar_x0 = 7.50
bar_y0 = 3.20
bar_w = 0.55
bar_gap = 0.15
bar_h_max = 1.85
for i, (name, m, c, act) in enumerate(zip(ch_names, ch_mass, ch_colors, ch_active)):
    x = bar_x0 + i * (bar_w + bar_gap)
    # background empty bar
    ax.add_patch(FancyBboxPatch(
        (x, bar_y0), bar_w, bar_h_max,
        boxstyle="round,pad=0.005,rounding_size=0.05",
        fc="#FFFFFF", ec="#BBBBBB", lw=0.8,
    ))
    # filled mass
    fc = c if act else "#D5D5D5"
    ax.add_patch(FancyBboxPatch(
        (x, bar_y0), bar_w, bar_h_max * m,
        boxstyle="round,pad=0.005,rounding_size=0.05",
        fc=fc, ec=fc, lw=0,
        alpha=0.95 if act else 0.7,
    ))
    # label
    ax.text(x + bar_w / 2, bar_y0 - 0.20, name,
            ha="center", va="top", fontsize=8.2,
            color=INK if act else "#777777",
            fontweight="bold" if act else "normal",
            rotation=0)

ax.text(
    bar_x0 + 3 * (bar_w + bar_gap) - bar_gap / 2, bar_y0 + bar_h_max + 0.18,
    "lepidic and solid both light up  -  the same slide",
    ha="center", va="bottom", fontsize=9, color=NEUTRAL, fontweight="bold",
)

# Missing mucinous channel - a dashed slot floating to the right
ms_x = bar_x0 + 6 * (bar_w + bar_gap) + 0.05
ax.add_patch(FancyBboxPatch(
    (ms_x, bar_y0), bar_w, bar_h_max,
    boxstyle="round,pad=0.005,rounding_size=0.05",
    fc="#FFFFFF", ec=KO, lw=1.3, linestyle="--",
))
ax.text(ms_x + bar_w / 2, bar_y0 + bar_h_max / 2,
        "no\nmucinous\nchannel",
        ha="center", va="center", fontsize=8.4,
        color=KO, fontweight="bold")
ax.text(ms_x + bar_w / 2, bar_y0 - 0.20, "[ missing ]",
        ha="center", va="top", fontsize=8.2, color=KO, fontweight="bold")

# Mass on a slide annotation under bars
rbox(
    7.65, 1.20, 4.55, 0.70,
    "Architecture is captured;\n"
    "mucus content is invisible to a layout-only classifier",
    fc="#FFFFFF", ec=NEUTRAL, fs=9.2, lw=1.0, radius=0.10,
)

# =====================================================================
# BOTTOM BAND  -  the learned proxy
# =====================================================================
rbox(
    0.30, 0.10, 12.20, 0.75,
    "",
    fc="#FFF6D6", ec="#B58E00", lw=1.4, radius=0.14,
)
ax.text(
    0.55, 0.58,
    r"FC-MIL learns:  $I_{\,\mathrm{lepidic,\,solid}} = +0.032$",
    ha="left", va="center", fontsize=11, fontweight="bold", color="#7A5C00",
)
ax.text(
    0.55, 0.30,
    "the lepidic and solid co-presence acts as a learned "
    "PROXY for  'mucinous, KRAS-like tumour'  -  the channel "
    "the ontology does not provide.",
    ha="left", va="center", fontsize=9.6, color="#7A5C00", style="italic",
)

plt.tight_layout()
out = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\kras_lepidic_solid_proxy.png"
)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
