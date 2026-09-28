"""V4: canonical ladder pointer and verify_ladder agreement after pipeline fix."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
EXPECTED = "reports/generated/nn_20260923/ladder_v3"


def test_canonical_ladder_points_at_v3():
    assert POINTER.is_file()
    assert POINTER.read_text().strip() == EXPECTED


def test_ladder_v3_has_450_folds_and_run_record():
    run = ROOT / EXPECTED
    folds = list((run / "folds").glob("*.json"))
    assert len(folds) == 450
    rec = json.loads((run / "run.json").read_text())
    assert rec["folds_expected"] == 450
    assert rec["folds_done"] == 450
    assert rec["failures"] == []


def test_verify_ladder_passes_on_canonical():
    run = POINTER.read_text().strip()
    proc = subprocess.run(
        [sys.executable, str(ROOT / "gnhf/verify_ladder.py"), "--run", run],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert '"verdict": "PASS"' in proc.stdout
