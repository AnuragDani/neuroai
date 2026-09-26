import pytest
from p22.eval.nn_factory import build_arm
from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold
from p22.eval.nn_factory import ArmData
import json
import numpy as np
from sklearn.metrics import roc_auc_score
from pathlib import Path
import sys

def test_chr21_dosage_alignment():
    with open("configs/nn_inputs_2026-09-23.json") as f:
        inputs_cfg = json.load(f)
        
    h5ad_path = inputs_cfg["inputs"]["h5ad"]["path"]
    atac_path = inputs_cfg["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = "configs/nn_gene_activity_2026-09-23.bed"
    if not Path(union_bed).exists():
        union_bed = inputs_cfg["inputs"]["tracked_union_bed"]["path"]
    
    inputs = load_nn_inputs(h5ad_path, atac_path, cap=256, seed=22, union_bed=union_bed)
    
    train_rows = np.arange(len(inputs.metadata))
    test_rows = np.arange(len(inputs.metadata))
    region_rows = np.arange(len(inputs.regions))
    
    cfg = {"n_hvg": 2000}
    
    fold_arrays = prepare_nn_fold(inputs, train_rows, test_rows, region_rows, cfg=cfg)
    
    widths = {
        "n_features_a": fold_arrays.rna.shape[1],
        "n_features_b": fold_arrays.atac.shape[1],
        "n_library": len(np.unique(inputs.metadata["library"])),
        "n_batch": len(np.unique(inputs.metadata["batch_seq"])),
        "k_rna": 16,
        "k_atac": 8,
        "n_classes": 2
    }
    
    model, aux, trainer = build_arm("chr21_dosage", widths, cfg)
    
    test_pos = np.arange(len(train_rows), len(train_rows) + len(test_rows))
    
    chr21_mask = inputs.chr21_gene_mask()
    chr21_genes_in_hvg = np.isin(fold_arrays.gene_ids, inputs.gene_ids[chr21_mask])
    
    chr21_dosage_train = fold_arrays.rna[np.arange(len(train_rows))][:, chr21_genes_in_hvg].mean(axis=1) if chr21_genes_in_hvg.any() else np.zeros(len(train_rows))
    chr21_dosage_test = fold_arrays.rna[test_pos][:, chr21_genes_in_hvg].mean(axis=1) if chr21_genes_in_hvg.any() else np.zeros(len(test_pos))
    
    train_data = ArmData(
        views={"chr21_dosage": chr21_dosage_train},
        labels=fold_arrays.label[np.arange(len(train_rows))],
        donors=fold_arrays.donor[np.arange(len(train_rows))],
        cell_meta=None
    )
    
    test_data = ArmData(
        views={"chr21_dosage": chr21_dosage_test},
        labels=fold_arrays.label[test_pos],
        donors=fold_arrays.donor[test_pos],
        cell_meta=None
    )
    
    trained = trainer(model, train_data, test_data)
    
    probs = trained.predict_proba(test_data.views)
    
    donor_probs_dict = {}
    for d, p in zip(test_data.donors, probs[:, 1]):
        donor_probs_dict.setdefault(d, []).append(p)
    donor_probs = {d: np.mean(v) for d, v in donor_probs_dict.items()}
    donor_ids = sorted(donor_probs.keys())
    donor_probabilities = [donor_probs[d] for d in donor_ids]
    
    donor_labels_dict = {}
    for d, l in zip(test_data.donors, test_data.labels):
        donor_labels_dict[d] = int(l)
    donor_labels_list = [donor_labels_dict[d] for d in donor_ids]
    
    mismatches = 0
    donor_disease = inputs.metadata.groupby("donor_id")["disease"].first()
    for i, d in enumerate(donor_ids):
        h5ad_label = 1 if donor_disease[d] == "complete trisomy 21" else 0
        sys.stderr.write(f"{d}: fold_label={donor_labels_list[i]}, h5ad_label={h5ad_label}, prob={donor_probabilities[i]:.4f}\n")
        if donor_labels_list[i] != h5ad_label:
            mismatches += 1
            
    assert mismatches == 0, f"{mismatches} donor labels mismatched"
    
    auroc = roc_auc_score(donor_labels_list, donor_probabilities)
    sys.stderr.write(f"AUROC: {auroc}\n")
    assert auroc >= 0.85, f"AUROC {auroc} < 0.85"
