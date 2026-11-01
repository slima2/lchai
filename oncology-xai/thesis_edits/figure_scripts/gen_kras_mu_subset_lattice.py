"""Generate the "subset lattice" figure for the KRAS Interpretation block.

Visualises mechanistically what I_{lep, sol} = +0.032 does to the
2-additive fuzzy measure mu(S):

  - For S = {}, {lep}, {sol}: mu(S) is unchanged by the interaction
    term (it only involves at most one of {lep, sol}).
  - For S = {lep, sol}: mu(S) receives a +0.032 bump on top of
    phi_lep + phi_sol.

The companion slide TCGA-55-7815 has p_lep > 0 AND p_sol > 0
simultaneously, so the Choquet integral picks up this bump.

Values used (from Table tab:choquet_shapley + tab:choquet_interactions
in chapter 6):
  phi_lep = 0.165, phi_sol = 0.168, I_{lep, sol} = +0.032
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# ---------- Colour palette (consistent with other KRAS figures) ----------
NEUTRAL = "#1B3A5C"
GRAY = "#9AA0A6"
GREEN = "#2A8C4A"
GREEN_LIGHT = "#A7D8B6"
GOLD = "#B58E00"
INK = "#222222"
SOFT = "#F2EFE9"

# ---------- Data (real KRAS values from chapter 6) ----------
PHI_LEP = 0.165
PHI_SOL = 0.168
I_LS = 0.032

subsets = [
    (r"$\emptyset$",                       0.0,                         0.0),
    (r"$\{\mathrm{lepidic}\}$",            PHI_LEP,                     PHI_LEP),
    (r"$\{\mathrm{solid}\}$",              PHI_SOL,                     PHI_SOL),
    (r"$\{\mathrm{lepidic,\,solid}\}$",    PHI_LEP + PHI_SOL,           PHI_LEP + PHI_SOL + I_LS),
]
labels      = [s[0] for s in subsets]
mu_no_int   = [s[1] for s in subsets]
mu_with_int = [s[2] for s in subsets]

# ---------- Figure ----------
# Compact aspect ratio (~2.7:1) so figure + caption fit on a thesis page
# without overlapping the page footer.
FIG_W, FIG_H = 12.5, 4.6
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis("off")

# ---------- Title ----------
ax.text(
    6.25, 4.36,
    r"How $I_{\,\mathrm{lepidic,\,solid}} = +0.032$ modifies the fuzzy measure $\mu(S)$",
    ha="center", va="center", fontsize=13.0, fontweight="bold", color=INK,
)
ax.text(
    6.25, 4.06,
    "Only the subset containing BOTH lepidic and solid receives a bump; "
    "the Choquet integral picks it up only when both patterns are present in the slide.",
    ha="center", va="center", fontsize=9.6, style="italic", color="#555555",
)

# ---------- Bar chart axes (manually drawn inside ax) ----------
# Place the chart in the left half of the figure
chart_left = 0.55
chart_right = 7.85
chart_bottom = 0.85
chart_top = 3.65
chart_height = chart_top - chart_bottom

# y-axis range: 0 to 0.42 (to accommodate the +0.032 bump above 0.333)
Y_MAX = 0.42

def y_to_chart(value: float) -> float:
    """Map a mu(S) value in [0, Y_MAX] to chart y-coordinate."""
    return chart_bottom + (value / Y_MAX) * chart_height

# Draw axes
ax.plot([chart_left, chart_left], [chart_bottom, chart_top], color=INK, lw=1.2)
ax.plot([chart_left, chart_right], [chart_bottom, chart_bottom], color=INK, lw=1.2)

# Y-axis tick marks at 0, 0.1, 0.2, 0.3, 0.4
for tick in [0.0, 0.1, 0.2, 0.3, 0.4]:
    yc = y_to_chart(tick)
    ax.plot([chart_left - 0.06, chart_left], [yc, yc], color=INK, lw=1.0)
    ax.text(chart_left - 0.12, yc, f"{tick:.1f}",
            ha="right", va="center", fontsize=9, color=INK)

ax.text(chart_left - 0.55, (chart_bottom + chart_top) / 2, r"$\mu(S)$",
        ha="center", va="center", fontsize=12, color=INK, rotation=90)

# Horizontal grid lines (subtle)
for tick in [0.1, 0.2, 0.3, 0.4]:
    yc = y_to_chart(tick)
    ax.plot([chart_left, chart_right], [yc, yc],
            color="#DDDDDD", lw=0.6, linestyle="--", zorder=0)

# ---------- Bars ----------
n = len(subsets)
group_width = (chart_right - chart_left - 0.4) / n
bar_w = group_width * 0.32
gap = group_width * 0.06

for i, (lab, mu0, mu1) in enumerate(zip(labels, mu_no_int, mu_with_int)):
    cx = chart_left + 0.20 + group_width * (i + 0.5)

    # bar 1: without interaction (gray)
    x0 = cx - bar_w - gap / 2
    h0 = y_to_chart(mu0) - chart_bottom
    ax.add_patch(plt.Rectangle((x0, chart_bottom), bar_w, h0,
                                facecolor=GRAY, edgecolor=NEUTRAL, lw=0.8))
    if mu0 > 0:
        ax.text(x0 + bar_w / 2, y_to_chart(mu0) + 0.06, f"{mu0:.3f}",
                ha="center", va="bottom", fontsize=8.5, color=INK)

    # bar 2: with learned interaction (green)
    x1 = cx + gap / 2
    h1_base = y_to_chart(mu0) - chart_bottom    # the additive part
    bump_h = y_to_chart(mu1) - y_to_chart(mu0)  # the I_{lep,sol} bump
    # base portion
    ax.add_patch(plt.Rectangle((x1, chart_bottom), bar_w, h1_base,
                                facecolor=GREEN_LIGHT, edgecolor=NEUTRAL, lw=0.8))
    # bump portion (only non-zero on the {lep, sol} subset)
    if bump_h > 0:
        ax.add_patch(plt.Rectangle((x1, y_to_chart(mu0)), bar_w, bump_h,
                                    facecolor=GREEN, edgecolor=NEUTRAL, lw=0.8))
        # annotation arrow + label for the bump (placed INSIDE the chart area
        # so it does not collide with the right-hand explanation panel)
        ax.annotate(
            r"$+\,I_{\,\mathrm{lep,\,sol}} = +0.032$",
            xy=(x1, y_to_chart((mu0 + mu1) / 2)),
            xytext=(x1 - 2.5, y_to_chart(mu1) + 0.30),
            fontsize=9.5, color=GREEN, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.4,
                            connectionstyle="arc3,rad=-0.18"),
            ha="left",
        )

    if mu1 > 0:
        ax.text(x1 + bar_w / 2, y_to_chart(mu1) + 0.06, f"{mu1:.3f}",
                ha="center", va="bottom", fontsize=8.5, color=INK,
                fontweight="bold" if mu1 != mu0 else "normal")

    # subset label below x-axis
    ax.text(cx, chart_bottom - 0.18, lab,
            ha="center", va="top", fontsize=10, color=INK)

# X-axis label
ax.text((chart_left + chart_right) / 2, chart_bottom - 0.50,
        r"Subset $S \subseteq \{\mathrm{lepidic},\,\mathrm{solid}\}$ "
        r"of the 6-pattern lattice",
        ha="center", va="top", fontsize=10.0, color=INK, style="italic")

# ---------- Legend (small, inside chart area) ----------
legend_x = chart_left + 0.20
legend_y = chart_top - 0.15
ax.add_patch(plt.Rectangle((legend_x, legend_y - 0.07), 0.20, 0.15,
                            facecolor=GRAY, edgecolor=NEUTRAL, lw=0.8))
ax.text(legend_x + 0.28, legend_y + 0.005,
        r"without $I$ (additive baseline: $\sum_{k \in S}\phi_k$)",
        ha="left", va="center", fontsize=8.5, color=INK)

ax.add_patch(plt.Rectangle((legend_x, legend_y - 0.30), 0.20, 0.15,
                            facecolor=GREEN_LIGHT, edgecolor=NEUTRAL, lw=0.8))
ax.add_patch(plt.Rectangle((legend_x + 0.035, legend_y - 0.27), 0.13, 0.04,
                            facecolor=GREEN, edgecolor=NEUTRAL, lw=0.6))
ax.text(legend_x + 0.28, legend_y - 0.225,
        r"with learned $I$  ($\mu(S) = \sum_{k \in S}\phi_k + \sum_{\{j,k\}\subseteq S} I_{jk}$)",
        ha="left", va="center", fontsize=8.5, color=INK)

# ---------- Right-hand explanation panel ----------
panel_x = 8.20
panel_y = 0.85
panel_w = 4.10
panel_h = 2.80

ax.add_patch(FancyBboxPatch(
    (panel_x, panel_y), panel_w, panel_h,
    boxstyle="round,pad=0.04,rounding_size=0.14",
    facecolor=SOFT, edgecolor=NEUTRAL, lw=1.2,
))

ax.text(panel_x + panel_w / 2, panel_y + panel_h - 0.20,
        "On TCGA-55-7815 (KRAS-mutant)",
        ha="center", va="center", fontsize=10.5, fontweight="bold", color=NEUTRAL)

# Slide membership snippet (compact: 2 highlighted rows only)
slide_lines = [
    (r"$p_{\mathrm{lepidic}}$",      ">0",         GOLD),
    (r"$p_{\mathrm{solid}}$",        r"$=0.64\%$ (>0)", GOLD),
]
for i, (lhs, rhs, c) in enumerate(slide_lines):
    yt = panel_y + panel_h - 0.55 - i * 0.27
    ax.text(panel_x + 0.30, yt, lhs,
            ha="left", va="center", fontsize=9.2, color=c)
    ax.text(panel_x + 1.55, yt, rhs,
            ha="left", va="center", fontsize=9.2, color=c, fontweight="bold")

# Mechanism statement (compact)
ax.text(panel_x + panel_w / 2, panel_y + 1.30,
        r"$p_{\mathrm{lep}} > 0$  AND  $p_{\mathrm{sol}} > 0$",
        ha="center", va="center", fontsize=10.0, fontweight="bold", color=GREEN)
ax.text(panel_x + panel_w / 2, panel_y + 1.00,
        r"$\Rightarrow\ \mu(\{\mathrm{lep,\,sol}\}) = 0.365$ used",
        ha="center", va="center", fontsize=9.2, color=INK)
ax.text(panel_x + panel_w / 2, panel_y + 0.75,
        r"(vs $0.333$ additive baseline)",
        ha="center", va="center", fontsize=9.0, color="#555555", style="italic")
ax.text(panel_x + panel_w / 2, panel_y + 0.40,
        r"$\Rightarrow\ P(\mathrm{KRAS}) = 0.965$ Combined",
        ha="center", va="center", fontsize=9.5, fontweight="bold", color=GREEN)
ax.text(panel_x + panel_w / 2, panel_y + 0.17,
        r"vs $0.782$ (Embeddings-only)",
        ha="center", va="center", fontsize=8.8, color="#555555")

plt.tight_layout()
out = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\kras_mu_subset_lattice.png"
)
fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
