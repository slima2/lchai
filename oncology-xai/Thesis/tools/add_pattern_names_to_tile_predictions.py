#!/usr/bin/env python3
"""
add_pattern_names_to_tile_predictions.py
========================================
The per-slide tile inference CSVs of FuzzyArcLoss V2 on TCGA
(``TCGA-*_tiles_384_predictions.csv``, columns ``x,y,pred_class``) store the
model output index 0-5 only.  This script appends a ``pattern`` column with the
TRUE ANORAK class name of that index (4-Apr-2026 correction) and writes a
sidecar ``pred_class_to_pattern_4apr2026.json`` next to the files.

Index -> true class (= CORRECTED_ID2LABEL in PATTERN_REMAP_4_apr_2026.py):
    0 micropapillary, 1 cribriform, 2 papillary, 3 lepidic, 4 solid, 5 acinar

Idempotent: files that already have a ``pattern`` column are skipped.

Usage:  python add_pattern_names_to_tile_predictions.py DIR [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ID2PATTERN = {0: "micropapillary", 1: "cribriform", 2: "papillary", 3: "lepidic", 4: "solid", 5: "acinar"}
LEGACY_ID2LABEL = {0: "acinar", 1: "lepidic", 2: "micropapillary", 3: "mucinous", 4: "papillary", 5: "solid"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("--glob", default="*_tiles_384_predictions.csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(args.dir.glob(args.glob))
    done = skipped = rows = 0
    for f in files:
        with open(f, newline="") as fh:
            rdr = csv.reader(fh)
            header = next(rdr)
            if "pattern" in header:
                skipped += 1
                continue
            if "pred_class" not in header:
                print(f"[skip] no pred_class column: {f.name}", file=sys.stderr)
                continue
            ci = header.index("pred_class")
            body = list(rdr)
        out = [header + ["pattern"]] + [r + [ID2PATTERN[int(r[ci])]] for r in body]
        rows += len(body)
        done += 1
        if args.dry_run:
            continue
        with open(f, "w", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerows(out)  # keep the original LF endings
    side = args.dir / "pred_class_to_pattern_4apr2026.json"
    if not args.dry_run:
        side.write_text(json.dumps({
            "note": "pred_class index -> TRUE ANORAK class (4-Apr-2026 correction). "
                    "The legacy name attached to each index before the correction is given for reference.",
            "pred_class_to_pattern": ID2PATTERN,
            "legacy_name_before_4_apr_2026": LEGACY_ID2LABEL,
        }, indent=2) + "\n")
    print(f"files={len(files)}  annotated={done}  skipped(already)={skipped}  rows={rows}  sidecar={side}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
