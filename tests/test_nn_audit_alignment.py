import pytest
import json
import numpy as np
import pandas as pd
from pathlib import Path

from p22.data.nn_inputs import load_nn_inputs, prepare_nn_fold
from p22.eval.nn_factory import build_arm
from p22.models.fusion import VIEW_A
from p22.training.loop import predict

def test_chr21_dosage_alignment():
    # Load inputs
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
        
    h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
    atac_path = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = input_manifest["inputs"]["tracked_union_bed"]["path"]
    
    inputs = load_nn_inputs(
        h5ad_path, atac_path, cap=1000, seed=22, union_bed=union_bed
    )
    
    # We can just use the whole dataset as both train and test to see if the alignment is correct
    n_cells = len(inputs.metadata)
    train_rows = np.arange(n_cells)
    test_rows = np.array([], dtype=np.int64)
    region_rows = np.arange(len(inputs.regions))
    
    fold_arrays = prepare_nn_fold(
        inputs,
        train_rows,
        test_rows,
        region_rows,
        n_hvg=2000,
        exclude_chr21=False
    )
    
    # We want to check the labels in the fold vs H5AD
    original_metadata = inputs.metadata
    
    # Check label alignment
    for i in range(len(train_rows)):
        donor = fold_arrays.donor[i]
        label = fold_arrays.label[i]
        orig_disease = original_metadata.iloc[i]["disease"]
        expected_label = 1 if orig_disease == "complete trisomy 21" else 0
        assert label == expected_label, f"Label mismatch for {donor}: got {label}, expected {expected_label} from {orig_disease}"
        
    # Check chr21 dosage AUROC
    # chr21 dosage uses the sum or mean of chr21 genes
    chr21_mask = inputs.chr21_gene_mask()
    chr21_genes_in_hvg = np.isin(fold_arrays.gene_ids, inputs.gene_ids[chr21_mask])
    
    assert chr21_genes_in_hvg.any(), "No chr21 genes in HVG"
    
    chr21_dosage = fold_arrays.rna[:, chr21_genes_in_hvg].mean(axis=1)
    
    # Aggregate to donor level
    donor_probs_dict = {}
    donor_labels_dict = {}
    for d, prob, lbl in zip(fold_arrays.donor, chr21_dosage, fold_arrays.label):
        donor_probs_dict.setdefault(d, []).append(prob)
        donor_labels_dict[d] = int(lbl)
        
    donor_ids = sorted(donor_probs_dict.keys())
    donor_probabilities = [np.mean(donor_probs_dict[d]) for d in donor_ids]
    donor_labels_list = [donor_labels_dict[d] for d in donor_ids]
    
    from sklearn.metrics import roc_auc_score
    auroc = roc_auc_score(donor_labels_list, donor_probabilities)
    print(f"Donor AUROC: {auroc}")
    
    assert auroc >= 0.85, f"AUROC {auroc} is less than 0.85"
