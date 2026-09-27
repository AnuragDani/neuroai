import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold

def main():
    with open("configs/nn_inputs_2026-09-23.json") as f:
        inputs_cfg = json.load(f)

    h5ad_path = inputs_cfg["inputs"]["h5ad"]["path"]
    atac_path = inputs_cfg["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = inputs_cfg["inputs"]["tracked_union_bed"]["path"]

    inputs = load_nn_inputs(h5ad_path, atac_path, cap=256, seed=22, union_bed=union_bed)

    chr21_mask = inputs.chr21_gene_mask()
    print("Num chr21 genes:", chr21_mask.sum())

    rows = np.arange(len(inputs.metadata))
    cfg = {"n_hvg": 2000}
    fold_arrays = prepare_nn_fold(inputs, rows, rows, np.arange(len(inputs.regions)))

    chr21_genes_in_hvg = np.isin(fold_arrays.gene_ids, inputs.gene_ids[chr21_mask])
    print("Num chr21 genes in HVG:", chr21_genes_in_hvg.sum())

    dosage = fold_arrays.rna[:len(rows)][:, chr21_genes_in_hvg].mean(axis=1)

    df = pd.DataFrame({
        'donor': fold_arrays.donor[:len(rows)],
        'label': fold_arrays.label[:len(rows)],
        'dosage': dosage
    })
    grouped = df.groupby('donor').mean()
    print("Mean dosage control:", grouped[grouped['label']==0]['dosage'].mean())
    print("Mean dosage DS:", grouped[grouped['label']==1]['dosage'].mean())

    lr = LogisticRegression(fit_intercept=False)
    lr.fit(grouped[['dosage']], grouped['label'])
    probs = lr.predict_proba(grouped[['dosage']])[:, 1]
    print("AUROC LR (fit_intercept=False):", roc_auc_score(grouped['label'], probs))

    lr2 = LogisticRegression(fit_intercept=True)
    lr2.fit(grouped[['dosage']], grouped['label'])
    probs2 = lr2.predict_proba(grouped[['dosage']])[:, 1]
    print("AUROC LR (fit_intercept=True):", roc_auc_score(grouped['label'], probs2))

if __name__ == "__main__":
    main()
