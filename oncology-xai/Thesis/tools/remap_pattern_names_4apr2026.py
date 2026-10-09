#!/usr/bin/env python3
"""
remap_pattern_names_4apr2026.py
===============================
Apply the 4 April 2026 ANORAK pattern-name correction to result files
(JSON / TXT / CSV) that were produced BEFORE the correction.

Background
----------
The overlay_index.xlsx used to train FuzzyArcLoss V2 carried a permuted set
of class names.  The model, its 6 output indices, and every downstream result
(ABMIL / Choquet metrics, XGBoost feature importances, per-class F1 of the
pattern classifier) are unchanged; only the *names* attached to each index
were wrong.  The correction was verified by a histopathologist on 4 Apr 2026
(see overlay_index_corrected_4_apr_2026.xlsx and PATTERN_REMAP_4_apr_2026.py).

Legacy name (pre-4-Apr)  ->  True ANORAK class
    acinar               ->  micropapillary
    lepidic              ->  cribriform
    micropapillary       ->  papillary
    mucinous             ->  lepidic
    papillary            ->  solid
    solid                ->  acinar

The mapping is a permutation, so it is applied in ONE simultaneous pass
(never sequentially, which would chain substitutions).

Usage
-----
  # rewrite files in place (make a backup first!)
  python remap_pattern_names_4apr2026.py --inplace FILE_OR_DIR [...]

  # write corrected copies under OUT, preserving the relative layout
  python remap_pattern_names_4apr2026.py --out OUT_DIR FILE_OR_DIR [...]

  # report only
  python remap_pattern_names_4apr2026.py --dry-run FILE_OR_DIR [...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

LEGACY_TO_TRUE = {
    "acinar": "micropapillary",
    "lepidic": "cribriform",
    "micropapillary": "papillary",
    "mucinous": "lepidic",
    "papillary": "solid",
    "solid": "acinar",
}

# 8-character column headers used by the K-fold statistical log
# ("micropap" = micropapillary, "papillar" = papillary).
TRUNCATED = {
    "micropap": "papillary",
    "papillar": "solid",
}

PROVENANCE_KEY = "_pattern_names_corrected_4_apr_2026"
PROVENANCE_VAL = (
    "Pattern names remapped from the legacy (pre-4-Apr-2026) labels to the "
    "verified ANORAK classes; numeric values untouched. "
    "Mapping: " + ", ".join(f"{k}->{v}" for k, v in LEGACY_TO_TRUE.items())
)

TEXT_MARKER = (
    "# [PATTERN NAMES CORRECTED 4-APR-2026] legacy->true: acinar->micropapillary, "
    "lepidic->cribriform, micropapillary->papillary, mucinous->lepidic, "
    "papillary->solid, solid->acinar (numeric values untouched)\n"
)

# Alphabetic boundaries (not \b): underscores/digits must count as separators so
# that tokens such as "pct_acinar", "prob_mucinous" or "n_solid" are remapped too.
_WORD_RE = re.compile(
    r"(?<![A-Za-z])(" + "|".join(sorted(list(LEGACY_TO_TRUE) + list(TRUNCATED), key=len, reverse=True)) + r")(?![A-Za-z])",
    re.IGNORECASE,
)
_PAIR_SEP = ("×", "x", "_x_", "*")


def _match_case(src: str, dst: str) -> str:
    if src.isupper():
        return dst.upper()
    if src[0].isupper():
        return dst.capitalize()
    return dst


def remap_text(text: str) -> tuple[str, int]:
    n = 0

    def _sub(m: re.Match) -> str:
        nonlocal n
        tok = m.group(0)
        low = tok.lower()
        new = LEGACY_TO_TRUE.get(low) or TRUNCATED.get(low)
        if new is None:
            return tok
        n += 1
        return _match_case(tok, new)

    return _WORD_RE.sub(_sub, text), n


def _remap_name(s: str) -> str | None:
    """Return the remapped string if *s* is a pattern name or a pattern pair."""
    low = s.lower()
    if low in LEGACY_TO_TRUE:
        return _match_case(s, LEGACY_TO_TRUE[low])
    for sep in _PAIR_SEP:
        if sep in s:
            parts = s.split(sep)
            if len(parts) == 2 and all(p.strip().lower() in LEGACY_TO_TRUE for p in parts):
                return sep.join(_match_case(p.strip(), LEGACY_TO_TRUE[p.strip().lower()]) for p in parts)
    return None


def remap_json(obj: Any) -> tuple[Any, int]:
    n = 0

    def _walk(o: Any) -> Any:
        nonlocal n
        if isinstance(o, dict):
            out = {}
            for k, v in o.items():
                nk = _remap_name(k) if isinstance(k, str) else None
                if nk is not None:
                    n += 1
                    k = nk
                out[k] = _walk(v)
            return out
        if isinstance(o, list):
            return [_walk(v) for v in o]
        if isinstance(o, str):
            ns = _remap_name(o)
            if ns is not None:
                n += 1
                return ns
        return o

    new = _walk(obj)
    if n and isinstance(new, dict) and PROVENANCE_KEY not in new:
        new[PROVENANCE_KEY] = PROVENANCE_VAL
    return new, n


ALREADY = "already-corrected"


def process_file(path: Path) -> tuple[str | None, int | str]:
    """Return (new_text, n_subs). n_subs == ALREADY when the file carries a
    correction marker and must not be touched again (the mapping is a
    permutation, so a second pass would scramble the names)."""
    raw = path.read_text(encoding="utf-8", errors="surrogateescape")
    if path.suffix.lower() == ".json":
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            if TEXT_MARKER.strip() in raw:
                return None, ALREADY
            new, n = remap_text(raw)
            return (new if n else None), n
        if isinstance(obj, dict) and PROVENANCE_KEY in obj:
            return None, ALREADY
        new_obj, n = remap_json(obj)
        if not n:
            return None, 0
        return json.dumps(new_obj, indent=2, ensure_ascii=False) + "\n", n
    if TEXT_MARKER.strip() in raw:
        return None, ALREADY
    new, n = remap_text(raw)
    if not n:
        return None, 0
    # CSV/TSV must stay machine-readable: no header comment (tracked via manifest only)
    if path.suffix.lower() not in (".csv", ".tsv"):
        new = TEXT_MARKER + new
    return new, n


def load_manifest(p: Path) -> set[str]:
    if p and p.exists():
        return set(json.loads(p.read_text()).get("processed", []))
    return set()


def save_manifest(p: Path, done: set[str]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"mapping": LEGACY_TO_TRUE, "processed": sorted(done)}, indent=2) + "\n")


def iter_files(targets: list[str], exts: set[str]):
    for t in targets:
        p = Path(t)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in exts:
                    yield f
        elif p.is_file():
            yield p
        else:
            print(f"[skip] not found: {p}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="files or directories")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--inplace", action="store_true", help="overwrite files in place")
    g.add_argument("--out", type=Path, help="write corrected copies under this directory")
    g.add_argument("--dry-run", action="store_true", help="report only")
    ap.add_argument("--ext", default=".json,.txt,.csv,.log,.md,.tsv",
                    help="comma-separated extensions scanned inside directories")
    ap.add_argument("--base", type=Path, default=None,
                    help="base directory used to compute relative paths for --out (default: cwd)")
    ap.add_argument("--manifest", type=Path, default=None,
                    help="JSON manifest of already-processed files (skipped on later runs)")
    args = ap.parse_args()

    exts = {e.strip().lower() for e in args.ext.split(",") if e.strip()}
    base = (args.base or Path.cwd()).resolve()
    done = load_manifest(args.manifest) if args.manifest else set()
    changed = scanned = skipped = total_subs = 0
    for f in iter_files(args.targets, exts):
        scanned += 1
        key = str(f.resolve())
        if key in done:
            skipped += 1
            continue
        new, n = process_file(f)
        if n == ALREADY:
            skipped += 1
            print(f"[  skip   ] already corrected: {f}")
            continue
        if not n:
            if args.out:
                dst = args.out / f.resolve().relative_to(base)
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(f.read_bytes())
            continue
        changed += 1
        total_subs += n
        print(f"[{n:4d} subs] {f}")
        if args.dry_run:
            continue
        if args.inplace:
            f.write_text(new, encoding="utf-8", errors="surrogateescape")
            done.add(key)
        else:
            dst = args.out / f.resolve().relative_to(base)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new, encoding="utf-8", errors="surrogateescape")
    if args.manifest and args.inplace and not args.dry_run:
        save_manifest(args.manifest, done)
    print(f"\nscanned={scanned}  changed={changed}  skipped(already)={skipped}  substitutions={total_subs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
