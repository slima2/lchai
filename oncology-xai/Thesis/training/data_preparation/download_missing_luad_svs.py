#!/usr/bin/env python3
"""
Download missing TCGA-LUAD SVS whole-slide images from GDC API.
Reads luad_cases_missing_slides.txt (388 barcodes) and downloads
the corresponding SVS files into data/slides/<slide_id>/<slide_id>.svs

Run:
  nohup python3 download_missing_luad_svs.py > output_svs_download.txt 2>&1 &
  tail -f output_svs_download.txt
"""
import os, json, time, hashlib
from pathlib import Path

try:
    import requests
except ImportError:
    os.system("pip install requests --break-system-packages")
    import requests

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR      = Path("/home/rapids/notebooks/slima")
MISSING_FILE  = BASE_DIR / "TGCA MAF" / "luad_cases_missing_slides.txt"
SLIDES_DIR    = BASE_DIR / "data" / "slides"
LOG_FILE      = BASE_DIR / "TGCA MAF" / "svs_download_log.tsv"

GDC_FILES_URL = "https://api.gdc.cancer.gov/files"
GDC_DATA_URL  = "https://api.gdc.cancer.gov/data"
BATCH_SIZE    = 50    # cases per GDC query
TIMEOUT_DL    = 3600  # 1 hour per file max
RETRY_MAX     = 3

# ── Load missing barcodes ─────────────────────────────────────────────────────
with open(MISSING_FILE) as f:
    missing_barcodes = [l.strip() for l in f if l.strip()]
print(f"Missing LUAD cases to download: {len(missing_barcodes)}")

# ── Query GDC: barcode → (file_id, file_name, file_size) ─────────────────────
def query_svs_for_barcodes(barcodes):
    """Query GDC Files API for SVS files matching case barcodes."""
    filters = {
        "op": "and",
        "content": [
            {"op": "in",  "content": {"field": "cases.submitter_id",     "value": barcodes}},
            {"op": "=",   "content": {"field": "cases.project.project_id","value": "TCGA-LUAD"}},
            {"op": "in",  "content": {"field": "data_format",             "value": ["SVS"]}},
            {"op": "=",   "content": {"field": "data_type",               "value": "Slide Image"}},
            {"op": "=",   "content": {"field": "experimental_strategy",   "value": "Tissue Slide"}},
        ]
    }
    params = {
        "filters": json.dumps(filters),
        "fields": "file_id,file_name,file_size,cases.submitter_id,cases.case_id",
        "size": len(barcodes) * 3,   # some cases have multiple slides
    }
    r = requests.get(GDC_FILES_URL, params=params, timeout=60)
    r.raise_for_status()
    return r.json()["data"]["hits"]

# ── Collect all file metadata in batches ─────────────────────────────────────
print("\nQuerying GDC for SVS file IDs...")
all_hits = []
for i in range(0, len(missing_barcodes), BATCH_SIZE):
    batch = missing_barcodes[i:i+BATCH_SIZE]
    batch_n = i // BATCH_SIZE + 1
    total_b = (len(missing_barcodes) + BATCH_SIZE - 1) // BATCH_SIZE
    try:
        hits = query_svs_for_barcodes(batch)
        all_hits.extend(hits)
        print(f"  Batch {batch_n}/{total_b}: found {len(hits)} SVS files", flush=True)
    except Exception as e:
        print(f"  Batch {batch_n}/{total_b}: query failed — {e}", flush=True)
    time.sleep(0.5)

print(f"\nTotal SVS files found: {len(all_hits)}")

# Deduplicate: one SVS per case (prefer DX1 diagnostic slide)
case_to_files = {}
for h in all_hits:
    case_ids = [c["submitter_id"] for c in h.get("cases", [])]
    for case_id in case_ids:
        if case_id not in case_to_files:
            case_to_files[case_id] = []
        case_to_files[case_id].append(h)

# Select best SVS per case: prefer DX (diagnostic) over others
def pick_best(files):
    dx = [f for f in files if "DX" in f["file_name"].upper()]
    return dx[0] if dx else files[0]

selected = []
for case_id, files in case_to_files.items():
    best = pick_best(files)
    selected.append((case_id, best["file_id"], best["file_name"],
                     best.get("file_size", 0)))

