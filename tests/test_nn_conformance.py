import json
from pathlib import Path
import pytest
from p22.eval.nn_factory import parameter_counts

def test_frozen_parameter_counts_match_protocol():
    with open("configs/nn_protocol_v2_2026-09-23.json") as f:
        protocol = json.load(f)
        
    with open("docs/nn_v2/parameter_counts.json") as f:
        frozen_counts = json.load(f)
        
    widths = frozen_counts["widths"]
    cfg = protocol["architecture"].copy()
    cfg.update(protocol["training"])
    import numpy as np
    cfg["cell_meta"] = {
        "labels": np.zeros(1),
        "library": np.zeros(1),
        "batch": np.zeros(1),
        "qc": np.zeros(1)
    }
    
    current_counts = parameter_counts(widths, cfg)
    
    for arm, expected in frozen_counts["counts"].items():
        if expected is None:
            assert current_counts[arm] is None
            continue
            
        expected_params = expected["n_params"]
        actual_params = current_counts[arm]["n_params"]
        
        rel_diff = abs(expected_params - actual_params) / expected_params
        assert rel_diff < 0.01, f"Arm {arm} params differ: {actual_params} vs expected {expected_params}"
