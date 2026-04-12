import json, os, statistics

base = r"D:\Dropbox\PHD\THESIS\results_luad_v2_no_checkpoints ver 15 mar 2026"
genes = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10']

conditions = {
    'B1': 'metrics_baseline1_xgboost',
    'B2': 'metrics_baseline2_abmil_embeddings',
    'B3': 'metrics_baseline3_abmil_patterns',
    'PI-ABMIL': 'metrics_proposed_abmil_concat',
    'A': 'metrics_ablation_abmil_onehot',
    'FC-MIL': 'metrics_proposed_fuzzy_choquet',
}

# Gene-optimal methods from Table 6.7
gene_optimal = {
    'TP53': 'B2', 'EGFR': 'B2',
    'STK11': 'PI-ABMIL', 'KEAP1': 'PI-ABMIL',
    'KRAS': 'FC-MIL', 'RBM10': 'FC-MIL',
}

print(f"{'Cond':<12} {'Gene':<8} {'fold0':>7} {'fold1':>7} {'fold2':>7} {'fold3':>7} {'fold4':>7} {'mean':>7} {'std':>7} {'max':>7}")
print("-" * 90)

for cond_name, prefix in conditions.items():
    for gene in genes:
        fold_aurocs = []
        for fold in range(5):
            path = os.path.join(base, f"{prefix}_{gene}_fold{fold}.json")
            if not os.path.exists(path):
                fold_aurocs.append(None)
                continue
            with open(path) as f:
                data = json.load(f)
            auroc = data.get('auroc', data.get('test_auroc', data.get('best_auroc', None)))
            fold_aurocs.append(float(auroc) if auroc is not None else None)

        valid = [a for a in fold_aurocs if a is not None]
        if valid:
            m = statistics.mean(valid)
            s = statistics.stdev(valid) if len(valid) > 1 else 0
            vals = [f"{a:.4f}" if a else "  ?   " for a in fold_aurocs]
            is_optimal = gene_optimal.get(gene) == cond_name
            marker = " <<<" if is_optimal else ""
            print(f"{cond_name:<12} {gene:<8} {' '.join(vals)}  {m:.4f}  {s:.4f}  {max(valid):.4f}{marker}")

print("\n\n=== BEST FOLD AUROC FOR GENE-OPTIMAL METHODS ===")
print(f"{'Gene':<8} {'Method':<12} {'Mean':>7} {'Std':>7} {'Max fold':>9} {'Thesis says':>12}")
print("-" * 60)

thesis_best_fold = {'TP53': 0.793, 'EGFR': 0.758, 'KRAS': 0.684, 'STK11': 0.727, 'KEAP1': 0.737, 'RBM10': 0.733}

for gene in genes:
    cond = gene_optimal[gene]
    prefix = conditions[cond]
    fold_aurocs = []
    for fold in range(5):
        path = os.path.join(base, f"{prefix}_{gene}_fold{fold}.json")
        with open(path) as f:
            data = json.load(f)
        auroc = data.get('auroc', data.get('test_auroc', None))
        fold_aurocs.append(float(auroc))
    m = statistics.mean(fold_aurocs)
    s = statistics.stdev(fold_aurocs)
    mx = max(fold_aurocs)
    thesis_val = thesis_best_fold[gene]
    match = "OK" if abs(mx - thesis_val) < 0.002 else "MISMATCH!"
    print(f"{gene:<8} {cond:<12} {m:.4f}  {s:.4f}  {mx:.4f}     {thesis_val:.3f}    {match}")
