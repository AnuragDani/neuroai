#!/usr/bin/env python3
"""P1/N13: held-out faithfulness against the canonical ladder (faithfulness_v3)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_OUT = ROOT / "reports/generated/nn_20260923/faithfulness_v3"
DOCS_JSON = ROOT / "docs/nn_v2/faithfulness.json"
DOCS_MD = ROOT / "docs/nn_v2/FAITHFULNESS.md"
LADDER_MD = ROOT / "docs/nn_v2/LADDER.md"
RUNNER = ROOT / "scripts/run_nn_v2_faithfulness.py"
PY = Path("/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python")
PID_FILE = DEFAULT_OUT / "run.pid"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def assert_ladder_has_models(ladder: Path, arms: tuple[str, ...] = (
    "R3_ca",
    "R3_tc",
    "R3_gated",
    "R4_ca",
)) -> dict:
    models = ladder / "models"
    if not models.is_dir():
        raise RuntimeError(f"missing models dir: {models}")
    counts = {arm: len(list((models / arm).glob("r*_f*.pt"))) for arm in arms}
    for arm, n in counts.items():
        if n != 25:
            raise RuntimeError(f"{ladder}: expected 25 {arm} models, got {n}")
    return {"n_models_per_arm": 25, "arms": list(arms), "ladder": str(ladder)}


def rewrite_pc_reason(payload: dict, ladder: Path) -> dict:
    """Replace hard-coded ladder_v2 PC wording with the actual source run name."""
    name = ladder.name
    decision = dict(payload.get("decision") or {})
    decision["pc_reason"] = (
        f"No saved planted S4/S5 δ=1.0 fold models under {name}; "
        "PC not refit in this run. I3 tags are reported but pairing "
        "claims remain provisional without PC sensitivity."
    )
    out = dict(payload)
    out["decision"] = decision
    out["source_run"] = str(ladder.resolve())
    return out


def rewrite_markdown(md_text: str, ladder: Path, payload: dict) -> str:
    lines = md_text.splitlines()
    if lines:
        lines[2] = (
            f"Source models: `{ladder.resolve()}` "
            f"(canonical {ladder.name}; not copied into finish-base)."
        )
    # Keep decision block in sync with rewritten payload.
    tags = ", ".join(payload["decision"].get("tags") or []) or "(none)"
    for i, line in enumerate(lines):
        if line.startswith("**Decision tags:**"):
            lines[i] = f"**Decision tags:** {tags}."
        if line.startswith("**PC:**"):
            lines[i] = (
                f"**PC:** {payload['decision']['pc_status']} — "
                f"{payload['decision']['pc_reason']}"
            )
        if line.startswith("**NC exact zero:**"):
            lines[i] = f"**NC exact zero:** `{payload['decision']['nc_exact_zero']}`."
    return "\n".join(lines) + "\n"


def publish(run_out: Path, ladder: Path) -> dict:
    src_json = run_out / "faithfulness.json"
    src_md = run_out / "FAITHFULNESS.md"
    if not src_json.is_file():
        raise RuntimeError(f"missing {src_json}")
    payload = rewrite_pc_reason(json.loads(src_json.read_text()), ladder)
    if not payload.get("decision", {}).get("nc_exact_zero"):
        raise RuntimeError("N13 acceptance failed: NC not exact zero")
    DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    if src_md.is_file():
        DOCS_MD.write_text(rewrite_markdown(src_md.read_text(), ladder, payload))
    else:
        # Minimal fallback if runner skipped md (e.g. smoke).
        DOCS_MD.write_text(
            "# Faithfulness interventions (N13)\n\n"
            f"Source models: `{ladder.resolve()}`.\n\n"
            f"**NC exact zero:** `{payload['decision']['nc_exact_zero']}`.\n"
            f"**Decision tags:** {', '.join(payload['decision'].get('tags') or [])}.\n"
            f"**PC:** {payload['decision']['pc_status']} — "
            f"{payload['decision']['pc_reason']}\n"
        )
    # Keep a rewritten copy beside the run output too.
    src_json.write_text(json.dumps(payload, indent=2) + "\n")
    return {
        "wrote": str(DOCS_JSON),
        "tags": payload["decision"].get("tags"),
        "nc": payload["decision"].get("nc_exact_zero"),
        "source_run": payload["source_run"],
    }


def update_ladder_md(payload: dict) -> None:
    if not LADDER_MD.is_file():
        return
    text = LADDER_MD.read_text()
    tags = ", ".join(f"`{t}`" for t in payload["decision"].get("tags") or [])
    source = payload.get("source_run", "")
    name = Path(source).name if source else "canonical"
    section = (
        "## Faithfulness interventions (N13)\n\n"
        f"Held-out interventions on {name} fold models (R3_ca/R3_tc/R3_gated/R4_ca): "
        f"NC Δ = 0 exact. Tags {tags}. "
        "Attention knockout (I4), uniform MIL (I5), and gate clamps (I6) CIs "
        "that include 0 are not claimed as used. Planted PC not run "
        f"(no saved S4/S5 models under {name}). "
        "Details: `docs/nn_v2/faithfulness.json`, `docs/nn_v2/FAITHFULNESS.md`.\n"
    )
    start = text.find("## Faithfulness interventions (N13)")
    if start < 0:
        return
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    LADDER_MD.write_text(text[:start] + section + "\n" + text[end:].lstrip("\n"))


def run_faithfulness(
    ladder: Path,
    out: Path,
    *,
    smoke: bool = False,
    i3_draws: int = 20,
    bootstrap_draws: int = 1000,
) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PY),
        str(RUNNER),
        "--run",
        str(ladder),
        "--out",
        str(out),
        "--i3-draws",
        str(i3_draws),
        "--bootstrap-draws",
        str(bootstrap_draws),
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
    logging.info("Running N13 faithfulness -> %s from %s", out, ladder)
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)
    return out / ("faithfulness_smoke.json" if smoke else "faithfulness.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run", action="store_true", help="Execute faithfulness runner")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Copy results into docs/nn_v2")
    parser.add_argument("--update-ladder-md", action="store_true")
    parser.add_argument("--i3-draws", type=int, default=20)
    parser.add_argument("--bootstrap-draws", type=int, default=1000)
    args = parser.parse_args(argv)

    ladder = (args.ladder or resolve_canonical_ladder()).resolve()
    assert_ladder_has_models(ladder)

    if args.run:
        args.out.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()) + "\n")
        try:
            run_faithfulness(
                ladder,
                args.out,
                smoke=args.smoke,
                i3_draws=2 if args.smoke else args.i3_draws,
                bootstrap_draws=50 if args.smoke else args.bootstrap_draws,
            )
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()

    result = None
    if args.publish:
        # Smoke writes faithfulness_smoke.json; promote for publish only if full json missing.
        full = args.out / "faithfulness.json"
        smoke_path = args.out / "faithfulness_smoke.json"
        if not full.is_file() and smoke_path.is_file() and args.smoke:
            shutil.copy2(smoke_path, full)
        result = publish(args.out, ladder)
        print(json.dumps(result, indent=2))

    if args.update_ladder_md:
        payload = json.loads(DOCS_JSON.read_text()) if DOCS_JSON.is_file() else None
        if payload is None and result is not None:
            payload = json.loads(DOCS_JSON.read_text())
        if payload is None:
            raise SystemExit("publish first so docs/nn_v2/faithfulness.json exists")
        update_ladder_md(payload)

    if not (args.run or args.publish or args.update_ladder_md):
        print(json.dumps({"ladder": str(ladder), "models_ok": True}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
