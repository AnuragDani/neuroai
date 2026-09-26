import pytest
import numpy as np
import scipy.sparse as sparse
from sklearn.metrics import roc_auc_score
from p22.data.group_splits import iter_repeated_stratified_group_folds
from p22.data.nn_inputs import load_nn_inputs
from p22.data.nn_fold import prepare_nn_fold
from p22.eval.nn_factory import build_arm, ArmData

import json

def test_audit_alignment():
    # Use real configs to run ladder's data path for chr21_dosage
    with open("configs/nn_protocol_v2_2026-09-23.json") as f:
        cfg = json.load(f)
    
    with open("configs/nn_inputs_2026-09-23.json") as f:
        inputs_cfg = json.load(f)
    
    h5ad = inputs_cfg["inputs"]["h5ad"]["path"]
    atac_npz = inputs_cfg["inputs"]["atac_tiebreak_counts"]["path"]
    
    union_bed = inputs_cfg["inputs"]["tracked_union_bed"]["path"]
    inputs = load_nn_inputs(h5ad, atac_npz, cap=cfg["sampling"]["cap_per_donor"], seed=cfg["sampling"]["seed"], union_bed=union_bed)
    donors = inputs.metadata["donor_id"].to_numpy()
    labels = (inputs.metadata["disease"] == "complete trisomy 21").astype(int).to_numpy()
    
    # One fold
    all_folds = list(iter_repeated_stratified_group_folds(donors, labels, n_repeats=1, n_folds=5, base_seed=0))
    train_idx, test_idx = all_folds[0].train_index, all_folds[0].test_index
    
    # we need the region set for fold 0
    region_rows = np.arange(inputs.atac.shape[1]) # just keep all for this test
    
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path("scripts").absolute()))
    from run_nn_v2_comparison import worker_task
    
    folds_dir = Path("/tmp/folds")
    folds_dir.mkdir(parents=True, exist_ok=True)
    
    all_donors = []
    all_labels = []
    all_probs = []
    
    for fold_obj in all_folds:
        record, error = worker_task(
            out_dir=Path("/tmp"),
            arm_name="chr21_dosage",
            repeat=fold_obj.repeat,
            fold=fold_obj.fold,
            train_rows=fold_obj.train_index,
            test_rows=fold_obj.test_index,
            inputs=inputs,
            protocol=cfg,
            exclude_chr21=False,
            model_seed=42,
            cfg=cfg["training"]
        )
        assert error is None
        
        all_donors.extend(record["donor_ids"])
        all_labels.extend(record["donor_labels"])
        all_probs.extend(record["donor_probabilities"])
        
    auroc = roc_auc_score(all_labels, all_probs)
    print(f"Global worker_task AUROC: {auroc}")
    assert auroc >= 0.85, f"AUROC too low: {auroc}"
