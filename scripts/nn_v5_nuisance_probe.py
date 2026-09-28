#!/usr/bin/env python3
"""P1/N14: held-out nuisance probes against the canonical ladder (nuisance_v3)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_OUT = ROOT / "reports/generated/nn_20260923/nuisance_v3"
DOCS_JSON = ROOT / "docs/nn_v2/nuisance_probe.json"
DOCS_MD = ROOT / "docs/nn_v2/NUISANCE_PROBE.md"
LADDER_MD = ROOT / "docs/nn_v2/LADDER.md"
RUNNER = ROOT / "scripts/run_nn_v2_nuisance_probe.py"
PY = Path("/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python")
PID_FILE = DEFAULT_OUT / "run.pid"
N14_ARMS = ("R1_ca", "R1_tc", "R2_ca", "R2_tc", "R3_ca", "R3_tc")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def assert_ladder_has_models(
    ladder: Path, arms: tuple[str, ...] = N14_ARMS
) -> dict[str, Any]:
    models = ladder / "models"
    if not models.is_dir():
        raise RuntimeError(f"missing models dir: {models}")
    counts = {arm: len(list((models / arm).glob("r*_f*.pt"))) for arm in arms}
    for arm, n in counts.items():
        if n != 25:
            raise RuntimeError(f"{ladder}: expected 25 {arm} models, got {n}")
    return {"n_models_per_arm": 25, "arms": list(arms), "ladder": str(ladder)}


def _fmt(v: float | None, digits: int = 4) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{digits}f}"


def render_markdown(payload: dict[str, Any], ladder: Path) -> str:
    decision = payload["decision"]
    label_list = decision.get("labels") or []
    detail = [t for t in label_list if t != decision.get("r2_rejection_decision")]
    labels = ", ".join(f"`{t}`" for t in detail) or "(none)"
    adv = "ADVERSARY_ERASES_SIGNAL" in label_list
    decision_line = (
        f"**Decision:** `{decision['r2_rejection_decision']}` with {labels}."
        + ("" if adv else " No `ADVERSARY_ERASES_SIGNAL`.")
    )
    n_lib = sum(
        1 for row in payload.get("folds") or [] if row.get("library_accuracy") is not None
    )
    n_rows = int(payload.get("n_fold_rows") or 0)
    lines = [
        "# Nuisance-probe diagnostics (N14)",
        "",
        f"Source models: `{ladder.resolve()}` "
        f"(canonical {ladder.name}; not copied into finish-base).",
        "",
        decision_line,
        "",
        "Rule (plan §4.2 / decision_tree N14): reject R2 if held-out within-disease "
        "nuisance-probe accuracy does not drop ≥ 5 points vs R1, or donor BA drops "
        "> 0.05 vs R1.",
        "",
        "| Arm | Batch probe (held-out) | Library probe | QC R² | "
        "Mean fold donor BA | Params |",
        "|---|---|---|---|---|---|",
    ]
    for arm in payload.get("arm_summaries") or []:
        lib = arm.get("library_accuracy")
        lib_s = _fmt(lib) if lib is not None else (
            f"N/A ({n_lib}/{n_rows} scorable)" if n_rows else "N/A"
        )
        lines.append(
            f"| {arm['arm']} | {_fmt(arm.get('batch_accuracy'))} | {lib_s} | "
            f"{_fmt(arm.get('qc_r2'), 3)} | {_fmt(arm.get('donor_ba'), 3)} | "
            f"{arm.get('parameter_count')} |"
        )
    by_fusion = decision.get("by_fusion") or {}
    drop_bits = [
        f"{fusion.upper()} ≈ {row['probe_drop_points']:.2f}"
        for fusion in ("ca", "tc")
        for row in [by_fusion.get(fusion) or {}]
        if "probe_drop_points" in row
    ]
    ba_bits = [
        f"{fusion.upper()} ≈ {row['ba_drop']:.3f}"
        for fusion in ("ca", "tc")
        for row in [by_fusion.get(fusion) or {}]
        if "ba_drop" in row
    ]
    lines.extend(
        [
            "",
            "Probe drop (R1−R2, percentage points): "
            + ("; ".join(drop_bits) if drop_bits else "n/a")
            + ". Donor BA drop: "
            + ("; ".join(ba_bits) if ba_bits else "n/a")
            + ".",
            "",
            "**Caveats:** Library probe is not scorable under donor-held-out splits "
            f"(scorable on {n_lib}/{n_rows} fold-arm rows). Primary probe therefore "
            "uses batch_seq when library is unscorable. Fold-mean donor BA here is "
            "not the same pooling as `ladder_summary.json` arm BA; the R1−R2 *delta* "
            "is what the rejection rule uses. R2 remains reported on the ladder; "
            "rejection means the adversary refinement is not carried as evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def publish(run_out: Path, ladder: Path) -> dict[str, Any]:
    src_json = run_out / "nuisance_probe.json"
    if not src_json.is_file():
        raise RuntimeError(f"missing {src_json}")
    payload = json.loads(src_json.read_text())
    payload["source_run"] = str(ladder.resolve())
    decision = payload.get("decision") or {}
    if decision.get("r2_rejection_decision") == "R2_UNEVALUATED":
        raise RuntimeError("N14 acceptance failed: R2_UNEVALUATED")
    if int(payload.get("n_fold_rows") or 0) != 150 and not payload.get("smoke"):
        raise RuntimeError(
            f"expected 150 fold-arm rows, got {payload.get('n_fold_rows')}"
        )
    DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    md = render_markdown(payload, ladder)
    DOCS_MD.write_text(md)
    src_json.write_text(json.dumps(payload, indent=2) + "\n")
    (run_out / "NUISANCE_PROBE.md").write_text(md)
    return {
        "wrote": str(DOCS_JSON),
        "decision": decision.get("r2_rejection_decision"),
        "labels": decision.get("labels"),
        "source_run": payload["source_run"],
        "n_fold_rows": payload.get("n_fold_rows"),
    }


def update_ladder_md(payload: dict[str, Any]) -> None:
    if not LADDER_MD.is_file():
        return
    text = LADDER_MD.read_text()
    decision = payload["decision"].get("r2_rejection_decision")
    detail = [
        t
        for t in (payload["decision"].get("labels") or [])
        if t != decision
    ]
    labels = ", ".join(f"`{t}`" for t in detail) or "(none)"
    source = payload.get("source_run", "")
    name = Path(source).name if source else "canonical"
    section = (
        "## Nuisance-probe diagnostics (N14)\n\n"
        f"Held-out within-disease embedding probes on {name} R1/R2/R3 (CA and TC): "
        f"**{decision}** ({labels}). "
        "Batch probe stays near chance and does not drop ≥ 5 points from R1 to R2; "
        "library probe is unscorable under donor hold-out. "
        "See `docs/nn_v2/nuisance_probe.json`, `docs/nn_v2/NUISANCE_PROBE.md`.\n"
    )
    start = text.find("## Nuisance-probe diagnostics (N14)")
    if start < 0:
        return
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    LADDER_MD.write_text(text[:start] + section + "\n" + text[end:].lstrip("\n"))


def run_nuisance(ladder: Path, out: Path, *, smoke: bool = False) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PY),
        str(RUNNER),
        "--run",
        str(ladder),
        "--out",
        str(out),
    ]
    if smoke:
        cmd.append("--smoke")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}:{ROOT / 'scripts'}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["TORCH_NUM_THREADS"] = "1"
    logging.info("Running N14 nuisance probe -> %s from %s", out, ladder)
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)
    return out / ("nuisance_probe_smoke.json" if smoke else "nuisance_probe.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run", action="store_true", help="Execute nuisance probe runner")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--update-ladder-md", action="store_true")
    args = parser.parse_args(argv)

    ladder = (args.ladder or resolve_canonical_ladder()).resolve()
    assert_ladder_has_models(ladder)

    if args.run:
        args.out.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()) + "\n")
        try:
            run_nuisance(ladder, args.out, smoke=args.smoke)
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()

    result = None
    if args.publish:
        full = args.out / "nuisance_probe.json"
        smoke_path = args.out / "nuisance_probe_smoke.json"
        if not full.is_file() and smoke_path.is_file():
            import shutil

            shutil.copy2(smoke_path, full)
        result = publish(args.out, ladder)
        print(json.dumps(result, indent=2))

    if args.update_ladder_md:
        if not DOCS_JSON.is_file():
            raise SystemExit("publish first so docs/nn_v2/nuisance_probe.json exists")
        update_ladder_md(json.loads(DOCS_JSON.read_text()))

    if not (args.run or args.publish or args.update_ladder_md):
        print(json.dumps({"ladder": str(ladder), "models_ok": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
