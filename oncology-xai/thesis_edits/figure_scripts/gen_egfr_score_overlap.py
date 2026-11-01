"""Generate EGFR score-distribution overlap figure for ch06 evaluation chapter.

Visualises why a false negative (slide TCGA-86-8280, P(mut) = 0.076) is
statistically expected for an EGFR-mutant case with atypical morphology,
given:

  * prevalence = 11.4% (78 mutated / 687 slides)
  * mean AUROC = 0.701 (5-fold CV)
  * mean AUPRC = 0.360 (5-fold CV)

The figure shows two overlapping score distributions (wild-type vs
EGFR-mutant) calibrated to the reported AUROC, with the false-negative
tail (atypical mutants with low scores) and the false-positive tail
(wild-type slides with high scores) annotated. The TCGA-86-8280 slide
is marked at its observed P(mut) = 0.076 to make the false-negative
mechanism concrete.

Schematic: distributions are illustrative, not the empirical CV scores.
The shape and AUROC of the schematic are tuned to match the reported
metrics.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Reported metrics (5-fold CV; ch06 Table tab:mutation_luad and
# fig:auroc_auprc_prevalence; prevalence from ch03 tab:mutation_prevalence)
# ---------------------------------------------------------------------------
PREVALENCE = 0.114  # 78 / 687
AUROC = 0.701
AUPRC = 0.360
SLIDE_P = 0.076  # TCGA-86-8280 observed P(mut)

# ---------------------------------------------------------------------------
# Score distributions (Beta densities tuned so that AUROC ~= 0.70).
# Wild-type peaks low; EGFR-mutant is shifted right but heavily overlapping.
# Verified numerically below.
# ---------------------------------------------------------------------------
WT_BETA = (2.0, 6.0)  # Mean ~ 0.25
MUT_BETA = (2.6, 4.5)  # Mean ~ 0.37; tuned so schematic AUROC = 0.700

x = np.linspace(0.0, 1.0, 1000)
wt_pdf = stats.beta(*WT_BETA).pdf(x)
mut_pdf = stats.beta(*MUT_BETA).pdf(x)

# Numerical AUROC of the schematic (sanity check)
rng = np.random.default_rng(42)
wt_sample = stats.beta(*WT_BETA).rvs(size=10000, random_state=rng)
mut_sample = stats.beta(*MUT_BETA).rvs(size=10000, random_state=rng)
schematic_auroc = (mut_sample[:, None] > wt_sample[None, :]).mean()
print(f"Schematic AUROC: {schematic_auroc:.3f} (target {AUROC:.3f})")

# Normalise to a common visual scale
wt_norm = wt_pdf / wt_pdf.max()
mut_norm = mut_pdf / mut_pdf.max()

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11.5, 5.8))

WT_COLOR = "#cc6677"
MUT_COLOR = "#4477aa"

ax.fill_between(
    x,
    0,
    wt_norm,
    color=WT_COLOR,
    alpha=0.45,
    label="Wild-type EGFR slides (n = 609, 88.6%)",
)
ax.fill_between(
    x,
    0,
    mut_norm,
    color=MUT_COLOR,
    alpha=0.55,
    label="EGFR-mutant slides (n = 78, 11.4%)",
)
ax.plot(x, wt_norm, color=WT_COLOR, linewidth=1.2)
ax.plot(x, mut_norm, color=MUT_COLOR, linewidth=1.2)

# Decision threshold
ax.axvline(0.5, color="gray", linestyle=":", linewidth=1.0)
ax.text(
    0.505,
    1.02,
    "decision\nthreshold = 0.5",
    fontsize=8.5,
    color="gray",
    va="bottom",
)

# Mark slide TCGA-86-8280 at P = 0.076
ax.axvline(SLIDE_P, ymin=0.0, ymax=0.32, color="black", linestyle="--", linewidth=1.4)
ax.scatter(
    [SLIDE_P],
    [0.30],
    s=70,
    color="black",
    zorder=5,
    edgecolor="white",
    linewidth=1.0,
)
ax.annotate(
    "Slide TCGA-86-8280\nEGFR-mutant, $P = 0.076$\n→ false negative",
    xy=(SLIDE_P, 0.32),
    xytext=(0.20, 0.62),
    fontsize=10,
    arrowprops=dict(arrowstyle="->", color="black", lw=1.0),
    bbox=dict(boxstyle="round,pad=0.35", facecolor="white", edgecolor="black"),
)

# False-negative tail annotation (left side, where mutant distribution
# still has appreciable mass below the threshold)
ax.annotate(
    "False-negative tail:\nEGFR-mutant slides whose\nmorphology lacks the\ntypical lepidic/papillary\nfingerprint fall here",
    xy=(0.12, 0.55),
    xytext=(0.005, 0.92),
    fontsize=9.2,
    color="#1f3a5f",
    arrowprops=dict(arrowstyle="->", color="#1f3a5f", lw=1.0),
    bbox=dict(boxstyle="round,pad=0.30", facecolor="#e8eef7", edgecolor="#1f3a5f"),
)

# False-positive tail annotation (right side, where wild-type still has
# mass above the threshold)
ax.annotate(
    "False-positive tail:\nwild-type slides whose\nmorphology happens to\nresemble EGFR fall here",
    xy=(0.62, 0.10),
    xytext=(0.66, 0.92),
    fontsize=9.2,
    color="#5a2828",
    arrowprops=dict(arrowstyle="->", color="#5a2828", lw=1.0),
    bbox=dict(boxstyle="round,pad=0.30", facecolor="#f4e3e3", edgecolor="#5a2828"),
)

# Metric box (top centre)
metric_text = (
    f"AUROC = {AUROC:.3f}  "
    f"(≈ {int(round((1 - AUROC) * 100))}% of (positive, negative) pairs mis-ranked)\n"
    f"AUPRC = {AUPRC:.2f}  (precision averaged over operating points)\n"
    f"Prevalence = {PREVALENCE * 100:.1f}%"
)
ax.text(
    0.40,
    0.50,
    metric_text,
    fontsize=9.5,
    ha="left",
    va="bottom",
    bbox=dict(
        boxstyle="round,pad=0.45",
        facecolor="#f7f7f5",
        edgecolor="#666666",
        linewidth=0.8,
    ),
)

ax.set_xlabel("Predicted $P(\\text{EGFR mutated})$", fontsize=11)
ax.set_ylabel("Density (normalised)", fontsize=11)
ax.set_xlim(0.0, 1.0)
ax.set_ylim(0.0, 1.10)
ax.set_yticks([])
ax.set_xticks(np.arange(0.0, 1.01, 0.1))

ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, fontsize=10, frameon=False)

ax.set_title(
    "Why a false negative is statistically expected for EGFR slides with atypical morphology",
    fontsize=11.5,
    pad=10,
)

# Caption-style footnote
ax.text(
    0.5,
    -0.28,
    "Schematic. The wild-type and EGFR-mutant score distributions overlap heavily, "
    "which is what AUROC = 0.701 and AUPRC = 0.36 jointly imply. "
    "An EGFR-mutant slide whose tissue does not match the lepidic/papillary fingerprint "
    "lands in the left tail of the blue distribution — exactly where slide TCGA-86-8280 ($P = 0.076$) sits.",
    transform=ax.transAxes,
    ha="center",
    va="top",
    fontsize=8.8,
    style="italic",
    wrap=True,
)

plt.subplots_adjust(left=0.06, right=0.98, top=0.92, bottom=0.30)

OUT = (
    r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9"
    r"\chapters\figures\egfr_score_overlap.png"
)
plt.savefig(OUT, dpi=220, bbox_inches="tight")
print(f"Saved: {OUT}")
