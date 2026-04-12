"""
Evaluate FuzzyArcLoss V2 pattern classifier on ANORAK tiles
using the CORRECTED overlay index (4 Apr 2026).

Evaluates on the VALIDATION SET ONLY (80/20 split, seed 42)
to match the thesis protocol.

Generates:
  - confusion_matrix_fuzzyarcloss_v2_zenodo.png
  - classification report with per-class recall
"""
import sys, json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image
from scipy.io import loadmat
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix, classification_report, f1_score
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

CHECKPOINT = "/data/models/best_fuzzyarcloss_v2.pth"
TILES_DIR  = Path("/data/anorak_tiles")
MASKS_DIR  = Path("/data/anorak_masks")
INDEX_XLS  = "/data/overlay_index_corrected.xlsx"
OUT_DIR    = Path("/data/eval_output")
OUT_DIR.mkdir(exist_ok=True)

CORRECTED_ID2CLASS = {
    1: "cribriform", 2: "micropapillary", 3: "solid",
    4: "papillary", 5: "acinar", 6: "lepidic",
}

SPLIT_SEED = 42
TEST_SIZE  = 0.20

DEVICE = "cpu"

def load_mat_mask(path: Path) -> np.ndarray:
    data = loadmat(str(path), squeeze_me=True)
    for key in ["mask", "Mask", "BW", "label", "seg"]:
        if key in data and isinstance(data[key], np.ndarray) and data[key].ndim >= 2:
            return data[key].astype(np.int32)
    for k, v in data.items():
        if not k.startswith("_") and isinstance(v, np.ndarray) and v.ndim >= 2:
            return v.astype(np.int32)
    raise RuntimeError(f"No mask in {path}")


def get_binary_tissue_mask(label_map: np.ndarray, target_size: int = 224) -> np.ndarray:
    mask = (label_map > 0).astype(np.float32)
    pil_mask = Image.fromarray((mask * 255).astype(np.uint8)).resize(
        (target_size, target_size), Image.NEAREST
    )
    return np.array(pil_mask).astype(np.float32) / 255.0


