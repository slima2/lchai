#!/usr/bin/env python3
"""
add_pattern_names_to_tile_predictions.py
========================================
The per-slide tile inference CSVs of FuzzyArcLoss V2 on TCGA
(``TCGA-*_tiles_384_predictions.csv``, columns ``x,y,pred_class``) store the
model output index 0-5 only.  This script appends a ``pattern`` column with the
ANORAK class name of that index and writes a
sidecar ``pred_class_to_pattern.json`` next to the files.

Index -> class (fixed class index order of the trained checkpoints):
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
    side = args.dir / "pred_class_to_pattern.json"
    if not args.dry_run:
        side.write_text(json.dumps({
            "note": "pred_class index -> ANORAK pattern name. This is the fixed class index order of the trained checkpoints (not alphabetical).",
            "pred_class_to_pattern": ID2PATTERN,
        }, indent=2) + "\n")
    print(f"files={len(files)}  annotated={done}  skipped(already)={skipped}  rows={rows}  sidecar={side}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
