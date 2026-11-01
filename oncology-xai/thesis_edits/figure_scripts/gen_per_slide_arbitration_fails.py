"""Generate the four-panel diagram for Chapter 4 Section 4.5.6.

The figure summarises the four reasons (R1-R4) why LCHAI v2.0 fixes
its model choice at the gene level and rejects per-slide arbitration:

  - R1 (top-left)  : Circularity -- per-slide selection requires the label.
  - R2 (top-right) : Score incomparability across separately trained models.
  - R3 (bottom-left): max-of-experts is not generally a better classifier.
  - R4 (bottom-right): per-slide variance is what AUROC already integrates.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ------------------------------------------------------------ Palette
OK = "#2A8C4A"
KO = "#C0392B"
WARN = "#B58E00"
NEUTRAL = "#1B3A5C"
SOFT = "#F2EFE9"
INK = "#222222"
GREY = "#888888"
LIGHTGREY = "#DDDDDD"

FIG_W, FIG_H = 13.0, 8.6
fig = plt.figure(figsize=(FIG_W, FIG_H))

# Top-level title
fig.text(
    0.5, 0.965,
    "Why LCHAI v2.0 does not arbitrate models per slide",
    ha="center", va="center", fontsize=14, fontweight="bold", color=INK,
)
fig.text(
    0.5, 0.937,
    "Four reasons why label-blind per-slide model selection is "
    "statistically ill-posed",
    ha="center", va="center", fontsize=10.5, style="italic", color="#555555",
)

# Layout: 2x2 grid with margins
gs = fig.add_gridspec(
    2, 2,
    left=0.05, right=0.97, top=0.91, bottom=0.04,
    wspace=0.18, hspace=0.18,
)

# ============================================================
# PANEL R1: Circularity
# ============================================================
ax = fig.add_subplot(gs[0, 0])
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

ax.text(0.3, 9.3, "(R1) Circularity",
        fontsize=12, fontweight="bold", color=KO, ha="left", va="center")
ax.text(0.3, 8.6,
        "Per-slide selection requires the ground-truth label.",
        fontsize=9.5, style="italic", color="#555555", ha="left", va="center")


def rbox(x, y, w, h, text, fc, ec, fontsize=9.5, fontweight="normal",
         color=INK):
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.18",
        linewidth=1.4, edgecolor=ec, facecolor=fc,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center",
            fontsize=fontsize, fontweight=fontweight, color=color, wrap=True)


def ar(ax_, x1, y1, x2, y2, color=NEUTRAL, lw=1.6, style="-|>", mut=15):
    a = FancyArrowPatch((x1, y1), (x2, y2),
                        arrowstyle=style, mutation_scale=mut,
                        linewidth=lw, color=color)
    ax_.add_patch(a)


# Three nodes in a triangle layout
rbox(1.0, 6.0, 3.6, 1.2,
     "Test slide arrives\n(label $y$ unknown)",
     fc="#EAF2F9", ec=NEUTRAL, fontsize=9.5)

rbox(5.4, 6.0, 3.6, 1.2,
     "Choose the model\nwhose output matches $y$",
     fc="#FFF6D6", ec=WARN, fontsize=9.5)

rbox(3.2, 2.6, 3.6, 1.2,
     "But $y$ is exactly\nwhat we are predicting",
     fc="#FBECEA", ec=KO, fontsize=9.5, fontweight="bold")

# Arrows connecting the three nodes in a loop
ar(ax, 4.6, 6.6, 5.4, 6.6, color=NEUTRAL, lw=1.6)
ar(ax, 7.2, 6.0, 5.5, 3.85, color=NEUTRAL, lw=1.6)
ar(ax, 3.6, 3.85, 2.0, 6.0, color=KO, lw=1.6)

# "X" through the loop centre
ax.text(5.0, 5.0, "$\\boldsymbol{\\oslash}$",
        fontsize=44, color=KO, ha="center", va="center", alpha=0.55)

ax.text(5.0, 1.4,
        "Any rule of the form \\emph{``use the model that matches the truth''}\n"
        "is not implementable at inference time --- it is post-hoc cherry-picking.",
        fontsize=8.7, style="italic", color="#555555",
        ha="center", va="center")
# Use plain text without LaTeX since matplotlib's mathtext doesn't support \emph
ax.texts[-1].set_text(
    "Any rule of the form \"use the model that matches the truth\"\n"
    "is not implementable at inference time -- it is post-hoc cherry-picking.")

# ============================================================
# PANEL R2: Score incomparability
# ============================================================
ax = fig.add_subplot(gs[0, 1])
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

ax.text(0.3, 9.3, "(R2) Score incomparability",
        fontsize=12, fontweight="bold", color=KO, ha="left", va="center")
ax.text(0.3, 8.6,
        "Sigmoid outputs of independently trained models are not on a common scale.",
        fontsize=9.5, style="italic", color="#555555", ha="left", va="center")

# Two number lines (sigmoid outputs)
def numline(y, label, marker_x, marker_label, marker_color):
    # Axis line
    ax.plot([1.5, 8.5], [y, y], color=NEUTRAL, lw=1.6, solid_capstyle="round")
    # Tick labels
    for tx, tlabel in [(1.5, "0"), (5.0, "0.5"), (8.5, "1")]:
        ax.plot([tx, tx], [y - 0.1, y + 0.1], color=NEUTRAL, lw=1.4)
        ax.text(tx, y - 0.4, tlabel, ha="center", va="top",
                fontsize=8.5, color=INK)
    # Threshold line
    ax.plot([5.0, 5.0], [y - 0.35, y + 0.35], color=GREY, lw=1.2,
            linestyle="--")
    # Marker
    cx = 1.5 + marker_x * 7.0
    ax.plot([cx], [y], marker="o", markersize=10,
            color=marker_color, markeredgecolor="white", markeredgewidth=1.5,
            zorder=5)
    ax.text(cx, y + 0.55, marker_label, ha="center", va="bottom",
            fontsize=9, fontweight="bold", color=marker_color)
    # Model label on the left
    ax.text(0.4, y, label, ha="left", va="center",
            fontsize=9.5, fontweight="bold", color=INK)


numline(6.6, "$f_{\\mathrm{B2}}$",  marker_x=0.69,
        marker_label="$P_{\\mathrm{B2}}=0.69$", marker_color=OK)
numline(4.4, "$f_{\\mathrm{PI}}$",  marker_x=0.25,
        marker_label="$P_{\\mathrm{PI}}=0.25$", marker_color=KO)

# Annotation between the two lines
ax.text(9.1, 5.5, "?", ha="center", va="center",
        fontsize=22, color=KO, fontweight="bold")
ax.text(0.4, 3.4,
        "Both classifiers use $\\sigma(\\cdot) > 0.5$ as decision rule, but\n"
        "their decision surfaces live in different feature spaces (518-d vs 512-d)\n"
        "and have different implicit calibration.\n"
        "$\\max(P_{\\mathrm{B2}}, P_{\\mathrm{PI}})$ is not a calibrated probability\n"
        "of any well-defined event.",
        fontsize=8.7, style="italic", color="#555555",
        ha="left", va="top")

# ============================================================
# PANEL R3: max-of-experts trade-off
# ============================================================
ax = fig.add_subplot(gs[1, 0])
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

ax.text(0.3, 9.3, "(R3) $\\max$-of-experts is not generally better",
        fontsize=12, fontweight="bold", color=KO, ha="left", va="center")
ax.text(0.3, 8.6,
        "max(s_A, s_B) inflates scores in BOTH the mutant and "
        "wild-type cohorts.",
        fontsize=9.5, style="italic", color="#555555", ha="left", va="center")


def gauss(x, mu, sigma):
    return np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def mini_hist(x_off, y_off, w, h, mu_a, mu_b, mu_max, label, recovery_text):
    # Frame
    ax.plot([x_off, x_off + w, x_off + w, x_off, x_off],
            [y_off, y_off, y_off + h, y_off + h, y_off],
            color=GREY, lw=0.8)
    ax.text(x_off + w / 2, y_off + h + 0.18, label,
            ha="center", va="bottom", fontsize=9.5, fontweight="bold",
            color=INK)

    xs = np.linspace(0, 1, 200)
    sa = gauss(xs, mu_a, 0.13)
    sb = gauss(xs, mu_b, 0.13)
    smax = gauss(xs, mu_max, 0.10)

    # Map [0,1] to [x_off, x_off+w] and [0,1] to [y_off, y_off+h]
    def xtr(v):
        return x_off + v * w

    def ytr(v):
        return y_off + v * h * 0.85

    ax.fill_between(xtr(xs), ytr(sa), y_off, color=NEUTRAL,
                    alpha=0.20)
    ax.plot(xtr(xs), ytr(sa), color=NEUTRAL, lw=1.4, label="$s_A$")
    ax.fill_between(xtr(xs), ytr(sb), y_off, color=WARN,
                    alpha=0.25)
    ax.plot(xtr(xs), ytr(sb), color=WARN, lw=1.4, label="$s_B$")
    ax.plot(xtr(xs), ytr(smax), color=KO, lw=2.0,
            label="$\\max(s_A,s_B)$")

    # Threshold line at 0.5
    ax.plot([xtr(0.5), xtr(0.5)], [y_off, y_off + h * 0.95],
            color=GREY, lw=1.2, linestyle="--")
    ax.text(xtr(0.5), y_off - 0.18, "0.5",
            ha="center", va="top", fontsize=8.0, color=GREY)

    # Recovery / FP annotation arrow
    ax.text(x_off + w / 2, y_off - 0.65, recovery_text,
            ha="center", va="top", fontsize=8.7, style="italic",
            color=NEUTRAL)


mini_hist(0.5, 4.0, 4.0, 3.0,
          mu_a=0.55, mu_b=0.40, mu_max=0.65,
          label="Mutant cohort scores",
          recovery_text="$\\max$ shift right $\\Rightarrow$\n"
                        "recovers some false negatives")
mini_hist(5.5, 4.0, 4.0, 3.0,
          mu_a=0.30, mu_b=0.20, mu_max=0.40,
          label="Wild-type cohort scores",
          recovery_text="$\\max$ shift right $\\Rightarrow$\n"
                        "creates new false positives")

# Shared legend at the top of the panel
legend_y = 7.7
ax.plot([0.6, 1.0], [legend_y, legend_y], color=NEUTRAL, lw=1.6)
ax.text(1.1, legend_y, "$s_A$", fontsize=9, va="center", color=INK)
ax.plot([1.9, 2.3], [legend_y, legend_y], color=WARN, lw=1.6)
ax.text(2.4, legend_y, "$s_B$", fontsize=9, va="center", color=INK)
ax.plot([3.2, 3.6], [legend_y, legend_y], color=KO, lw=2.2)
ax.text(3.7, legend_y, "$\\max(s_A, s_B)$", fontsize=9, va="center",
        color=INK)

# Bottom verdict
ax.text(5.0, 1.7,
        "Net effect on cross-validated AUROC is empirical and frequently "
        "negative,\n"
        "especially for low-prevalence genes (e.g.\\ KEAP1: $14.3\\%$ mutation rate).",
        fontsize=8.7, style="italic", color="#555555", ha="center", va="center")

# ============================================================
# PANEL R4: per-slide variance is what AUROC integrates
# ============================================================
ax = fig.add_subplot(gs[1, 1])
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis("off")

ax.text(0.3, 9.3, "(R4) Per-slide variance is what AUROC already integrates",
        fontsize=12, fontweight="bold", color=KO, ha="left", va="center")
ax.text(0.3, 8.6,
        "5-fold CV AUROC = expected ranking quality; per-slide gaps are noise.",
        fontsize=9.5, style="italic", color="#555555", ha="left", va="center")

# Synthetic per-slide predictions for B2 and PI on a small KEAP1-like cohort
rng = np.random.default_rng(42)
n_slides = 14
slide_x = np.arange(n_slides) + 0.5
b2 = rng.uniform(0.10, 0.85, size=n_slides)
# PI tends slightly higher on average
pi = b2 + rng.normal(0.05, 0.18, size=n_slides)
pi = np.clip(pi, 0.05, 0.95)

# Box for the chart
chart_x0, chart_x1 = 0.9, 9.3
chart_y0, chart_y1 = 3.0, 7.7

# y-axis (probability)
def py(p):
    return chart_y0 + p * (chart_y1 - chart_y0)


# x-axis (slide index)
def px(i):
    return chart_x0 + (i + 0.5) / n_slides * (chart_x1 - chart_x0)


# Frame
ax.plot([chart_x0, chart_x1, chart_x1, chart_x0, chart_x0],
        [chart_y0, chart_y0, chart_y1, chart_y1, chart_y0],
        color=GREY, lw=0.8)

# y-ticks
for p, lab in [(0.0, "0"), (0.5, "0.5"), (1.0, "1")]:
    ax.plot([chart_x0 - 0.1, chart_x0], [py(p), py(p)],
            color=GREY, lw=0.8)
    ax.text(chart_x0 - 0.2, py(p), lab,
            ha="right", va="center", fontsize=8.0, color=INK)

# Threshold line at P=0.5
ax.plot([chart_x0, chart_x1], [py(0.5), py(0.5)],
        color=GREY, lw=1.0, linestyle="--")

# Per-slide markers and connecting verticals
for i in range(n_slides):
    x = px(i)
    ax.plot([x, x], [py(b2[i]), py(pi[i])],
            color=LIGHTGREY, lw=1.0)

# Markers
ax.plot([px(i) for i in range(n_slides)],
        [py(b2[i]) for i in range(n_slides)],
        marker="o", markersize=6, linestyle="none",
        markerfacecolor=NEUTRAL, markeredgecolor="white",
        markeredgewidth=0.8, label="$P_{\\mathrm{B2}}$")
ax.plot([px(i) for i in range(n_slides)],
        [py(pi[i]) for i in range(n_slides)],
        marker="s", markersize=6, linestyle="none",
        markerfacecolor=KO, markeredgecolor="white",
        markeredgewidth=0.8, label="$P_{\\mathrm{PI\\text{-}ABMIL}}$")

# Cohort means as horizontal lines
ax.plot([chart_x0, chart_x1], [py(np.mean(b2)), py(np.mean(b2))],
        color=NEUTRAL, lw=1.2, alpha=0.6)
ax.text(chart_x1 + 0.15, py(np.mean(b2)),
        "$\\overline{P}_{\\mathrm{B2}}$",
        fontsize=8.5, color=NEUTRAL, va="center", ha="left")
ax.plot([chart_x0, chart_x1], [py(np.mean(pi)), py(np.mean(pi))],
        color=KO, lw=1.2, alpha=0.6)
ax.text(chart_x1 + 0.15, py(np.mean(pi)),
        "$\\overline{P}_{\\mathrm{PI}}$",
        fontsize=8.5, color=KO, va="center", ha="left")

# x-axis label (slide index)
ax.text((chart_x0 + chart_x1) / 2, chart_y0 - 0.35,
        "slides (cohort)",
        ha="center", va="top", fontsize=8.5, color=GREY)

# Bottom verdict
ax.text(5.0, 1.7,
        "On any single slide either model can win; the cohort AUROC "
        "integrates\n"
        "this per-slide spread. Selecting the per-gene best-in-expectation\n"
        "model minimises expected misranking risk.",
        fontsize=8.7, style="italic", color="#555555",
        ha="center", va="center")

# Legend (top-right, inside the chart frame)
legend_y = 7.95
ax.plot([5.6], [legend_y], marker="o", markersize=6,
        markerfacecolor=NEUTRAL, markeredgecolor="white",
        markeredgewidth=0.8)
ax.text(5.78, legend_y, "$P_{\\mathrm{B2}}$",
        fontsize=9, va="center", color=INK)
ax.plot([7.0], [legend_y], marker="s", markersize=6,
        markerfacecolor=KO, markeredgecolor="white",
        markeredgewidth=0.8)
ax.text(7.18, legend_y, "$P_{\\mathrm{PI\\text{-}ABMIL}}$",
        fontsize=9, va="center", color=INK)


# ============================================================
out = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\per_slide_arbitration_fails.png"
)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
