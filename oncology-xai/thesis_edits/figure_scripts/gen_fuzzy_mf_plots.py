"""Generate trapezoidal membership function plots for thesis Chapter 4."""
import matplotlib.pyplot as plt
import numpy as np
import os

OUT_DIR = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures"

SCALES = {
    "interaction_index": {
        "title": "Interaction Index $|I_{jk}|$",
        "xlabel": "$|I_{jk}|$",
        "sets": [
            ("Negligible",   [0, 0, 0.003, 0.008],   "#9ca3af"),
            ("Weak",         [0.005, 0.008, 0.012, 0.020], "#60a5fa"),
            ("Moderate",     [0.015, 0.025, 0.035, 0.050], "#fbbf24"),
            ("Strong",       [0.040, 0.055, 0.070, 0.090], "#f97316"),
            ("Very Strong",  [0.075, 0.090, 0.120, 0.120], "#ef4444"),
        ],
        "xlim": (0, 0.12),
    },
    "shapley_profile": {
        "title": "Shapley Profile (spread = $\\max\\phi_k - \\min\\phi_k$)",
        "xlabel": "Spread",
        "sets": [
            ("Uniform",                  [0, 0, 0.003, 0.008],       "#9ca3af"),
            ("Near-Uniform",             [0.005, 0.008, 0.015, 0.025], "#60a5fa"),
            ("Mod. Differentiated",      [0.020, 0.035, 0.050, 0.070], "#fbbf24"),
            ("Strongly Differentiated",  [0.060, 0.080, 0.120, 0.160], "#f97316"),
            ("Highly Polarised",         [0.140, 0.180, 0.250, 0.250], "#ef4444"),
        ],
        "xlim": (0, 0.25),
    },
    "shap_balance": {
        "title": "SHAP Balance (Pattern Contribution %)",
        "xlabel": "Pattern Contribution (%)",
        "sets": [
            ("Emb-Dominated", [0, 0, 5, 12],     "#3b82f6"),
            ("Emb-Led",       [8, 15, 20, 30],    "#60a5fa"),
            ("Balanced",      [25, 35, 45, 55],   "#a855f7"),
            ("Pattern-Led",   [45, 55, 65, 75],   "#f97316"),
            ("Pat-Dominated", [70, 80, 100, 100],  "#ef4444"),
        ],
        "xlim": (0, 100),
    },
    "shapley_individual": {
        "title": "Shapley Individual ($|\\delta_k|$ from uniform)",
        "xlabel": "$|\\delta_k|$ (%)",
        "sets": [
            ("Average",          [0, 0, 2, 5],       "#9ca3af"),
            ("Slightly Above",   [3, 6, 10, 15],     "#60a5fa"),
            ("Moderately Above", [12, 20, 30, 40],   "#fbbf24"),
            ("Strongly Above",   [35, 50, 80, 80],   "#f97316"),
        ],
        "xlim": (0, 80),
    },
    "attention_level": {
        "title": "ABMIL Attention Level (Tile Percentile)",
        "xlabel": "Attention Percentile",
        "sets": [
            ("Very Low",  [0, 0, 20, 40],     "#9ca3af"),
            ("Low",       [30, 45, 55, 65],    "#60a5fa"),
            ("Moderate",  [55, 65, 75, 85],    "#fbbf24"),
            ("High",      [75, 85, 92, 97],    "#f97316"),
            ("Very High", [93, 97, 100, 100],  "#ef4444"),
        ],
        "xlim": (0, 100),
    },
}


def trapezoid(x, abcd):
    a, b, c, d = abcd
    y = np.zeros_like(x)
    if b > a:
        mask = (x >= a) & (x < b)
        y[mask] = (x[mask] - a) / (b - a)
    mask = (x >= b) & (x <= c)
    y[mask] = 1.0
    if d > c:
        mask = (x > c) & (x <= d)
        y[mask] = (d - x[mask]) / (d - c)
    return y


def plot_scale(key, spec):
    fig, ax = plt.subplots(figsize=(6.5, 2.2))
    xmin, xmax = spec["xlim"]
    x = np.linspace(xmin, xmax, 2000)

    for label, abcd, color in spec["sets"]:
        y = trapezoid(x, abcd)
        ax.plot(x, y, color=color, linewidth=1.8, label=label)
        ax.fill_between(x, y, alpha=0.15, color=color)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(0, 1.15)
    ax.set_xlabel(spec["xlabel"], fontsize=9)
    ax.set_ylabel("$\\mu$", fontsize=9, rotation=0, labelpad=12)
    ax.set_title(spec["title"], fontsize=10, fontweight="bold")
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9, ncol=2)
    ax.axhline(y=1.0, color="#d1d5db", linewidth=0.5, linestyle="--")
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, f"fuzzy_mf_{key}.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for key, spec in SCALES.items():
        plot_scale(key, spec)
    print("Done — 5 plots generated.")
