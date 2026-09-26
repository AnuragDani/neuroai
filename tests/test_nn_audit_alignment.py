import pytest
import json
from pathlib import Path
import tempfile
import numpy as np
from scripts.run_nn_v2_comparison import worker_task
from p22.data.nn_inputs import load_nn_inputs
from sklearn.metrics import roc_auc_score

def test_audit_alignment():
    # Load input manifest
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
        
    h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
    atac_path = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = input_manifest["inputs"]["tracked_union_bed"]["path"]
    
    # We load with cap=256 for faster testing
    inputs = load_nn_inputs(
        h5ad_path, atac_path, cap=256, seed=22, union_bed=union_bed
    )
    
    with open("configs/nn_protocol_v2_2026-09-23.json") as f:
        protocol = json.load(f)
        
    from p22.data.group_splits import iter_repeated_stratified_group_folds
    metadata = inputs.metadata
    donors = metadata["donor_id"].to_numpy()
    labels = (metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    splits = list(iter_repeated_stratified_group_folds(
        donors, labels, n_repeats=1, n_folds=5, base_seed=protocol["splits"]["split_seed"]
    ))
    split = splits[0]
    train_rows = split.train_index
    test_rows = split.test_index
    
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        # We run chr21_dosage
        rec, err = worker_task(
            out_dir=out_dir,
            arm_name="chr21_dosage",
            repeat=0,
            fold=0,
            train_rows=train_rows,
            test_rows=test_rows,
            inputs=inputs,
            protocol=protocol,
            exclude_chr21=False,
            model_seed=0,
            cfg=cfg
        )
        assert err is None, f"Worker task failed: {err}"
        
        # Check AUC
        auroc = roc_auc_score(rec["donor_labels"], rec["donor_probabilities"])
        assert auroc >= 0.85, f"AUROC {auroc} < 0.85"
        
        # Check alignment: donor label matches H5AD disease
        donor_disease = dict(zip(inputs.metadata["donor_id"], inputs.metadata["disease"]))
        for donor_id, label in zip(rec["donor_ids"], rec["donor_labels"]):
            disease = donor_disease[donor_id]
            expected_label = 1 if disease == "complete trisomy 21" else 0
            assert label == expected_label, f"Misalignment for donor {donor_id}: got {label}, expected {expected_label} ({disease})"
