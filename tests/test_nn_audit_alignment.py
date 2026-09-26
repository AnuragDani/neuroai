import json
import logging
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score

from p22.data.nn_inputs import load_nn_inputs, region_indices
from p22.data.nn_fold import prepare_nn_fold
from p22.data.group_splits import iter_repeated_stratified_group_folds
from scripts.run_nn_v2_comparison import worker_task

def test_audit_alignment_chr21_dosage(tmp_path):
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
    
    with open("configs/nn_protocol_v2_2026-09-23.json") as f:
        protocol = json.load(f)
        
    h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
    atac_path = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = input_manifest["inputs"]["tracked_union_bed"]["path"]
    
    inputs = load_nn_inputs(
        h5ad_path, atac_path, 
        protocol["sampling"]["cap_per_donor"], 
        22, # sampling_seed
        union_bed=union_bed
    )
    
    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=1, n_folds=5, base_seed=0
    ))
    split = splits[0]
    
    cfg = protocol["training"].copy()
    cfg["seed"] = 0
    
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    
    record, error = worker_task(
        out_dir, 
        "chr21_dosage", 
        split.repeat, 
        split.fold, 
        split.train_index, 
        split.test_index, 
        inputs, 
        protocol, 
        False, 
        0, 
        cfg
    )
    
    assert error is None, f"worker_task failed: {error}"
    
    donor_ids = np.array(record["donor_ids"])
    donor_labels = np.array(record["donor_labels"])
    donor_probs = np.array(record["donor_probabilities"])
    
    # Assert label correctness
    metadata = inputs.metadata.drop_duplicates("donor_id").set_index("donor_id")
    for d, l in zip(donor_ids, donor_labels):
        true_disease = metadata.loc[d, "disease"]
        expected_l = 1 if true_disease == "complete trisomy 21" else 0
        assert l == expected_l, f"Donor {d} label mismatch: got {l}, expected {expected_l}"
        
    # Assert AUROC >= 0.85
    auroc = roc_auc_score(donor_labels, donor_probs)
    assert auroc >= 0.85, f"AUROC is too low: {auroc}"
