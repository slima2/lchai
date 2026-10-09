"""
PATTERN_REMAP_4_apr_2026.py
===========================
Reference file documenting the correction of the pattern class mapping.

The original ID_TO_CLASS in the overlay generation notebook was INCORRECT.
This file documents the corrected mapping and provides the remapping
constants needed to fix LCHAI and the thesis.

Verified by histopathologist on 4 April 2026 (blind review of 6 tiles).
"""

# ============================================================
# ORIGINAL (INCORRECT) mapping used in training
# ============================================================
# The overlay_index.xlsx used for training had these wrong names:
WRONG_ID_TO_CLASS = {
    1: "lepidic",        # WRONG: .mat label 1 = cribriform (Zenodo)
    2: "acinar",         # WRONG: .mat label 2 = micropapillary
    3: "papillary",      # WRONG: .mat label 3 = solid
    4: "micropapillary", # WRONG: .mat label 4 = papillary
    5: "solid",          # WRONG: .mat label 5 = acinar
    6: "mucinous",       # WRONG: .mat label 6 = lepidic
}

# Training sorted these alphabetically → model output indices 0-5:
WRONG_ID2LABEL = {
    0: "acinar",         # trained on .mat label 2 tiles
    1: "lepidic",        # trained on .mat label 1 tiles
    2: "micropapillary", # trained on .mat label 4 tiles
    3: "mucinous",       # trained on .mat label 6 tiles
    4: "papillary",      # trained on .mat label 3 tiles
    5: "solid",          # trained on .mat label 5 tiles
}

# ============================================================
# CORRECT mapping (Zenodo ANORAK official + pathologist verified)
# ============================================================
CORRECT_ANORAK_LABELS = {
    0: "background",
    1: "cribriform",
    2: "micropapillary",
    3: "solid",
    4: "papillary",
    5: "acinar",
    6: "lepidic",
}

# Model output index → correct class name
CORRECTED_ID2LABEL = {
    0: "micropapillary",  # model idx 0 was trained on .mat label 2
    1: "cribriform",      # model idx 1 was trained on .mat label 1
    2: "papillary",       # model idx 2 was trained on .mat label 4
    3: "lepidic",         # model idx 3 was trained on .mat label 6
    4: "solid",           # model idx 4 was trained on .mat label 3
    5: "acinar",          # model idx 5 was trained on .mat label 5
}

# Permutation: old_name → correct_name
NAME_REMAP = {
    "acinar":         "micropapillary",
    "lepidic":        "cribriform",
    "micropapillary": "papillary",
    "mucinous":       "lepidic",
    "papillary":      "solid",
    "solid":          "acinar",
}

# Colors (Zenodo official RGB)
CORRECTED_COLORS = {
    "cribriform":     (0, 255, 255),    # cyan
    "micropapillary": (255, 0, 255),    # magenta
    "solid":          (128, 0, 0),      # dark red
    "papillary":      (255, 255, 0),    # yellow
    "acinar":         (255, 0, 0),      # red
    "lepidic":        (0, 0, 255),      # blue
}

# Corrected class distribution (from 637 usable tiles after excluding
# none=94 tiles; cribriform IS included in the corrected taxonomy)
CORRECTED_DISTRIBUTION = {
    "acinar":         181,  # was incorrectly called "solid" (208 in old count due to different tile selection)
    "papillary":      125,
    "solid":          107,
    "lepidic":         86,
    "micropapillary":  69,
    "cribriform":      69,
    # Total: 637
}
