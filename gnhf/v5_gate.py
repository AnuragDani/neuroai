#!/usr/bin/env python3
"""v5 completion gate (driver-owned; agents must not edit gnhf/). Prints PASS/FAIL per check.

Usage: python3 gnhf/v5_gate.py   (run from the repository/worktree root). Exit 0 only if all pass.
"""
import json
import subprocess
import sys
from pathlib import Path

PY = "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python"
V = Path("docs/nn_v2/v5")
TASKS = ["V1", "V2", "V3", "V4", "P1", "P2", "P3", "P4", "P5", "P6"]


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).returncode == 0


def main():
    checks = {}
    canon = Path(V / "CANONICAL_LADDER.txt")
    run_dir = canon.read_text().strip() if canon.exists() else ""
    checks["canonical ladder named"] = bool(run_dir) and Path(run_dir, "folds").is_dir()
    checks["verify_ladder PASS on canonical run"] = bool(run_dir) and run(f"python3 gnhf/verify_ladder.py --run {run_dir} --write")
    pf = load(V / "per_fold_metrics.json") or {}
    checks["per-fold metrics for all 18 arms"] = len(pf.get("per_arm", {})) >= 18 and all(
        "per_fold_auroc_mean" in a for a in pf.get("per_arm", {}).values())
    pc = load(V / "positive_control.json") or {}
    checks["positive control through full pipeline (AUROC >= 0.9)"] = (pc.get("donor_auroc") or 0) >= 0.9
    dx = load(V / "below_chance_diagnosis.json") or {}
    checks["below-chance diagnosis has verdict"] = dx.get("verdict") in {"POOLING_ARTEFACT", "PIPELINE_BUG_FIXED", "REAL_ANTI_SIGNAL_EXPLAINED"}
    checks["results doc updated with per-fold section"] = "Per-fold" in Path("docs/nn_v2/NN_V2_RESULTS_2026-09-23.md").read_text(errors="replace")
    checks["professor update v5 exists"] = Path(V / "PROFESSOR_UPDATE_v5.md").exists()
    checks["professor coverage table complete"] = all(f"D{i}" in Path(V / "PROFESSOR_UPDATE_v5.md").read_text(errors="replace")
                                                      for i in range(1, 14)) if Path(V / "PROFESSOR_UPDATE_v5.md").exists() else False
    checks["paper checker passes"] = run(f"{PY} paper/check_paper.py")
    checks["draft carries verified CI"] = run("python3 gnhf/check_evidence.py docs/nn_v2/ladder_verification.json "
                                              "--in paper/draft.md primary_recomputed.ci")
    checks["draft mentions per-fold AUROC"] = "per-fold auroc" in Path("paper/draft.md").read_text(errors="replace").lower()
    checks["full test suite passes"] = run(f"PYTHONPATH=src:scripts {PY} -m pytest -q")
    st = {t: (Path("tasks/nn/status") / t).read_text().strip() if (Path("tasks/nn/status") / t).exists() else "MISSING"
          for t in TASKS}
    checks["all v5 tasks resolved"] = all(s.startswith(("DONE", "NOT_NEEDED", "BLOCKED")) for s in st.values())
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    print("V5_GATE", "PASS" if all(checks.values()) else "FAIL")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