total_gb = sum(s for _, _, _, s in selected) / 1e9
print(f"Cases with SVS found : {len(selected)}")
print(f"Estimated total size : {total_gb:.1f} GB")
cases_without_svs = set(missing_barcodes) - set(case_to_files.keys())
if cases_without_svs:
    print(f"Cases with NO SVS in GDC: {len(cases_without_svs)} (will be skipped)")

# ── Setup log file ────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
if not LOG_FILE.exists():
    with open(LOG_FILE, "w") as lf:
        lf.write("case_id\tfile_id\tfile_name\tfile_size_mb\tstatus\tslide_dir\n")

# Read already-downloaded from log
done_file_ids = set()
if LOG_FILE.exists():
    with open(LOG_FILE) as lf:
        for line in lf:
            if "\tOK\t" in line:
                parts = line.strip().split("\t")
                if len(parts) >= 2:
                    done_file_ids.add(parts[1])

remaining = [(c, fid, fn, sz) for c, fid, fn, sz in selected
             if fid not in done_file_ids]
print(f"\nAlready downloaded    : {len(done_file_ids)}")
print(f"Remaining to download : {len(remaining)}")

# ── Download function ─────────────────────────────────────────────────────────
def download_file(file_id, dest_path, file_size_bytes=0):
    """Stream-download a single file from GDC data endpoint."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Skip if already complete
    if dest_path.exists():
        if file_size_bytes and dest_path.stat().st_size >= file_size_bytes * 0.99:
            return "already_exists"

    url = f"{GDC_DATA_URL}/{file_id}"
    for attempt in range(1, RETRY_MAX + 1):
        try:
            with requests.get(url, stream=True, timeout=TIMEOUT_DL) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                tmp = dest_path.with_suffix(".tmp")
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):  # 8MB chunks
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                tmp.rename(dest_path)
                return "ok"
        except Exception as e:
            print(f"    Attempt {attempt}/{RETRY_MAX} failed: {e}", flush=True)
            if attempt < RETRY_MAX:
                time.sleep(10 * attempt)
    return "failed"

# ── Main download loop ────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  STARTING SVS DOWNLOADS")
print("=" * 65)

ok_count   = len(done_file_ids)
fail_count = 0
skip_count = 0

for idx, (case_id, file_id, file_name, file_size) in enumerate(remaining, 1):
    size_mb = file_size / 1e6 if file_size else 0
    pct_done = (ok_count) / len(selected) * 100

    # Destination: data/slides/<file_name_without_ext>/<file_name>
    # Use the SVS filename (without .svs) as the slide folder name
    slide_id  = file_name.replace(".svs", "").replace(".SVS", "")
    slide_dir = SLIDES_DIR / slide_id
    dest_path = slide_dir / file_name

    print(f"\n  [{idx}/{len(remaining)}] {file_name}  ({size_mb:.0f} MB)  "
          f"[{pct_done:.1f}% done overall]", flush=True)

    status = download_file(file_id, dest_path, file_size)

    if status == "ok" or status == "already_exists":
        ok_count += 1
        log_status = "OK"
        print(f"    ✓ {status}", flush=True)
    else:
        fail_count += 1
        log_status = "FAILED"
        print(f"    ✗ FAILED", flush=True)

    with open(LOG_FILE, "a") as lf:
        lf.write(f"{case_id}\t{file_id}\t{file_name}\t{size_mb:.1f}\t"
                 f"{log_status}\t{slide_dir}\n")

    # Progress summary every 10 files
    if idx % 10 == 0:
        elapsed_est = idx  # just a counter for now
        print(f"\n  ── Progress: {ok_count} OK, {fail_count} failed "
              f"of {len(selected)} total ──", flush=True)

# ── Final summary ─────────────────────────────────────────────────────────────
print(f"\n{'=' * 65}")
print(f"  DOWNLOAD COMPLETE")
print(f"{'=' * 65}")
print(f"  Successfully downloaded : {ok_count}")
print(f"  Failed                  : {fail_count}")
print(f"  Log saved to            : {LOG_FILE}")
print(f"  Slides directory        : {SLIDES_DIR}")
print(f"\n  NEXT STEPS:")
print(f"  1. Run tile extraction + FuzzyArcLoss on new slides")
print(f"     (pattern_probs.npy for each new slide)")
print(f"  2. Run embedding extraction (embeddings.npy)")
print(f"  3. Re-run benchmark with LUAD-only cohort (~557 slides)")
print(f"{'=' * 65}")
