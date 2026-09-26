import json
import subprocess
import sys
from pathlib import Path
from sklearn.metrics import roc_auc_score

def test_audit_alignment(tmp_path):
    out_dir = tmp_path / "ladder"
    
    cmd = [
        sys.executable, "scripts/run_nn_v2_comparison.py",
        "--protocol", "configs/nn_protocol_v2_2026-09-23.json",
        "--out", str(out_dir),
        "--arms", "chr21_dosage",
        "--repeats", "1",
        "--folds", "1",
        "--workers", "1"
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    
    run_json = out_dir / "run.json"
    assert run_json.exists()
    
    fold_file = out_dir / "folds" / "r0_f0_chr21_dosage.json"
    assert fold_file.exists()
    
    with open(fold_file) as f:
        fold_data = json.load(f)
        
    labels = fold_data["donor_labels"]
    probs = fold_data["donor_probabilities"]
    donors = fold_data["donor_ids"]
    
    auroc = roc_auc_score(labels, probs)
    
    from p22.data.nn_inputs import load_nn_inputs
    with open("configs/nn_inputs_2026-09-23.json") as f:
        input_manifest = json.load(f)
    h5ad_path = input_manifest["inputs"]["h5ad"]["path"]
    atac_path = input_manifest["inputs"]["atac_tiebreak_counts"]["path"]
    union_bed = input_manifest["inputs"]["tracked_union_bed"]["path"]
    
    inputs = load_nn_inputs(
        h5ad_path, atac_path, cap=1000, seed=22, union_bed=union_bed
    )
    
    donor_to_disease = {}
    for d, dis in zip(inputs.metadata["donor_id"], inputs.metadata["disease"]):
        donor_to_disease[d] = 1 if dis == "complete trisomy 21" else 0
        
    for d, l in zip(donors, labels):
        assert l == donor_to_disease[d], f"Donor {d} label mismatch: {l} != {donor_to_disease[d]}"
        
    assert auroc >= 0.85, f"chr21_dosage AUROC is {auroc}, expected >= 0.85"
