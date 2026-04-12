import torch, os, statistics

base = '/data/checkpoints'
genes = ['TP53', 'EGFR', 'KRAS', 'STK11', 'KEAP1', 'RBM10']

conditions = {
    'B2': 'ckpt_baseline2_abmil_embeddings',
    'B3': 'ckpt_baseline3_abmil_patterns',
    'PI-ABMIL': 'ckpt_proposed_abmil_concat',
    'A': 'ckpt_ablation_abmil_onehot',
    'FC-MIL': 'ckpt_proposed_fuzzy_choquet',
}

for cond_name, prefix in conditions.items():
    for gene in genes:
        fold_aurocs = []
        for fold in range(5):
            path = os.path.join(base, f"{prefix}_{gene}_fold{fold}.pth")
            if not os.path.exists(path):
                fold_aurocs.append(None)
                continue
            ck = torch.load(path, map_location='cpu', weights_only=False)
            auroc = ck.get('best_auroc', ck.get('test_auroc', ck.get('auroc', None)))
            if auroc is None:
                for k in ck.keys():
                    if 'auroc' in k.lower():
                        auroc = ck[k]
                        break
            if auroc is None:
                # Try inside metrics dict
                metrics = ck.get('metrics', {})
                auroc = metrics.get('auroc', metrics.get('best_auroc', None))
            fold_aurocs.append(float(auroc) if auroc is not None else None)

        valid = [a for a in fold_aurocs if a is not None]
        if valid:
            m = statistics.mean(valid)
            s = statistics.stdev(valid) if len(valid) > 1 else 0
            vals_str = '  '.join(f"{a:.4f}" if a else "?" for a in fold_aurocs)
            print(f"{cond_name:12s} {gene:8s} [{vals_str}]  mean={m:.4f}  std={s:.4f}  max={max(valid):.4f}  min={min(valid):.4f}")
        else:
            # Check what keys are available
            path = os.path.join(base, f"{prefix}_{gene}_fold0.pth")
            if os.path.exists(path):
                ck = torch.load(path, map_location='cpu', weights_only=False)
                print(f"{cond_name:12s} {gene:8s} NO AUROC KEY. Available keys: {list(ck.keys())[:10]}")
            else:
                print(f"{cond_name:12s} {gene:8s} FILE NOT FOUND")
