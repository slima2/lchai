"""Report: TCGA slides with confirmed mutations per gene, cross-referenced with available cohort."""

import csv
from collections import defaultdict
from pathlib import Path

GENES = ["TP53", "EGFR", "KRAS", "STK11", "KEAP1", "RBM10"]
MAF = Path(r"D:\Dropbox\PHD\THESIS\cohortMAF.2025-11-16_with_histologic_patterns.csv")
SLIDES_DEC = Path(r"D:\Dropbox\PHD\THESIS\DEC 17 763 TCGA HISTO FILES ANALYZED\tcga_histologic_pattern_summary_per_slide_dec2025.csv")

SILENT = {"Silent", "Intron", "3'UTR", "5'UTR", "3'Flank", "5'Flank", "IGR", "RNA", "lincRNA"}

# Read slide info (703 slides with pattern analysis)
slide_info = {}
with open(SLIDES_DEC) as f:
    for row in csv.DictReader(f):
        slide_info[row["case_barcode"]] = {
            "slide_id": row["slide_id"],
            "n_tiles": int(row["n_tiles_total"]),
        }

# Read mutations from MAF
case_gene_vars = defaultdict(lambda: defaultdict(list))
with open(MAF, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        g = row["Hugo_Symbol"]
        c = row["case_barcode"]
        vc = row["Variant_Classification"]
        if g in GENES and vc not in SILENT and c:
            case_gene_vars[c][g].append(vc)

# Available local SVS files
local_svs = {
    "TCGA-99-8025": "BEST MUTATION SAMPLES/TP53/",
    "TCGA-05-4425": "BEST MUTATION SAMPLES/EGFR/",
    "TCGA-55-7815": "BEST MUTATION SAMPLES/KRAS/",
    "TCGA-49-AAR0": "BEST MUTATION SAMPLES/STK11/",
    "TCGA-49-AAR9": "BEST MUTATION SAMPLES/KEAP1/",
}

print("=" * 90)
print("MUTATION REPORT — TCGA slides with confirmed non-silent mutations per gene")
print("Cohort: 703 slides with histologic pattern analysis (dec 2025)")
print("=" * 90)

for gene in GENES:
    cases_mut = []
    for c, gene_vars in case_gene_vars.items():
        if gene in gene_vars and c in slide_info:
            cases_mut.append((c, gene_vars[gene], slide_info[c]))
    cases_mut.sort(key=lambda x: -x[2]["n_tiles"])

    local = [c for c in local_svs if gene in case_gene_vars.get(c, {})]

    print(f"\n{'-'*90}")
    print(f" {gene}: {len(cases_mut)} slides with confirmed mutation (in 703-slide cohort)")
    print(f" Local SVS available: {', '.join(local) if local else 'NONE - need to download'}")
    print(f"{'-'*90}")

    print(f" {'Case':<22} {'Tiles':>7} {'Variant Types':<40} {'Also mutated in'}")
    print(f" {'-'*22} {'-'*7} {'-'*40} {'-'*25}")

    for c, v, s in cases_mut[:15]:
        n_t = s["n_tiles"]
        vtypes = ", ".join(sorted(set(v)))
        other = [g for g in case_gene_vars[c] if g != gene and g in GENES]
        other_str = ", ".join(other) if other else "-"
        marker = " * LOCAL" if c in local_svs else ""
        print(f" {c:<22} {n_t:>7} {vtypes:<40} {other_str}{marker}")

    if len(cases_mut) > 15:
        print(f" ... and {len(cases_mut) - 15} more")

# Summary for downloading
print(f"\n{'='*90}")
print("RECOMMENDED DOWNLOADS — slides with high tile count + confirmed mutation")
print("(more tiles = better WSI quality for LCHAI analysis)")
print("=" * 90)

for gene in GENES:
    cases_mut = []
    for c, gene_vars in case_gene_vars.items():
        if gene in gene_vars and c in slide_info:
            cases_mut.append((c, gene_vars[gene], slide_info[c]))
    cases_mut.sort(key=lambda x: -x[2]["n_tiles"])

    best = cases_mut[0] if cases_mut else None
    if best:
        c, v, s = best
        local_flag = "★ ALREADY LOCAL" if c in local_svs else "DOWNLOAD"
        print(f"  {gene:6s}: {c} (tiles={s['n_tiles']}, {', '.join(sorted(set(v)))}) [{local_flag}]")
        print(f"          slide_id: {s['slide_id']}")
    else:
        print(f"  {gene:6s}: no confirmed mutations in cohort")
