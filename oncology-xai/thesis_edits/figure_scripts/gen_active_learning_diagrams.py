"""Generate Active Learning diagrams for thesis."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

OUT_DIR = r"D:\Dropbox\PHD\THESIS\SLIMA_Thesis_Research_ver_2026_rev_9\chapters\figures"


def box(ax, x, y, w, h, text, color, textcolor="white", fontsize=7, bold=False):
    rect = mpatches.FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.12", facecolor=color,
        edgecolor="#374151", linewidth=0.7, zorder=3)
    ax.add_patch(rect)
    weight = "bold" if bold else "normal"
    ax.text(x + w/2, y + h/2, text, ha="center", va="center",
            fontsize=fontsize, color=textcolor, weight=weight, zorder=4,
            linespacing=1.3)


def arrow(ax, x1, y1, x2, y2, color="#6b7280"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->,head_width=0.12,head_length=0.08",
                                color=color, lw=1.2))


# ═══════════════════════════════════════════════════════
# DIAGRAM 1: Active Learning Correction Workflow
# ═══════════════════════════════════════════════════════

def gen_correction_workflow():
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.5)
    ax.axis("off")

    ax.text(7, 6.2, "Active Learning: Expert Pattern Correction Workflow",
            ha="center", fontsize=12, fontweight="bold", color="#1e293b")

    # Row of 6 boxes with comfortable spacing
    bw, bh = 1.8, 1.2
    gap = 0.4
    y0 = 2.8
    positions = []
    x = 0.3
    for _ in range(6):
        positions.append(x)
        x += bw + gap

    labels = [
        ("1. Viewer Tab\nPattern Overlay\n(misclassification\ndetected)", "#1e40af"),
        ("2. Draw Lasso\naround incorrect\ntiles (click\n& drag)", "#f97316"),
        ("3. Select correct\npattern from\ndropdown\n(6 ANORAK classes)", "#7c3aed"),
        ("4. Save &\nRetrain\n(submit to\nactive-learning\nservice)", "#dc2626"),
        ("5. Delta\nTraining\n(head-only,\n10 epochs)", "#059669"),
        ("6. Updated\noverlays +\npredictions", "#0891b2"),
    ]

    for i, (text, color) in enumerate(labels):
        box(ax, positions[i], y0, bw, bh, text, color, fontsize=6.5, bold=True)
        if i < 5:
            arrow(ax, positions[i] + bw + 0.02, y0 + bh/2,
                  positions[i+1] - 0.02, y0 + bh/2)

    # Bottom annotations
    annotations = [
        "Pathologist\nidentifies error",
        "~150 tiles\nselected",
        "e.g., acinar\n→ micropapillary",
        "Corrections\npersisted in DB",
        "~30 seconds\nCPU only",
        "New model\nversion v2.0.1",
    ]
    for i, txt in enumerate(annotations):
        ax.text(positions[i] + bw/2, y0 - 0.5, txt, ha="center",
                fontsize=6, color="#64748b", style="italic")

    # Feedback loop arrow — straight horizontal line above boxes, then down
    loop_y = y0 + bh + 0.8
    # Right end: up from box 6 top
    ax.annotate("", xy=(positions[5] + bw/2, y0 + bh),
                xytext=(positions[5] + bw/2, loop_y),
                arrowprops=dict(arrowstyle="-", color="#2563eb", lw=1.5))
    # Horizontal line
    ax.plot([positions[0] + bw/2, positions[5] + bw/2], [loop_y, loop_y],
            color="#2563eb", lw=1.5, zorder=2)
    # Down to box 1 top with arrowhead
    ax.annotate("", xy=(positions[0] + bw/2, y0 + bh),
                xytext=(positions[0] + bw/2, loop_y),
                arrowprops=dict(arrowstyle="->,head_width=0.15",
                                color="#2563eb", lw=1.5))
    ax.text(7, loop_y + 0.3,
            "Feedback loop: pathologist reviews updated overlay and may correct further",
            ha="center", fontsize=7.5, color="#2563eb", style="italic")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "active_learning_workflow.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")


# ═══════════════════════════════════════════════════════
# DIAGRAM 2: Delta Training Architecture
# ═══════════════════════════════════════════════════════

def gen_delta_training():
    fig, ax = plt.subplots(figsize=(7, 5.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 7)
    ax.axis("off")

    ax.text(5, 6.7, "Delta Training: Head-Only Fine-Tuning",
            ha="center", fontsize=11, fontweight="bold", color="#1e293b")
    ax.text(5, 6.3, "Backbone frozen — only the classification head is updated",
            ha="center", fontsize=8, color="#64748b", style="italic")

    # Frozen zone background
    frozen_bg = mpatches.FancyBboxPatch(
        (0.3, 3.0), 4.5, 3.0, boxstyle="round,pad=0.15",
        facecolor="#dbeafe", edgecolor="#93c5fd", linewidth=1.5,
        linestyle="--", zorder=1)
    ax.add_patch(frozen_bg)
    ax.text(2.55, 5.85, "FROZEN (no gradient updates)", ha="center",
            fontsize=7, color="#1e40af", fontweight="bold")

    # Trainable zone background
    train_bg = mpatches.FancyBboxPatch(
        (5.5, 3.0), 4.2, 3.0, boxstyle="round,pad=0.15",
        facecolor="#dcfce7", edgecolor="#86efac", linewidth=1.5,
        linestyle="--", zorder=1)
    ax.add_patch(train_bg)
    ax.text(7.6, 5.85, "TRAINABLE (10 epochs, lr=1e-5)", ha="center",
            fontsize=7, color="#166534", fontweight="bold")

    # CTransPath backbone
    box(ax, 0.6, 4.5, 2.0, 0.9, "CTransPath\nBackbone\n(Swin Tiny, 23M params)", "#3b82f6", fontsize=6.5)

    # Projection head
    box(ax, 0.6, 3.3, 2.0, 0.8, "Projection Head\n768 → 512-d\n(L2 normalized)", "#60a5fa", fontsize=6.5)

    arrow(ax, 1.6, 4.5, 1.6, 4.1)

    # Arrow from projection to cosine head
    arrow(ax, 2.6, 3.7, 5.7, 4.3)

    # FuzzyArcLoss head
    box(ax, 5.7, 3.8, 2.2, 1.2, "FuzzyArcLoss V2\nCosine Head\n(6 classes, ~3K params)\n$W \\in \\mathbb{R}^{6 \\times 512}$",
        "#16a34a", fontsize=6.5, bold=True)

    # Output
    box(ax, 8.3, 3.8, 1.2, 1.2, "Pattern\nPrediction\n$\\hat{y} \\in$\n{6 classes}", "#0891b2", fontsize=6.5)
    arrow(ax, 7.9, 4.4, 8.3, 4.4)

    # Input: corrected tiles
    box(ax, 5.7, 1.0, 3.8, 1.5, "Training Data\n──────────────────\nCorrected tiles (expert labels)\n+ Buffer of original tiles (30%)\n→ prevents catastrophic forgetting",
        "#fef3c7", textcolor="#92400e", fontsize=6.5)
    arrow(ax, 7.6, 2.5, 7.6, 3.8)

    # Input: tile embeddings
    box(ax, 0.6, 1.0, 2.0, 1.0, "tile_data.npz\n(pre-computed\n512-d embeddings)", "#e5e7eb", textcolor="#374151", fontsize=6.5)
    arrow(ax, 2.6, 1.5, 5.7, 1.5)

    # Version output
    box(ax, 3.0, 0.1, 4.0, 0.6, "Output: new_model_v2.0.1.pth → MinIO\n(original checkpoint never overwritten)",
        "#fef2f2", textcolor="#7f1d1d", fontsize=6)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "active_learning_delta_training.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    gen_correction_workflow()
    gen_delta_training()
    print("Done — 2 active learning diagrams generated.")
