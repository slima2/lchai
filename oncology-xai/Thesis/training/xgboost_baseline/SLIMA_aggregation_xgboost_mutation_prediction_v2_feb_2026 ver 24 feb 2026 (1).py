#!/usr/bin/env python3
"""
SLIMA Aggregation + XGBoost Mutation Prediction (Feb 2026)
============================================================
PIPELINE:
  1. Aggregate tile CSVs → slide-level morphologic profiles
  2. Link profiles to TCGA mutation labels (GDC MAF)
  3. Train XGBoost per gene (EGFR, TP53, KRAS, KEAP1, STK11, NF1)
  4. Generate SHAP plots (bar, beeswarm, force)
  5. Compare to previous results (old V1/ResNet50 profiles)

INPUT:
  Tile CSVs from inference v6: {slide_name}_tiles_512_v2.csv
  Each CSV has: x, y, pred_class, pred_label, prob_acinar, ..., prob_solid

OUTPUT:
  - morphologic_profiles_v2.csv (slide-level features)
  - xgboost_mutation_results_v2.json (per-gene metrics)
  - SHAP plots per gene (bar, beeswarm, force)
  - Comparison table: old vs new profiles

FEATURE VECTOR (per thesis §4.5):
  pct_acinar, pct_lepidic, pct_micropapillary, pct_mucinous,
  pct_papillary, pct_solid, n_tiles_total
"""

import os, sys, json, warnings
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["OMP_NUM_THREADS"] = "4"

import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')


# ============================================================
# CONFIGURATION
# ============================================================

# Tile CSV directory (output of inference v6)
TILE_CSV_DIR = "/home/rapids/notebooks/slima/outputs/inference_results_v2_ctranspath_fast"

# Output directory
OUT_DIR = "/home/rapids/notebooks/slima/outputs/mutation_prediction_v2"

# TCGA mutation data (MAF file — will download if not present)
MAF_PATH = "/home/rapids/notebooks/slima/TGCA MAF/cohortMAF.2025-11-16 only LUAD.maf"
# Alternative: pre-processed mutation labels CSV
MUTATION_LABELS_PATH = "/home/rapids/notebooks/slima/data/tcga_luad_mutation_labels.csv"

# Genes to predict
GENES = ["EGFR", "TP53", "KRAS", "KEAP1", "STK11", "NF1"]

# Pattern classes (must match inference output)
PATTERNS = ["acinar", "lepidic", "micropapillary", "mucinous", "papillary", "solid"]

# XGBoost settings
XGBOOST_PARAMS = {
    'max_depth': 4,
    'learning_rate': 0.1,
    'n_estimators': 200,
    'objective': 'binary:logistic',
    'eval_metric': 'logloss',
    'use_label_encoder': False,
    'random_state': 42,
    'scale_pos_weight': 1,  # Will be computed per gene
}

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# STEP 1: AGGREGATE TILE CSVs → MORPHOLOGIC PROFILES
# ============================================================

