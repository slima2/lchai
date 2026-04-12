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
    fig, ax = plt.subplots(figsize=(8.5, 3.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.axis("off")

    ax.text(6, 4.7, "Active Learning: Expert Pattern Correction Workflow",
            ha="center", fontsize=11, fontweight="bold", color="#1e293b")

    # Step 1: Viewer
    box(ax, 0.1, 2.2, 1.7, 1.2, "1. Viewer Tab\nPattern Overlay\n(misclassification\ndetected)", "#1e40af", fontsize=6.5, bold=True)
    arrow(ax, 1.8, 2.8, 2.3, 2.8)

    # Step 2: Lasso
    box(ax, 2.3, 2.2, 1.7, 1.2, "2. Draw Lasso\naround incorrect\ntiles (click\n& drag)", "#f97316", fontsize=6.5, bold=True)
    arrow(ax, 4.0, 2.8, 4.5, 2.8)

    # Step 3: Assign pattern
    box(ax, 4.5, 2.2, 1.7, 1.2, "3. Select\ncorrect pattern\nfrom dropdown\n(6 ANORAK classes)", "#7c3aed", fontsize=6.5, bold=True)
    arrow(ax, 6.2, 2.8, 6.7, 2.8)

    # Step 4: Submit
    box(ax, 6.7, 2.2, 1.7, 1.2, "4. Save &\nRetrain\n(submit to\nactive-learning\nservice)", "#dc2626", fontsize=6.5, bold=True)
    arrow(ax, 8.4, 2.8, 8.9, 2.8)

    # Step 5: Delta training
    box(ax, 8.9, 2.2, 1.5, 1.2, "5. Delta\nTraining\n(head-only\n10 epochs)", "#059669", fontsize=6.5, bold=True)
    arrow(ax, 10.4, 2.8, 10.7, 2.8)

    # Step 6: Updated
    box(ax, 10.7, 2.2, 1.2, 1.2, "6. Updated\noverlays +\npredictions", "#0891b2", fontsize=6.5, bold=True)

    # Bottom annotations
    ax.text(1.0, 1.5, "Pathologist\nidentifies error", ha="center", fontsize=6, color="#64748b", style="italic")
    ax.text(3.15, 1.5, "152 tiles\nselected", ha="center", fontsize=6, color="#64748b", style="italic")
    ax.text(5.35, 1.5, "e.g., acinar\n→ micropapillary", ha="center", fontsize=6, color="#64748b", style="italic")
    ax.text(7.55, 1.5, "Corrections\npersisted in DB", ha="center", fontsize=6, color="#64748b", style="italic")
    ax.text(9.65, 1.5, "~30 seconds\nCPU only", ha="center", fontsize=6, color="#64748b", style="italic")
    ax.text(11.3, 1.5, "New model\nversion v2.0.1", ha="center", fontsize=6, color="#64748b", style="italic")

    # Feedback loop arrow
    ax.annotate("", xy=(0.95, 3.6), xytext=(11.3, 3.6),
                arrowprops=dict(arrowstyle="->,head_width=0.15",
                                color="#2563eb", lw=1.5,
                                connectionstyle="arc3,rad=-0.25"))
    ax.text(6, 4.2, "Feedback loop: pathologist reviews updated overlay and may correct further",
            ha="center", fontsize=7, color="#2563eb", style="italic")

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "active_learning_workflow.png")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {path}")


# ═══════════════════════════════════════════════════════
# DIAGRAM 2: Delta Training Architecture
# ═══════════════════════════════════════════════════════

def gen_delta_training():
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
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
