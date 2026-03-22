"""Download recommended SVS files from GDC for LCHAI demo."""

import requests
import os
import time
from pathlib import Path

DEST_DIR = Path(r"D:\Dropbox\PHD\THESIS\BEST MUTATION SAMPLES")

CASES_TO_DOWNLOAD = [
    {"case": "TCGA-86-8280", "genes": ["TP53", "EGFR", "STK11"], "label": "TP53+EGFR+STK11 triple mutant"},
    {"case": "TCGA-69-7980", "genes": ["KRAS"], "label": "KRAS+TP53"},
    {"case": "TCGA-49-4506", "genes": ["KEAP1"], "label": "KEAP1"},
    {"case": "TCGA-78-7148", "genes": ["RBM10"], "label": "RBM10+KRAS+STK11"},
]

GDC_FILES_ENDPOINT = "https://api.gdc.cancer.gov/files"
GDC_DATA_ENDPOINT = "https://api.gdc.cancer.gov/data/"


def find_svs_file(case_submitter_id):
    """Search GDC for the diagnostic SVS slide of a given case."""
    filters = {
        "op": "and",
        "content": [
            {"op": "=", "content": {"field": "cases.submitter_id", "value": case_submitter_id}},
            {"op": "=", "content": {"field": "data_format", "value": "SVS"}},
            {"op": "=", "content": {"field": "experimental_strategy", "value": "Diagnostic Slide"}},
        ]
    }
    params = {
        "filters": str(filters).replace("'", '"'),
        "fields": "file_id,file_name,file_size,access,data_type",
        "size": 5,
    }
    r = requests.get(GDC_FILES_ENDPOINT, params=params, timeout=15)
    if r.status_code != 200:
        print(f"  GDC API error: {r.status_code}")
        return None

    hits = r.json().get("data", {}).get("hits", [])
    if not hits:
        # Try Tissue Slide instead
        filters["content"][2] = {"op": "=", "content": {"field": "experimental_strategy", "value": "Tissue Slide"}}
        params["filters"] = str(filters).replace("'", '"')
        r = requests.get(GDC_FILES_ENDPOINT, params=params, timeout=15)
        hits = r.json().get("data", {}).get("hits", [])

    if not hits:
        # Broader search: any SVS for this case
        filters = {
            "op": "and",
            "content": [
                {"op": "=", "content": {"field": "cases.submitter_id", "value": case_submitter_id}},
                {"op": "=", "content": {"field": "data_format", "value": "SVS"}},
            ]
        }
        params["filters"] = str(filters).replace("'", '"')
        r = requests.get(GDC_FILES_ENDPOINT, params=params, timeout=15)
        hits = r.json().get("data", {}).get("hits", [])

    return hits


def download_file(file_id, dest_path, expected_size=0):
    """Stream-download a file from GDC."""
    url = f"{GDC_DATA_ENDPOINT}{file_id}"
    r = requests.get(url, stream=True, timeout=30)
    r.raise_for_status()

    total = int(r.headers.get("Content-Length", 0)) or expected_size
    downloaded = 0
    start = time.time()

    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            downloaded += len(chunk)
            elapsed = time.time() - start
            speed = downloaded / (1024 * 1024 * max(elapsed, 0.1))
            if total > 0:
                pct = downloaded / total * 100
                eta = (total - downloaded) / (downloaded / max(elapsed, 0.1))
                print(f"\r  {downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB ({pct:.1f}%) - {speed:.1f} MB/s - ETA {eta:.0f}s   ", end="", flush=True)
            else:
                print(f"\r  {downloaded/(1024*1024):.1f} MB - {speed:.1f} MB/s   ", end="", flush=True)

    print(f"\n  Done! {downloaded/(1024*1024):.1f} MB in {time.time()-start:.0f}s")


def main():
    print("=" * 70)
    print("GDC SVS Downloader for LCHAI Demo")
    print("=" * 70)

    for entry in CASES_TO_DOWNLOAD:
        case = entry["case"]
        genes = entry["genes"]
        label = entry["label"]

        print(f"\n--- {case} ({label}) ---")

        # Check if already downloaded
        primary_gene = genes[0]
        existing = list((DEST_DIR / primary_gene).glob(f"{case}*.svs"))
        if existing:
            print(f"  Already exists: {existing[0].name} ({existing[0].stat().st_size/(1024*1024):.1f} MB)")
            continue

        # Search GDC
        print(f"  Searching GDC for {case} SVS files...")
        hits = find_svs_file(case)

        if not hits:
            print(f"  NOT FOUND on GDC!")
            continue

        # Pick best hit (prefer DX diagnostic slides)
        best = None
        for h in hits:
            fname = h.get("file_name", "")
            if "DX" in fname.upper():
                best = h
                break
        if not best:
            best = hits[0]

        file_id = best["file_id"]
        fname = best["file_name"]
        fsize = best.get("file_size", 0)
        access = best.get("access", "unknown")

        print(f"  Found: {fname} ({fsize/(1024*1024):.1f} MB, access={access})")
        print(f"  File ID: {file_id}")

        if access != "open":
            print(f"  WARNING: Controlled access - needs GDC token!")
            continue

        dest_path = DEST_DIR / primary_gene / fname
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"  Downloading...")
        try:
            download_file(file_id, dest_path, fsize)
        except Exception as e:
            print(f"  ERROR downloading: {e}")
            if dest_path.exists():
                dest_path.unlink()
            continue

        # Link to other gene folders
        for extra_gene in genes[1:]:
            extra_dest = DEST_DIR / extra_gene / fname
            extra_dest.parent.mkdir(parents=True, exist_ok=True)
            if not extra_dest.exists():
                try:
                    os.link(str(dest_path), str(extra_dest))
                    print(f"  Linked -> {extra_gene}/{fname}")
                except OSError:
                    import shutil
                    shutil.copy2(str(dest_path), str(extra_dest))
                    print(f"  Copied -> {extra_gene}/{fname}")

    # Summary
    print(f"\n{'='*70}")
    print("Summary: BEST MUTATION SAMPLES")
    print(f"{'='*70}")
    for gene_dir in sorted(DEST_DIR.iterdir()):
        if gene_dir.is_dir():
            svs = list(gene_dir.glob("*.svs"))
            print(f"\n  {gene_dir.name}/")
            for f in svs:
                print(f"    {f.name} ({f.stat().st_size/(1024*1024):.1f} MB)")
            if not svs:
                print(f"    (empty)")


if __name__ == "__main__":
    main()