def aggregate_tile_csvs(csv_dir: str) -> pd.DataFrame:
    """
    Read all tile CSVs and compute per-slide morphologic profiles.
    
    For each slide:
      pct_{pattern} = count(tiles predicted as pattern) / total_tiles
      n_tiles_total = total tiles analyzed
    """
    print("=" * 70)
    print("[STEP 1] Aggregating tile CSVs into morphologic profiles")
    print("=" * 70)
    
    csv_dir = Path(csv_dir)
    csv_files = sorted(csv_dir.glob("*_tiles_*_v2.csv"))
    
    if not csv_files:
        # Try other patterns
        csv_files = sorted(csv_dir.glob("*.csv"))
    
    print(f"  Found {len(csv_files)} tile CSVs in {csv_dir}")
    
    if len(csv_files) == 0:
        print("  [ERROR] No CSVs found! Is TCGA inference still running?")
        sys.exit(1)
    
    profiles = []
    errors = 0
    
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            n_tiles = len(df)
            
            if n_tiles == 0:
                errors += 1
                continue
            
            # Extract TCGA case ID from filename
            # Format: TCGA-XX-XXXX-01Z-00-DX1.UUID_tiles_512_v2.csv
            stem = csv_path.stem  # e.g., TCGA-75-7030-01Z-00-DX1.5DDF24B5..._tiles_512_v2
            # Get the TCGA barcode (first 3 segments: TCGA-XX-XXXX)
            parts = stem.split("-")
            if len(parts) >= 3 and parts[0] == "TCGA":
                case_id = f"{parts[0]}-{parts[1]}-{parts[2]}"
                # Also keep the full slide name (before _tiles_)
                slide_name = stem.split("_tiles_")[0] if "_tiles_" in stem else stem
            else:
                case_id = stem
                slide_name = stem
            
            # Count predictions per pattern
            if 'pred_label' in df.columns:
                counts = df['pred_label'].str.lower().value_counts()
            elif 'pred_class' in df.columns:
                counts = df['pred_class'].value_counts()
            else:
                errors += 1
                continue
            
            # Compute percentages
            profile = {
                'case_id': case_id,
                'slide_name': slide_name,
                'slide_file': csv_path.name,
                'n_tiles_total': n_tiles,
            }
            
            for pat in PATTERNS:
                cnt = counts.get(pat, 0)
                profile[f'pct_{pat}'] = cnt / n_tiles
                profile[f'n_{pat}'] = int(cnt)
            
            # Also store dominant pattern
            pattern_pcts = {pat: profile[f'pct_{pat}'] for pat in PATTERNS}
            profile['dominant_pattern'] = max(pattern_pcts, key=pattern_pcts.get)
            profile['dominant_pct'] = max(pattern_pcts.values())
            
            profiles.append(profile)
            
        except Exception as e:
            print(f"  [WARN] Error reading {csv_path.name}: {e}")
            errors += 1
    
    df_profiles = pd.DataFrame(profiles)
    
    # Handle multiple slides per case (aggregate)
    n_before = len(df_profiles)
    if df_profiles['case_id'].duplicated().any():
        print(f"  Found {df_profiles['case_id'].duplicated().sum()} duplicate cases (multiple slides)")
        # For duplicates, take the slide with most tiles (most representative)
        df_profiles = df_profiles.sort_values('n_tiles_total', ascending=False)
        df_profiles = df_profiles.drop_duplicates(subset='case_id', keep='first')
        print(f"  After dedup: {len(df_profiles)} unique cases (from {n_before} slides)")
    
    print(f"\n  Profiles generated: {len(df_profiles)}")
    print(f"  Errors/skipped: {errors}")
    print(f"  Mean tiles/slide: {df_profiles['n_tiles_total'].mean():.0f}")
    print(f"  Median tiles/slide: {df_profiles['n_tiles_total'].median():.0f}")
    print(f"\n  Dominant pattern distribution:")
    for pat, cnt in df_profiles['dominant_pattern'].value_counts().items():
        print(f"    {pat}: {cnt} ({cnt/len(df_profiles)*100:.1f}%)")
    
    print(f"\n  Mean pattern composition across cohort:")
    for pat in PATTERNS:
        m = df_profiles[f'pct_{pat}'].mean() * 100
        s = df_profiles[f'pct_{pat}'].std() * 100
        print(f"    {pat:15s}: {m:5.1f}% ± {s:4.1f}")
    
    # Save
    out_path = os.path.join(OUT_DIR, "morphologic_profiles_v2.csv")
    df_profiles.to_csv(out_path, index=False)
    print(f"\n  ✓ Saved: {out_path}")
    
    return df_profiles


# ============================================================
# STEP 2: LOAD / CREATE MUTATION LABELS
# ============================================================

def load_mutation_labels() -> pd.DataFrame:
    """
    Load TCGA-LUAD mutation labels.
    
    Tries in order:
      1. Pre-processed CSV (if exists)
      2. MAF file (if exists, process it)
      3. Download from GDC API
    
    Returns DataFrame with columns: case_id, EGFR, TP53, KRAS, ...
    """
    print("\n" + "=" * 70)
    print("[STEP 2] Loading TCGA mutation labels")
    print("=" * 70)
    
    # Option 1: Pre-processed CSV
    if os.path.exists(MUTATION_LABELS_PATH):
        print(f"  Loading pre-processed labels: {MUTATION_LABELS_PATH}")
        df = pd.read_csv(MUTATION_LABELS_PATH)
        print(f"  {len(df)} cases with mutation labels")
        return df
    
    # Option 2: MAF file
    if os.path.exists(MAF_PATH):
        print(f"  Processing MAF file: {MAF_PATH}")
        return process_maf(MAF_PATH)
    
    # Option 3: Try cBioPortal-style file
    alt_paths = [
        "/home/rapids/notebooks/slima/data/data_mutations.txt",
        "/home/rapids/notebooks/slima/data/tcga_luad_mutations.csv",
        "/home/rapids/notebooks/slima/tcga_luad_mutations.maf",
        "/home/rapids/notebooks/slima/data/mutation_labels.csv",
    ]
    for p in alt_paths:
        if os.path.exists(p):
            print(f"  Found alternative: {p}")
            if p.endswith('.maf') or p.endswith('.maf.gz'):
                return process_maf(p)
            else:
                df = pd.read_csv(p, sep='\t' if p.endswith('.txt') else ',')
                return process_mutation_df(df)
    
    # Option 4: Download from GDC
    print("  No local mutation data found. Attempting GDC download...")
    return download_gdc_mutations()


