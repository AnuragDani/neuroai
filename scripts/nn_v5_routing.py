#!/usr/bin/env python3
"""P1/N17: routing/attention description against the canonical ladder_v3."""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_OUT = ROOT / "reports/generated/nn_20260923/routing_v3"
DOCS_JSON = ROOT / "docs/nn_v2/routing_attention.json"
DOCS_MD = ROOT / "docs/nn_v2/ROUTING_ATTENTION.md"
LADDER_MD = ROOT / "docs/nn_v2/LADDER.md"
FAITH_JSON = ROOT / "docs/nn_v2/faithfulness.json"
RUNNER = ROOT / "scripts/describe_nn_v2_attention.py"
PY = Path("/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python")
DEFAULT_ARMS = ("R3_gated", "R3_ca", "R4_ca")
PID_FILE = DEFAULT_OUT / "run.pid"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load_describe():
    spec = importlib.util.spec_from_file_location("describe_nn_v2_attention", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    return (path if path.is_absolute() else ROOT / path).resolve()


def assert_ladder_has_models(
    ladder: Path, arms: tuple[str, ...] = DEFAULT_ARMS
) -> dict:
    models = ladder / "models"
    if not models.is_dir():
        raise RuntimeError(f"missing models dir: {models}")
    counts = {arm: len(list((models / arm).glob("r*_f*.pt"))) for arm in arms}
    for arm, n in counts.items():
        if n != 25:
            raise RuntimeError(f"{ladder}: expected 25 {arm} models, got {n}")
    return {"n_models_per_arm": 25, "arms": list(arms), "ladder": str(ladder)}


def assert_faithfulness_binds_ladder(
    ladder: Path, faith_json: Path = FAITH_JSON
) -> dict:
    if not faith_json.is_file():
        raise RuntimeError(f"missing {faith_json}")
    payload = json.loads(faith_json.read_text())
    source = Path(payload.get("source_run") or "").resolve()
    if source != ladder.resolve():
        raise RuntimeError(f"faithfulness source_run {source} != canonical {ladder}")
    if payload.get("status") != "DONE":
        raise RuntimeError(f"N13 status is {payload.get('status')!r}, need DONE")
    return payload


def rewrite_markdown(md_text: str, ladder: Path) -> str:
    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("Source models:"):
            lines[i] = (
                f"Source models: `{ladder.resolve()}` "
                f"(canonical {ladder.name}; not copied into finish-base)."
            )
            break
    return "\n".join(lines) + ("\n" if md_text.endswith("\n") else "")


def publish(run_out: Path, ladder: Path) -> dict:
    src_json = run_out / "routing_attention.json"
    src_md = run_out / "ROUTING_ATTENTION.md"
    if not src_json.is_file():
        raise RuntimeError(f"missing {src_json}")
    payload = json.loads(src_json.read_text())
    if int(payload.get("folds_used") or 0) != 75 and not payload.get("smoke"):
        raise RuntimeError(
            f"expected folds_used=75 for full N17, got {payload.get('folds_used')}"
        )
    tags = payload.get("readout_tags") or {}
    if len(tags) != 3:
        raise RuntimeError(f"expected 3 readout tags, got {tags}")
    payload["source_run"] = str(ladder.resolve())
    DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    if src_md.is_file():
        DOCS_MD.write_text(rewrite_markdown(src_md.read_text(), ladder))
    else:
        mod = _load_describe()
        mod.write_markdown(payload, DOCS_MD)
        DOCS_MD.write_text(rewrite_markdown(DOCS_MD.read_text(), ladder))
    src_json.write_text(json.dumps(payload, indent=2) + "\n")
    return {
        "wrote": str(DOCS_JSON),
        "folds_used": payload.get("folds_used"),
        "readout_tags": tags,
        "source_run": payload["source_run"],
        "smoke": bool(payload.get("smoke")),
    }


def update_ladder_md(payload: dict) -> None:
    if not LADDER_MD.is_file():
        return
    source = payload.get("source_run", "")
    name = Path(source).name if source else "canonical"
    tags = payload.get("readout_tags") or {}
    tag_list = ", ".join(f"`{t}`" for t in sorted(set(tags.values()))) or "`NOT_SHOWN_USED`"
    n_folds = int(payload.get("folds_used") or 0)
    all_not_shown = set(tags.values()) == {"NOT_SHOWN_USED"}
    tag_phrase = (
        "**NOT_SHOWN_USED** because mapped N13 interventions I4 (CA / program-CA "
        "attention knockout) and I6 (gated route clamps) have Δ log-loss CIs that "
        "include 0"
        if all_not_shown
        else f"{tag_list} from mapped N13 I4/I6 interventions"
    )
    section = (
        "## Routing / attention (N17)\n\n"
        f"Per-cell-type descriptive readouts from {name} fold models "
        f"({n_folds} folds: R3_gated / R3_ca / R4_ca). All three readouts tagged "
        f"{tag_phrase}. N13 `ATAC_USED` (I1) does not authorize attention/routing "
        "claims. Evidence: `docs/nn_v2/routing_attention.json`, "
        "`docs/nn_v2/ROUTING_ATTENTION.md`.\n"
    )
    text = LADDER_MD.read_text()
    start = text.find("## Routing / attention (N17)")
    if start < 0:
        return
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    LADDER_MD.write_text(text[:start] + section + "\n" + text[end:].lstrip("\n"))


def run_routing(
    ladder: Path,
    out: Path,
    *,
    smoke: bool = False,
    arms: tuple[str, ...] = DEFAULT_ARMS,
) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(PY),
        str(RUNNER),
        "--run",
        str(ladder),
        "--out-docs",
        str(out),
        "--faithfulness",
        str(FAITH_JSON),
        "--arms",
        ",".join(arms),
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
    logging.info("Running N17 routing -> %s from %s (smoke=%s)", out, ladder, smoke)
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)
    return out / "routing_attention.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run", action="store_true", help="Execute describe runner")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--update-ladder-md", action="store_true")
    args = parser.parse_args(argv)

    ladder = (args.ladder or resolve_canonical_ladder()).resolve()
    assert_ladder_has_models(ladder)
    assert_faithfulness_binds_ladder(ladder)

    if args.run:
        args.out.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()) + "\n")
        try:
            run_routing(ladder, args.out, smoke=args.smoke)
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()

    result = None
    if args.publish:
        result = publish(args.out, ladder)
        print(json.dumps(result, indent=2))

    if args.update_ladder_md:
        if not DOCS_JSON.is_file():
            raise SystemExit("publish first so docs/nn_v2/routing_attention.json exists")
        update_ladder_md(json.loads(DOCS_JSON.read_text()))

    if not (args.run or args.publish or args.update_ladder_md):
        print(
            json.dumps(
                {
                    "ladder": str(ladder),
                    "models_ok": True,
                    "faithfulness_ok": True,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
