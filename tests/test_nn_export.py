import pytest
import subprocess
import sys

def test_nn_export():
    cmd = [sys.executable, "scripts/export_nn_v2_cell_scores.py", "--help"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