def process_maf(maf_path: str) -> pd.DataFrame:
    """Process a MAF file into binary mutation labels per case."""
    import gzip
    
    opener = gzip.open if maf_path.endswith('.gz') else open
    
    rows = []
    with opener(maf_path, 'rt') as f:
        header = None
        for line in f:
            if line.startswith('#'):
                continue
            if header is None:
                header = line.strip().split('\t')
                continue
            fields = line.strip().split('\t')
            if len(fields) < len(header):
                continue
            row = dict(zip(header, fields))
            rows.append(row)
    
    df = pd.DataFrame(rows)
    return process_mutation_df(df)


def process_mutation_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a mutations dataframe to binary labels per case × gene."""
    
    # Find the gene column
    gene_col = None
    for c in ['Hugo_Symbol', 'gene', 'Gene', 'hugo_symbol']:
        if c in df.columns:
            gene_col = c
            break
    
    # Find the case/barcode column
    case_col = None
    for c in ['Tumor_Sample_Barcode', 'case_id', 'SAMPLE_ID', 'sample_id',
              'case_submitter_id', 'Tumor_Sample_UUID']:
        if c in df.columns:
            case_col = c
            break
    
    # Find variant classification
    vc_col = None
    for c in ['Variant_Classification', 'variant_classification', 'Consequence']:
        if c in df.columns:
            vc_col = c
            break
    
    if gene_col is None or case_col is None:
        print(f"  [ERROR] Could not find gene/case columns. Available: {list(df.columns[:20])}")
        sys.exit(1)
    
    print(f"  Gene column: {gene_col}, Case column: {case_col}")
    
    # Filter to non-synonymous variants
    synonymous = {'Silent', 'Intron', "3'UTR", "5'UTR", "3'Flank", "5'Flank",
                  'IGR', 'RNA', 'lincRNA'}
    if vc_col:
        before = len(df)
        df = df[~df[vc_col].isin(synonymous)]
        print(f"  Filtered {before - len(df)} synonymous variants → {len(df)} non-synonymous")
    
    # Extract TCGA case ID (first 3 segments)
    def extract_case_id(barcode):
        parts = str(barcode).split('-')
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]}-{parts[2]}"
        return barcode
    
    df['case_id'] = df[case_col].apply(extract_case_id)
    
    # Create binary labels for each gene
    labels = {}
    for gene in GENES:
        gene_cases = set(df[df[gene_col] == gene]['case_id'].unique())
        labels[gene] = gene_cases
    
    all_cases = sorted(df['case_id'].unique())
    
    result = []
    for case in all_cases:
        row = {'case_id': case}
        for gene in GENES:
            row[gene] = 1 if case in labels[gene] else 0
        result.append(row)
    
    df_labels = pd.DataFrame(result)
    
    print(f"\n  Mutation labels for {len(df_labels)} cases:")
    for gene in GENES:
        n_pos = df_labels[gene].sum()
        print(f"    {gene:6s}: {n_pos:3d} mutated ({n_pos/len(df_labels)*100:.1f}%)")
    
    # Save for reuse
    os.makedirs(os.path.dirname(MUTATION_LABELS_PATH), exist_ok=True)
    df_labels.to_csv(MUTATION_LABELS_PATH, index=False)
    print(f"\n  ✓ Saved: {MUTATION_LABELS_PATH}")
    
    return df_labels


def download_gdc_mutations():
    """Download TCGA-LUAD mutations from GDC API."""
    try:
        import requests
    except ImportError:
        print("  [ERROR] requests library needed. pip install requests")
        print("  Alternative: manually download MAF from https://portal.gdc.cancer.gov/")
        print("  Place it at:", MAF_PATH)
        sys.exit(1)
    
    print("  Querying GDC for TCGA-LUAD mutation files...")
    
    # GDC files endpoint — get MAF files for TCGA-LUAD
    filters = {
        "op": "and",
        "content": [
            {"op": "=", "content": {"field": "cases.project.project_id", "value": "TCGA-LUAD"}},
            {"op": "=", "content": {"field": "data_category", "value": "Simple Nucleotide Variation"}},
            {"op": "=", "content": {"field": "data_type", "value": "Masked Somatic Mutation"}},
            {"op": "=", "content": {"field": "data_format", "value": "MAF"}},
        ]
    }
    
    params = {
        "filters": json.dumps(filters),
        "fields": "file_id,file_name,file_size",
        "size": 10,
    }
    
    r = requests.get("https://api.gdc.cancer.gov/files", params=params)
    data = r.json()
    
    if data['data']['hits']:
        file_id = data['data']['hits'][0]['file_id']
        print(f"  Found MAF file: {file_id}")
        
        # Download
        url = f"https://api.gdc.cancer.gov/data/{file_id}"
        r = requests.get(url, stream=True)
        
        os.makedirs(os.path.dirname(MAF_PATH), exist_ok=True)
        with open(MAF_PATH, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  ✓ Downloaded: {MAF_PATH}")
        return process_maf(MAF_PATH)
    else:
        print("  [ERROR] No MAF files found on GDC.")
        print("  Please manually download from: https://portal.gdc.cancer.gov/")
        sys.exit(1)


# ============================================================
# STEP 3: XGBOOST MUTATION PREDICTION
# ============================================================

def train_mutation_models(df_profiles: pd.DataFrame, df_labels: pd.DataFrame):
    """
    Train XGBoost per gene using morphologic features.
    Stratified 5-fold CV for evaluation, train on all data for SHAP.
    """
    try:
        import xgboost as xgb
    except ImportError:
        print("  [ERROR] xgboost required. pip install xgboost")
        sys.exit(1)
    
    try:
        import shap
    except ImportError:
        print("  [WARN] shap not installed. Skipping SHAP plots. pip install shap")
        shap = None
    
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import (f1_score, accuracy_score, roc_auc_score,
                                 precision_score, recall_score, classification_report)
    
    print("\n" + "=" * 70)
    print("[STEP 3] XGBoost Mutation Prediction")
    print("=" * 70)
    
    # Merge profiles with mutation labels
    df = df_profiles.merge(df_labels, on='case_id', how='inner')
    print(f"  Matched cases: {len(df)} (profiles={len(df_profiles)}, labels={len(df_labels)})")
    
    if len(df) < 50:
        print(f"  [ERROR] Only {len(df)} matched cases — too few for meaningful prediction")
        print(f"  Check case_id format. Profile IDs sample: {df_profiles['case_id'].head().tolist()}")
        print(f"  Label IDs sample: {df_labels['case_id'].head().tolist()}")
        return None
    
    # Feature columns
    feature_cols = [f'pct_{p}' for p in PATTERNS] + ['n_tiles_total']
    X = df[feature_cols].values
    feature_names = feature_cols
    
    print(f"  Features: {feature_names}")
    print(f"  Feature matrix: {X.shape}")
    
    results = {}
    
    for gene in GENES:
        if gene not in df.columns:
            print(f"\n  [SKIP] {gene} — not in mutation labels")
            continue
        
        y = df[gene].values
        n_pos = y.sum()
        n_neg = len(y) - n_pos
        
        if n_pos < 5:
            print(f"\n  [SKIP] {gene} — only {n_pos} positive cases (too few)")
            continue
        
        print(f"\n  ── {gene} ──")
        print(f"  Positive: {n_pos}, Negative: {n_neg}, Ratio: 1:{n_neg/max(n_pos,1):.1f}")
        
        # 5-fold stratified CV
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        
        cv_preds = np.zeros(len(y))
        cv_probs = np.zeros(len(y))
        
        for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
            X_tr, X_val = X[train_idx], X[val_idx]
            y_tr, y_val = y[train_idx], y[val_idx]
            
            # Scale positive weight by class imbalance
            spw = (y_tr == 0).sum() / max((y_tr == 1).sum(), 1)
            
            params = XGBOOST_PARAMS.copy()
            params['scale_pos_weight'] = spw
            
            model = xgb.XGBClassifier(**params)
            model.fit(X_tr, y_tr, verbose=False)
            
            cv_probs[val_idx] = model.predict_proba(X_val)[:, 1]
            cv_preds[val_idx] = model.predict(X_val)
        
        # Metrics
        acc = accuracy_score(y, cv_preds)
        f1 = f1_score(y, cv_preds, zero_division=0)
        prec = precision_score(y, cv_preds, zero_division=0)
        rec = recall_score(y, cv_preds, zero_division=0)
        try:
            auc = roc_auc_score(y, cv_probs)
        except:
            auc = 0.0
        
        print(f"  AUC={auc:.3f} | Acc={acc:.3f} | F1={f1:.3f} | P={prec:.3f} | R={rec:.3f}")
        
        results[gene] = {
            'n': len(y), 'n_pos': int(n_pos), 'n_neg': int(n_neg),
            'auc': round(auc, 3), 'accuracy': round(acc, 3),
            'f1': round(f1, 3), 'precision': round(prec, 3), 'recall': round(rec, 3),
        }
        
        # Train final model on all data for SHAP
        spw = (y == 0).sum() / max((y == 1).sum(), 1)
        params = XGBOOST_PARAMS.copy()
        params['scale_pos_weight'] = spw
        final_model = xgb.XGBClassifier(**params)
        final_model.fit(X, y, verbose=False)
        
        # Save model
        model_path = os.path.join(OUT_DIR, f"xgboost_{gene}.json")
        final_model.save_model(model_path)
        
        # SHAP analysis
        if shap is not None:
            try:
                generate_shap_plots(final_model, X, y, feature_names, gene, df)
            except Exception as e:
                print(f"  [WARN] SHAP failed for {gene}: {e}")
    
    # Summary table
    print("\n" + "=" * 70)
    print("[STEP 3] MUTATION PREDICTION RESULTS (V2 CTransPath)")
    print("=" * 70)
    print(f"\n{'Gene':>6} {'N':>5} {'N+':>5} {'N-':>5} {'AUC':>6} {'Acc':>6} {'F1':>6} {'P':>6} {'R':>6}")
    print("-" * 58)
    for gene, r in results.items():
        print(f"{gene:>6} {r['n']:>5} {r['n_pos']:>5} {r['n_neg']:>5} "
              f"{r['auc']:>6.3f} {r['accuracy']:>6.3f} {r['f1']:>6.3f} "
              f"{r['precision']:>6.3f} {r['recall']:>6.3f}")
    
    # Save results
    results_path = os.path.join(OUT_DIR, "xgboost_mutation_results_v2.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n  ✓ Saved: {results_path}")
    
    return results


# ============================================================
# STEP 4: SHAP PLOTS
# ============================================================

def generate_shap_plots(model, X, y, feature_names, gene, df_full):
    """Generate SHAP bar, beeswarm, and force plots for a gene."""
    import shap
    
    print(f"  Generating SHAP plots for {gene}...")
    
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    
    # Bar plot (global feature importance)
    fig, ax = plt.subplots(figsize=(10, 5))
    shap.summary_plot(shap_values, X, feature_names=feature_names,
                      plot_type="bar", show=False, max_display=len(feature_names))
    plt.title(f"SHAP Bar — {gene} Mutation (Global Feature Importance)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"shap_{gene.lower()}_bar.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Beeswarm plot
    fig, ax = plt.subplots(figsize=(10, 5))
    shap.summary_plot(shap_values, X, feature_names=feature_names,
                      show=False, max_display=len(feature_names))
    plt.title(f"SHAP Beeswarm — {gene} Mutation (Feature Impact Distribution)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, f"shap_{gene.lower()}_beeswarm.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # Force plot for a representative positive case
    pos_idx = np.where(y == 1)[0]
    if len(pos_idx) > 0:
        # Pick the positive case with highest predicted probability
        probs = model.predict_proba(X)[:, 1]
        best_pos = pos_idx[np.argmax(probs[pos_idx])]
        
        fig = plt.figure(figsize=(14, 3))
        shap.force_plot(explainer.expected_value, shap_values[best_pos],
                       X[best_pos], feature_names=feature_names,
                       matplotlib=True, show=False)
        plt.title(f"SHAP Force — {gene} (Case-Level Explanation)")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, f"shap_{gene.lower()}_force.png"),
                   dpi=150, bbox_inches='tight')
        plt.close()
    
    print(f"  ✓ SHAP plots saved for {gene}")


# ============================================================
# STEP 5: COMPARISON WITH PREVIOUS RESULTS
# ============================================================

def compare_with_previous(new_results: dict):
    """Compare new V2/CTransPath results with old V1/ResNet50 results from thesis."""
    
    print("\n" + "=" * 70)
    print("[STEP 5] COMPARISON: Old (V1/ResNet50) vs New (V2/CTransPath)")
    print("=" * 70)
    
    # Previous results from thesis Table (mutation_results)
    old_results = {
        'EGFR':  {'n': 216, 'n_pos': 26,  'n_neg': 190, 'auc': 0.436, 'accuracy': 0.800, 'f1': 0.133, 'precision': 0.143, 'recall': 0.125},
        'TP53':  {'n': 216, 'n_pos': 132, 'n_neg': 84,  'auc': 0.473, 'accuracy': 0.523, 'f1': 0.608, 'precision': 0.615, 'recall': 0.600},
        'KEAP1': {'n': 216, 'n_pos': 36,  'n_neg': 180, 'auc': 0.544, 'accuracy': 0.785, 'f1': 0.222, 'precision': 0.286, 'recall': 0.182},
        'NF1':   {'n': 216, 'n_pos': 27,  'n_neg': 189, 'auc': 0.480, 'accuracy': 0.769, 'f1': 0.000, 'precision': 0.000, 'recall': 0.000},
        'STK11': {'n': 216, 'n_pos': 18,  'n_neg': 198, 'auc': 0.573, 'accuracy': 0.908, 'f1': 0.000, 'precision': 0.000, 'recall': 0.000},
    }
    
    print(f"\n{'Gene':>6} {'Old AUC':>8} {'New AUC':>8} {'Δ AUC':>7} {'Old F1':>7} {'New F1':>7} {'Δ F1':>7}")
    print("-" * 55)
    
    for gene in GENES:
        old = old_results.get(gene, {})
        new = new_results.get(gene, {})
        
        if not old or not new:
            continue
        
        d_auc = new['auc'] - old['auc']
        d_f1 = new['f1'] - old['f1']
        
        arrow_auc = "↑" if d_auc > 0.01 else "↓" if d_auc < -0.01 else "≈"
        arrow_f1 = "↑" if d_f1 > 0.01 else "↓" if d_f1 < -0.01 else "≈"
        
        print(f"{gene:>6} {old['auc']:>8.3f} {new['auc']:>8.3f} {d_auc:>+6.3f}{arrow_auc}"
              f" {old['f1']:>7.3f} {new['f1']:>7.3f} {d_f1:>+6.3f}{arrow_f1}")
    
    print(f"\n  Old profile model: ResNet50 + FuzzyArcLoss V1/V3 (~76% tile F1)")
    print(f"  New profile model: CTransPath + FuzzyArcLoss V2 Optuna (92.3% tile F1)")
    print(f"  Thesis hypothesis: Better tile classification → cleaner profiles → better mutation signal")


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  SLIMA Aggregation + XGBoost Mutation Prediction")
    print("  CTransPath + FuzzyArcLoss V2 (K-fold: 92.31% ± 2.04)")
    print("=" * 70)
    
    # Step 1: Aggregate tiles
    df_profiles = aggregate_tile_csvs(TILE_CSV_DIR)
    
    # Step 2: Load mutation labels
    df_labels = load_mutation_labels()
    
    # Step 3: Train XGBoost + SHAP
    results = train_mutation_models(df_profiles, df_labels)
    
    # Step 5: Compare old vs new
    if results:
        compare_with_previous(results)
    
    print("\n" + "=" * 70)
    print("  DONE — All outputs in:", OUT_DIR)
    print("=" * 70)
    
    # List outputs
    for f in sorted(Path(OUT_DIR).glob("*")):
        size = f.stat().st_size
        print(f"  {f.name} ({size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
