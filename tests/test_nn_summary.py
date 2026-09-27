import json
import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import sys
from sklearn.metrics import balanced_accuracy_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from p22.eval.repeated_comparison import repeated_primary_contrast
import scripts.summarize_nn_v2

def independent_recomputation(repeats):
    pooled = {}
    for entry in repeats:
        rep = entry["repeat"]
        if rep not in pooled:
            pooled[rep] = {"R3_ca": [], "R3_tc": []}
        pooled[rep]["R3_ca"].append(entry["R3_ca"])
        pooled[rep]["R3_tc"].append(entry["R3_tc"])
        
    merged_repeats = []
    for rep in sorted(pooled.keys()):
        ca = pd.concat(pooled[rep]["R3_ca"], ignore_index=True).sort_values("donor_id").reset_index(drop=True)
        tc = pd.concat(pooled[rep]["R3_tc"], ignore_index=True).sort_values("donor_id").reset_index(drop=True)
        merged_repeats.append({
            "repeat": rep,
            "R3_ca": ca,
            "R3_tc": tc
        })
        
    rep0 = merged_repeats[0]
    donors = rep0["R3_ca"]["donor_id"].to_numpy()
    labels = rep0["R3_ca"]["label"].to_numpy()
    
    prepared = []
    for rep in merged_repeats:
        ca_pred = (rep["R3_ca"]["probability"].to_numpy(dtype=float) >= 0.5).astype(int)
        tc_pred = (rep["R3_tc"]["probability"].to_numpy(dtype=float) >= 0.5).astype(int)
        prepared.append((ca_pred, tc_pred))
        
    rng = np.random.default_rng(22)
    n_donors = len(donors)
    
    def get_delta(idx):
        truth = labels[idx]
        deltas = []
        for ca_pred, tc_pred in prepared:
            first = balanced_accuracy_score(truth, ca_pred[idx])
            second = balanced_accuracy_score(truth, tc_pred[idx])
            deltas.append(first - second)
        return float(np.mean(deltas))
        
    values = []
    for _ in range(1000):
        idx = rng.choice(n_donors, size=n_donors, replace=True)
        if len(np.unique(labels[idx])) < 2:
            continue
        values.append(get_delta(idx))
        
    estimate = np.mean([get_delta(np.arange(n_donors))]) # well, mean of deltas without bootstrap
    
    tail = (1.0 - 0.95) / 2.0
    bounds = np.percentile(values, [100 * tail, 100 * (1 - tail)])
    return float(estimate), [float(bounds[0]), float(bounds[1])]

def test_summary():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        folds_dir = tmp_path / "folds"
        folds_dir.mkdir()
        
        rng = np.random.default_rng(42)
        donors_fold0 = [f"D{i}" for i in range(20)]
        donors_fold1 = [f"D{i}" for i in range(20, 40)]
        
        repeats_for_indep = []
        for rep in range(3):
            for fold, donors in enumerate([donors_fold0, donors_fold1]):
                labels = [i % 2 for i in range(len(donors))]
                
                ca_probs = rng.uniform(0, 1, size=len(donors)).tolist()
                tc_probs = rng.uniform(0, 1, size=len(donors)).tolist()
                
                with open(folds_dir / f"rep{rep}_fold{fold}_R3_ca.json", "w") as fp:
                    json.dump({
                        "repeat": rep,
                        "arm": "R3_ca",
                        "donor_ids": donors,
                        "donor_labels": labels,
                        "donor_probabilities": ca_probs
                    }, fp)
                
                with open(folds_dir / f"rep{rep}_fold{fold}_R3_tc.json", "w") as fp:
                    json.dump({
                        "repeat": rep,
                        "arm": "R3_tc",
                        "donor_ids": donors,
                        "donor_labels": labels,
                        "donor_probabilities": tc_probs
                    }, fp)
                    
                repeats_for_indep.append({
                    "repeat": rep,
                    "R3_ca": pd.DataFrame({"donor_id": donors, "label": labels, "probability": ca_probs}),
                    "R3_tc": pd.DataFrame({"donor_id": donors, "label": labels, "probability": tc_probs})
                })
                
        out_docs = tmp_path / "docs"
        out_docs.mkdir()
        
        ret = scripts.summarize_nn_v2.main(["--run", str(tmp_path), "--out", str(out_docs)])
        assert ret == 0
        
        with open(out_docs / "ladder_summary.json") as fp:
            res = json.load(fp)
            
        ci = res["primary"]["ci"]
        assert ci[1] - ci[0] > 0
        
        est_indep, ci_indep = independent_recomputation(repeats_for_indep)
        
        assert abs(res["primary"]["estimate"] - est_indep) < 1e-9
        assert abs(ci[0] - ci_indep[0]) < 1e-9
        assert abs(ci[1] - ci_indep[1]) < 1e-9