def main():
    print("Loading checkpoint...")
    ck = torch.load(CHECKPOINT, map_location=DEVICE, weights_only=False)
    ck_id2label = {int(k): v for k, v in ck["id2label"].items()}
    num_classes = len(ck_id2label)
    print(f"  id2label: {ck_id2label}")
    print(f"  test_f1: {ck.get('test_f1')}, test_acc: {ck.get('test_accuracy')}, epoch: {ck.get('best_epoch')}")

    sys.path.insert(0, "/app")
    from app.ml.models.ctranspath_backbone import CTransPathPipeline

    model = CTransPathPipeline.from_finetuned(CHECKPOINT, DEVICE)
    model.eval()

    classifier_info = CTransPathPipeline.load_classifier_weights(CHECKPOINT, DEVICE)
    head_weight = classifier_info["head_weight"]
    s_scale = classifier_info["s_scale"]
    embed_dim = classifier_info["embed_dim"]

    print(f"  embed_dim={embed_dim}, s_scale={s_scale:.2f}, classes={num_classes}")

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    print("Loading corrected index...")
    df = pd.read_excel(INDEX_XLS)
    df = df[df["pattern"] != "none"].copy()
    print(f"  {len(df)} tiles with pattern labels (full dataset)")
    print(f"  Distribution:\n{df['pattern'].value_counts().to_string()}")

    # 80/20 stratified split — evaluate only on the held-out validation set
    train_df, val_df = train_test_split(
        df, test_size=TEST_SIZE, random_state=SPLIT_SEED,
        stratify=df["pattern"],
    )
    print(f"\n  Train: {len(train_df)}, Val: {len(val_df)} (seed={SPLIT_SEED}, test_size={TEST_SIZE})")
    print(f"  Val distribution:\n{val_df['pattern'].value_counts().to_string()}")
    df = val_df

    true_labels = []
    pred_labels = []
    tiles_processed = 0

    classes_sorted = sorted(set(ck_id2label.values()))
    class2idx = {c: i for i, c in enumerate(classes_sorted)}

    print(f"\nRunning inference on {len(df)} tiles...")
    with torch.no_grad():
        for idx, row in df.iterrows():
            tile_id = row["tile_id"]
            gt_pattern = row["pattern"].lower().strip()

            if gt_pattern not in class2idx:
                continue

            img_path = None
            for ext in [".png", ".jpg", ".jpeg"]:
                candidate = TILES_DIR / f"{tile_id}{ext}"
                if candidate.exists():
                    img_path = candidate
                    break
            if img_path is None:
                continue

            mat_path = MASKS_DIR / f"{tile_id}.mat"
            img = Image.open(img_path).convert("RGB")
            img_t = transform(img)

            if mat_path.exists():
                try:
                    lm = load_mat_mask(mat_path)
                    tissue_mask = get_binary_tissue_mask(lm, 224)
                    mask_t = torch.from_numpy(tissue_mask).unsqueeze(0)
                    x = torch.cat([img_t, mask_t], dim=0)
                except Exception:
                    x = torch.cat([img_t, torch.ones(1, 224, 224)], dim=0)
            else:
                x = torch.cat([img_t, torch.ones(1, 224, 224)], dim=0)

            x = x.unsqueeze(0).to(DEVICE)
            embedding = model(x)
            embedding = F.normalize(embedding, dim=1)
            w_norm = F.normalize(head_weight, dim=1)
            logits = s_scale * embedding @ w_norm.T
            probs = F.softmax(logits, dim=1).squeeze(0).cpu().numpy()
            pred_idx = int(np.argmax(probs))
            pred_pattern = ck_id2label[pred_idx]

            true_labels.append(gt_pattern)
            pred_labels.append(pred_pattern)
            tiles_processed += 1

            if tiles_processed % 100 == 0:
                print(f"  Processed {tiles_processed}/{len(df)} tiles...")

    print(f"\nTotal tiles evaluated: {tiles_processed}")

    report = classification_report(
        true_labels, pred_labels,
        labels=classes_sorted,
        target_names=classes_sorted,
        output_dict=True,
    )
    report_text = classification_report(
        true_labels, pred_labels,
        labels=classes_sorted,
        target_names=classes_sorted,
    )
    print("\n=== CLASSIFICATION REPORT ===")
    print(report_text)

    macro_f1 = f1_score(true_labels, pred_labels, labels=classes_sorted, average="macro")
    print(f"\nMacro-F1: {macro_f1*100:.1f}%")

    cm = confusion_matrix(true_labels, pred_labels, labels=classes_sorted)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm, annot=True, fmt="d", cmap="Blues",
        xticklabels=classes_sorted,
        yticklabels=classes_sorted,
        ax=ax, cbar_kws={"shrink": 0.8},
    )
    ax.set_xlabel("Predicted (Model)", fontsize=12)
    ax.set_ylabel("Ground Truth (Zenodo)", fontsize=12)
    ax.set_title(
        f"FuzzyArcLoss V2 — Confusion Matrix on ANORAK Val Set\n"
        f"(Zenodo-correct labels, N={tiles_processed}, Macro-F1={macro_f1*100:.1f}%)",
        fontsize=12,
    )
    plt.tight_layout()

    out_png = OUT_DIR / "confusion_matrix_fuzzyarcloss_v2_zenodo.png"
    fig.savefig(out_png, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"\nSaved: {out_png}")

    out_json = OUT_DIR / "eval_results.json"
    results = {
        "n_tiles": tiles_processed,
        "macro_f1": round(macro_f1, 4),
        "per_class": {},
    }
    for cls in classes_sorted:
        r = report.get(cls, {})
        results["per_class"][cls] = {
            "precision": round(r.get("precision", 0), 4),
            "recall": round(r.get("recall", 0), 4),
            "f1": round(r.get("f1-score", 0), 4),
            "support": int(r.get("support", 0)),
        }
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved: {out_json}")


if __name__ == "__main__":
    main()
