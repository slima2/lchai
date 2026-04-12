"""
SLIMA Zenodo overlay CORRECTED - 4 apr 2026
============================================
Fixes the ID_TO_CLASS mapping to match the official Zenodo ANORAK documentation.
Regenerates overlay_index.xlsx and overlay images with correct class names.

Previous (INCORRECT) mapping:
  {1:"lepidic", 2:"acinar", 3:"papillary", 4:"micropapillary", 5:"solid", 6:"mucinous"}

Correct mapping (from Zenodo website + pathologist verification):
  {1:"cribriform", 2:"micropapillary", 3:"solid", 4:"papillary", 5:"acinar", 6:"lepidic"}
"""

from pathlib import Path
from typing import Dict, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import loadmat
from scipy.ndimage import binary_dilation, binary_erosion
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

ROOT = Path(r"D:\Dropbox\PHD\ZENODO ANORAK")
IMAGES_DIR = ROOT / "image"
MASKS_DIR = ROOT / "mask"
OUT_DIR = ROOT / "overlays_corrected_4_apr_2026"

# ============================================================
# CORRECTED mapping (Zenodo official)
# ============================================================
ID_TO_CLASS: Dict[int, str] = {
    1: "cribriform",
    2: "micropapillary",
    3: "solid",
    4: "papillary",
    5: "acinar",
    6: "lepidic",
}

CLASS_COLORS: Dict[str, Tuple[int, int, int]] = {
    "cribriform":     (0, 255, 255),    # cyan (Zenodo official)
    "micropapillary": (255, 0, 255),    # magenta
    "solid":          (128, 0, 0),      # dark red
    "papillary":      (255, 255, 0),    # yellow
    "acinar":         (255, 0, 0),      # red
    "lepidic":        (0, 0, 255),      # blue
}

ALPHA = 110


def load_mat_mask(path: Path) -> np.ndarray:
    data = loadmat(str(path), squeeze_me=True)
    for key in ["mask", "Mask", "BW", "label", "seg"]:
        if key in data and isinstance(data[key], np.ndarray) and data[key].ndim >= 2:
            return data[key].astype(np.int32)
    for k, v in data.items():
        if not k.startswith("_") and isinstance(v, np.ndarray) and v.ndim >= 2:
            return v.astype(np.int32)
    raise RuntimeError(f"No mask found in {path}")


def make_overlay(img: Image.Image, label_map: np.ndarray) -> Image.Image:
    base = img.convert("RGBA")
    W, H = base.size
    lm = label_map
    if lm.shape != (H, W):
        lm = np.array(Image.fromarray(lm.astype(np.uint16)).resize((W, H), Image.NEAREST))

    overlay = np.zeros((H, W, 4), dtype=np.uint8)
    edges = np.zeros((H, W, 4), dtype=np.uint8)

    for cid, cname in ID_TO_CLASS.items():
        m = (lm == cid)
        if not np.any(m):
            continue
        r, g, b = CLASS_COLORS[cname]
        overlay[m] = (r, g, b, ALPHA)
        bd = binary_dilation(m) ^ binary_erosion(m)
        edges[bd] = (r, g, b, 255)

    out = Image.alpha_composite(base, Image.fromarray(overlay, "RGBA"))
    out = Image.alpha_composite(out, Image.fromarray(edges, "RGBA"))
    return out


def get_dominant_class(label_map: np.ndarray) -> Tuple[str, str, str, int, float]:
    total_pixels = label_map.size
    best_class = "none"
    best_color = ""
    best_rgb = ""
    best_pixels = 0
    best_pct = 0.0

    for cid, cname in ID_TO_CLASS.items():
        count = int(np.sum(label_map == cid))
        if count > best_pixels:
            best_pixels = count
            best_class = cname
            best_color = {
                "cribriform": "CYAN", "micropapillary": "MAGENTA",
                "solid": "DARK_RED", "papillary": "YELLOW",
                "acinar": "RED", "lepidic": "BLUE",
            }.get(cname, "")
            best_rgb = str(CLASS_COLORS.get(cname, ""))
            best_pct = round(100 * count / total_pixels, 3)

    if best_pixels == 0:
        return "none", "", "", 0, 0.0
    return best_class, best_color, best_rgb, best_pixels, best_pct


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    images = sorted(
        list(IMAGES_DIR.glob("*.png")) + list(IMAGES_DIR.glob("*.jpg"))
    )
    images = [p for p in images if "overlay" not in p.stem.lower()]

    logging.info(f"Found {len(images)} images")

    records = []
    ok = fail = 0

    for img_path in images:
        mat_path = MASKS_DIR / (img_path.stem + ".mat")
        if not mat_path.exists():
            logging.warning(f"No .mat for {img_path.name}")
            records.append({
                "overlay_file": "", "tile_id": img_path.stem,
                "pattern": "none", "color_name": "", "color_rgb": "",
                "pixels": 0, "area_pct": 0.0,
            })
            fail += 1
            continue

        try:
            lm = load_mat_mask(mat_path)
            img = Image.open(img_path)
            W, H = img.size
            if lm.shape != (H, W):
                if lm.shape == (W, H):
                    lm = lm.T
                else:
                    lm = np.array(
                        Image.fromarray(lm.astype(np.uint16)).resize((W, H), Image.NEAREST)
                    ).astype(np.int32)

            out_img = make_overlay(img, lm)
            out_path = OUT_DIR / f"{img_path.stem}_overlay.png"
            out_img.save(out_path)

            pat, color, rgb, pixels, pct = get_dominant_class(lm)
            records.append({
                "overlay_file": str(out_path),
                "tile_id": img_path.stem,
                "pattern": pat,
                "color_name": color,
                "color_rgb": rgb,
                "pixels": pixels,
                "area_pct": pct,
            })
            ok += 1

        except Exception as e:
            logging.exception(f"Error: {img_path.name}: {e}")
            fail += 1

    # Save corrected overlay index
    df = pd.DataFrame(records)
    xlsx_path = ROOT / "overlay_index_corrected_4_apr_2026.xlsx"
    df.to_excel(str(xlsx_path), index=False, sheet_name="overlay_index")
    logging.info(f"Saved {xlsx_path} ({len(df)} rows)")
    logging.info(f"OK: {ok}, Failed: {fail}")

    # Summary
    print("\n=== CLASS DISTRIBUTION (corrected) ===")
    dist = df[df["pattern"] != "none"]["pattern"].value_counts()
    for pat, count in dist.items():
        print(f"  {pat}: {count}")
    print(f"  none: {len(df[df['pattern'] == 'none'])}")
    print(f"  TOTAL: {len(df)}")


if __name__ == "__main__":
    main()
