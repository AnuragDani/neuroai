#!/usr/bin/env python3
"""v6 completion gate (driver-owned; agents must not edit gnhf/). Exit 0 only if all checks pass."""
import json
import subprocess
import sys
from pathlib import Path

PY = "/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python"
V6 = Path("docs/nn_v2/v6")
RUN4 = "reports/generated/nn_20260923/ladder_v4_chr21forced"
TASKS = ["X1", "X2", "X3", "X4", "X5", "X6", "X7"]


def load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def text(p):
    return Path(p).read_text(errors="replace") if Path(p).exists() else ""


def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).returncode == 0


def main():
    c = {}
    amend = text("configs/nn_protocol_v2_amendment_chr21forced.json")
    c["X1 amendment names chr21 + n_hvg"] = "chr21" in amend and "n_hvg" in amend
    c["X1 chr21-forced ladder has 450 fold files"] = len(list(Path(RUN4, "folds").glob("*.json"))) >= 450
    c["X2 chr21-forced ladder verifies (no --write)"] = run(
        f"python3 gnhf/verify_ladder.py --run {RUN4} --summary {V6}/ladder_v4_summary.json")
    canon = text("docs/nn_v2/v5/CANONICAL_LADDER.txt").strip()
    c["canonical ladder unchanged (ladder_v3)"] = canon == "reports/generated/nn_20260923/ladder_v3"
    c["canonical ladder still verifies"] = run(f"python3 gnhf/verify_ladder.py --run {canon}")
    pfc = load(V6 / "per_fold_contrast.json") or {}
    c["X3 per-fold contrast has estimate + ci"] = pfc.get("estimate") is not None and len(pfc.get("ci") or []) == 2
    det = load(V6 / "detectability.json") or {}
    c["X4 detectability has min_detectable_delta"] = "min_detectable_delta" in det
    res = text("docs/nn_v2/NN_V2_RESULTS_2026-09-23.md")
    c["X5 results doc has chr21-forced + detectability"] = "chr21-forced" in res and "Detectability" in res
    c["X5 professor update v6 exists"] = (V6 / "PROFESSOR_UPDATE_v6.md").exists()
    draft = text("paper/draft.md")
    c["X6 draft label DRAFT_V3"] = "DRAFT_V3_COMPLETE" in draft
    c["X6 draft mentions detectability + chr21-forced"] = "detectab" in draft.lower() and "chr21-forced" in draft
    c["X6 paper checker passes"] = run(f"{PY} paper/check_paper.py")
    c["X6 draft carries verified primary CI"] = run(
        "python3 gnhf/check_evidence.py docs/nn_v2/ladder_verification.json --in paper/draft.md primary_recomputed.ci")
    c["full test suite passes"] = run(f"PYTHONPATH=src:scripts {PY} -m pytest -q")
    main_repo = "/Users/anuragdani/Github/niw-eb1a/P22"
    c["X7 finish-base merged into gnhf/p22-nn-cellstate"] = run(
        f"git -C {main_repo} merge-base --is-ancestor codex/p22-nn-finish-base gnhf/p22-nn-cellstate")
    c["X7 integration branch pushed"] = run(
        f"test \"$(git -C {main_repo} rev-parse gnhf/p22-nn-cellstate)\" = \"$(git -C {main_repo} rev-parse origin/gnhf/p22-nn-cellstate)\"")
    st = {t: text(f"tasks/nn/status/{t}").strip() for t in TASKS}
    c["all v6 tasks resolved"] = all(s.startswith(("DONE", "NOT_NEEDED", "BLOCKED")) for s in st.values())
    for k, v in c.items():
        print(("PASS " if v else "FAIL ") + k)
    print("V6_GATE", "PASS" if all(c.values()) else "FAIL")
    return 0 if all(c.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
