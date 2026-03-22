"""Find TCGA slides with highest predicted mutation probability using baseline3 (patterns-only ABMIL)."""

import torch
import csv
import numpy as np
from pathlib import Path

CKPT_DIR = Path(r"D:\Dropbox\PHD\THESIS\CHECKPOINTS LUAD V2\checkpoints")
THESIS_DIR = Path(r"D:\Dropbox\PHD\THESIS")
MAF_PATH = THESIS_DIR / "cohortMAF.2025-11-16_with_histologic_patterns.csv"
GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]


class GatedAttention(torch.nn.Module):
    def __init__(self, L=256, D=128):
        super().__init__()
        self.V = torch.nn.Linear(L, D)
        self.U = torch.nn.Linear(L, D)
        self.w = torch.nn.Linear(D, 1, bias=False)

    def forward(self, h):
        a = self.w(torch.tanh(self.V(h)) * torch.sigmoid(self.U(h)))
        a = torch.softmax(a, dim=0)
        return (a * h).sum(dim=0)


class ABMIL_B3(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(6, 256),
            torch.nn.LayerNorm(256),
            torch.nn.ReLU(),
        )
        self.attention = GatedAttention(256, 128)
        self.classifier = torch.nn.Linear(256, 1)

    def forward(self, x):
        h = self.encoder(x)
        z = self.attention(h)
        return torch.sigmoid(self.classifier(z)).item()


def load_ground_truth():
    """Load ground truth mutations from MAF file."""
    silent = {"Silent", "Intron", "3'UTR", "5'UTR", "3'Flank", "5'Flank", "IGR", "RNA", "lincRNA"}
    case_mutations = {}
    with open(MAF_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gene = row["Hugo_Symbol"]
            case = row["case_barcode"]
            var_class = row["Variant_Classification"]
            if gene in GENES and var_class not in silent and case:
                case_mutations.setdefault(case, set()).add(gene)
    return case_mutations


def main():
    # Load tile predictions
    pred_files = sorted(THESIS_DIR.glob("TCGA-*_tiles_384_predictions.csv"))
    print(f"Loading {len(pred_files)} slide tile predictions...")

    slide_tiles = {}
    for pf in pred_files:
        name = pf.name.replace("_tiles_384_predictions.csv", "")
        classes = []
        with open(pf) as f:
            reader = csv.DictReader(f)
            for row in reader:
                classes.append(int(row["pred_class"]))
        if len(classes) < 10:
            continue
        arr = np.zeros((len(classes), 6), dtype=np.float32)
        for i, c in enumerate(classes):
            if 0 <= c < 6:
                arr[i, c] = 1.0
        slide_tiles[name] = torch.from_numpy(arr)

    print(f"Slides with enough tiles: {len(slide_tiles)}")

    # Load ground truth
    gt = load_ground_truth()

    # Run inference per gene
    for gene in GENES:
        models = []
        for fold in range(5):
            ckpt_path = CKPT_DIR / f"ckpt_baseline3_abmil_patterns_{gene}_fold{fold}.pth"
            if not ckpt_path.exists():
                print(f"  WARNING: {ckpt_path.name} not found")
                continue
            model = ABMIL_B3()
            sd = torch.load(ckpt_path, map_location="cpu", weights_only=False)
            model.load_state_dict(sd)
            model.eval()
            models.append(model)

        gene_results = []
        with torch.no_grad():
            for slide_name, tiles in slide_tiles.items():
                probs = [m(tiles) for m in models]
                avg_prob = np.mean(probs)
                case = "-".join(slide_name.split("-")[:3])
                has_mutation = gene in gt.get(case, set())
                gene_results.append((slide_name, avg_prob, has_mutation, case))

        gene_results.sort(key=lambda x: -x[1])

        high = [r for r in gene_results if r[1] >= 0.90]
        print(f"\n{'='*70}")
        print(f" {gene}: {len(high)} slides with predicted prob >= 0.90")
        print(f" (baseline3 patterns-only ABMIL, 5-fold ensemble)")
        print(f"{'='*70}")

        if high:
            for slide_name, prob, has_mut, case in high:
                short = slide_name.split(".")[0]
                gt_label = "MUT+" if has_mut else "WT"
                print(f"  {prob:.4f}  {gt_label:4s}  {case}  ->  {short}")
        else:
            print("  No slides >= 0.90. Top 10:")
            for slide_name, prob, has_mut, case in gene_results[:10]:
                short = slide_name.split(".")[0]
                gt_label = "MUT+" if has_mut else "WT"
                print(f"  {prob:.4f}  {gt_label:4s}  {case}  ->  {short}")

        # Also show: how many with prob >= 0.70, >= 0.80
        n70 = sum(1 for r in gene_results if r[1] >= 0.70)
        n80 = sum(1 for r in gene_results if r[1] >= 0.80)
        n90 = len(high)
        print(f"\n  Distribution: >= 0.70: {n70} | >= 0.80: {n80} | >= 0.90: {n90} / {len(gene_results)} slides")


if __name__ == "__main__":
    main()
