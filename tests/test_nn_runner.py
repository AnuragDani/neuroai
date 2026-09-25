import json
import subprocess
import sys
from pathlib import Path

def test_runner_and_summarizer(tmp_path):
    # Call the runner with synthetic flag
    out_dir = tmp_path / "ladder"
    
    cmd = [
        sys.executable, "scripts/run_nn_v2_comparison.py",
        "--protocol", "configs/nn_protocol_v2_2026-09-23.json",
        "--out", str(out_dir),
        "--arms", "R3_ca", "R3_tc",
        "--repeats", "1",
        "--folds", "2",
        "--workers", "1",
        "--synthetic"
    ]
    
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    
    run_json = out_dir / "run.json"
    assert run_json.exists()
    
    with open(run_json) as f:
        run_data = json.load(f)
    assert run_data["folds_expected"] == 4  # 2 arms * 1 repeat * 2 folds
    assert run_data["folds_done"] == 4
    assert not run_data["failures"]
    
    # Check that model JSONs and PTs exist
    assert (out_dir / "models" / "R3_ca" / "r0_f0.json").exists()
    assert (out_dir / "models" / "R3_ca" / "r0_f0.pt").exists()
    
    # Test resume
    res2 = subprocess.run(cmd + ["--resume"], capture_output=True, text=True)
    assert res2.returncode == 0, res2.stderr
    with open(run_json) as f:
        run_data = json.load(f)
    assert run_data["folds_expected"] == 4
    assert run_data["folds_done"] == 4  # Should still be 4 total
    
    # Test summarizer
    sum_cmd = [sys.executable, "scripts/summarize_nn_v2.py", str(out_dir)]
    res3 = subprocess.run(sum_cmd, capture_output=True, text=True)
    assert res3.returncode == 0, res3.stderr
    
    summary_file = Path("docs/nn_v2/ladder_summary.json")
    assert summary_file.exists()
    
    with open(summary_file) as f:
        summary = json.load(f)
        
    assert "primary" in summary
    assert "estimate" in summary["primary"]
    assert "outcome" in summary
    assert "rung_decisions" in summary
    assert "per_arm" in summary
