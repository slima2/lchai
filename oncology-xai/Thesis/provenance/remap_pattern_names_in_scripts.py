#!/usr/bin/env python3
"""
remap_pattern_names_in_scripts.py
=================================
Apply the 4 April 2026 ANORAK pattern-name correction to *source files*
(.py / .ipynb) that still carry the legacy class names.  Same one-pass
permutation as remap_pattern_names_4apr2026.py (imported from it):

    acinar->micropapillary, lepidic->cribriform, micropapillary->papillary,
    mucinous->lepidic, papillary->solid, solid->acinar

What is changed
---------------
* every legacy pattern token (also inside identifiers such as pct_acinar,
  SOLID_CLASS_BOOST, prob_mucinous) is renamed; numeric values untouched;
* a provenance comment is inserted after the shebang / encoding line
  (.py) or in notebook metadata (.ipynb) -> idempotent;
* with --fix-class-order (Artefact-1 training scripts):
    - the default XLS_PATH is pointed to overlay_index.xlsx;
    - `labels = sorted(...)` / `classes = sorted(...)` is replaced by a sort
      that keeps the ORIGINAL class-index order of the trained models
      (alphabetical order of the legacy names, i.e. CLASS_ORDER in
      true names).  Positional per-class parameters (class_tau / class_margin /
      class_scale) and checkpoint output indices therefore keep their meaning.

Usage
-----
  python remap_pattern_names_in_scripts.py --dry-run  FILE [...]
  python remap_pattern_names_in_scripts.py --inplace  FILE [...]
  python remap_pattern_names_in_scripts.py --inplace --fix-class-order training/artefact1_pattern_classifier/*.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from remap_pattern_names_4apr2026 import LEGACY_TO_TRUE, PROVENANCE_KEY, PROVENANCE_VAL, TEXT_MARKER, remap_text  # noqa: E402

# true names in the index order used by every trained model / result file
# (index i == position of the legacy name in alphabetical order)
CLASS_ORDER = [LEGACY_TO_TRUE[k] for k in sorted(LEGACY_TO_TRUE)]
# -> ['micropapillary', 'cribriform', 'papillary', 'lepidic', 'solid', 'acinar']

CLASS_ORDER_BLOCK = (
    "# [4-APR-2026] true ANORAK class names in the ORIGINAL index order of the trained models\n"
    "# (= alphabetical order of the legacy names). Used to keep label2id stable.\n"
    f"CLASS_ORDER = {CLASS_ORDER!r}\n"
)

_SORTED_RE = re.compile(r"^(?P<ind>[ \t]*)(?P<var>labels|classes) = sorted\((?P<inner>.+)\)[ \t]*$", re.M)
_XLS_RE = re.compile(r"overlay_index ver \d+ nov 2025\.xlsx")
XLS_NEW = "overlay_index.xlsx"


def _fix_class_order(text: str) -> tuple[str, int]:
    n_xls = len(_XLS_RE.findall(text))
    text = _XLS_RE.sub(XLS_NEW, text)

    def _sub(m: re.Match) -> str:
        ind, var, inner = m.group("ind"), m.group("var"), m.group("inner")
        return (
            f"{ind}# [4-APR-2026] keep the original class-index order of the trained models;\n"
            f"{ind}# sorted() over the corrected names would shuffle the indices.\n"
            f"{ind}{var} = sorted({inner}, key=lambda _c: (CLASS_ORDER.index(str(_c).lower())\n"
            f"{ind}{' ' * (len(var) + 3)}      if str(_c).lower() in CLASS_ORDER else 99, str(_c)))"
        )

    text, n_sorted = _SORTED_RE.subn(_sub, text)
    return text, n_xls + n_sorted


def _insert_header(text: str, extra: str = "") -> str:
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].startswith("#!") or re.match(r"#.*coding[:=]", lines[i])):
        i += 1
    return "".join(lines[:i]) + TEXT_MARKER + extra + "".join(lines[i:])


def process_py(path: Path, fix_class_order: bool) -> tuple[str | None, int | str]:
    raw = path.read_text(encoding="utf-8", errors="surrogateescape")
    if TEXT_MARKER.strip() in raw:
        return None, "already-corrected"
    new, n = remap_text(raw)
    extra = ""
    if fix_class_order:
        new, k = _fix_class_order(new)
        n += k
        extra = CLASS_ORDER_BLOCK
    if not n:
        return None, 0
    return _insert_header(new, extra), n


def process_ipynb(path: Path) -> tuple[str | None, int | str]:
    nb = json.loads(path.read_text(encoding="utf-8"))
    if PROVENANCE_KEY in nb.get("metadata", {}):
        return None, "already-corrected"
    n = 0
    for cell in nb.get("cells", []):
        src = cell.get("source", "")
        joined = "".join(src) if isinstance(src, list) else src
        new, k = remap_text(joined)
        if k:
            n += k
            cell["source"] = new.splitlines(keepends=True) if isinstance(src, list) else new
        # outputs (printed tables, plots' text) are remapped too
        for out in cell.get("outputs", []) or []:
            for key in ("text",):
                if key in out:
                    t = out[key]
                    j = "".join(t) if isinstance(t, list) else t
                    nt, k2 = remap_text(j)
                    if k2:
                        n += k2
                        out[key] = nt.splitlines(keepends=True) if isinstance(t, list) else nt
            data = out.get("data", {}) or {}
            for mime in ("text/plain", "text/html"):
                if mime in data:
                    t = data[mime]
                    j = "".join(t) if isinstance(t, list) else t
                    nt, k2 = remap_text(j)
                    if k2:
                        n += k2
                        data[mime] = nt.splitlines(keepends=True) if isinstance(t, list) else nt
    if not n:
        return None, 0
    nb.setdefault("metadata", {})[PROVENANCE_KEY] = PROVENANCE_VAL
    return json.dumps(nb, indent=1, ensure_ascii=False) + "\n", n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--inplace", action="store_true")
    g.add_argument("--dry-run", action="store_true")
    ap.add_argument("--fix-class-order", action="store_true",
                    help="Artefact-1 scripts: stable class order + corrected XLS path")
    args = ap.parse_args()

    changed = total = 0
    for f in map(Path, args.files):
        if not f.is_file():
            print(f"[skip] not found: {f}", file=sys.stderr)
            continue
        if f.suffix == ".py":
            new, n = process_py(f, args.fix_class_order)
        elif f.suffix == ".ipynb":
            new, n = process_ipynb(f)
        else:
            print(f"[skip] unsupported: {f}", file=sys.stderr)
            continue
        if n == "already-corrected":
            print(f"[  skip   ] already corrected: {f}")
            continue
        if not n:
            print(f"[   0 subs] {f}")
            continue
        changed += 1
        total += n
        print(f"[{n:4d} subs] {f}")
        if args.inplace:
            f.write_text(new, encoding="utf-8", errors="surrogateescape")
    print(f"\nchanged={changed}  substitutions={total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
