#!/usr/bin/env python3
"""P1/N15: OOF cell-score export against the canonical ladder (spectrum_v3)."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_OUT = ROOT / "reports/generated/nn_20260923/spectrum_v3"
DOCS_JSON = ROOT / "docs/nn_v2/cell_scores_export.json"
DOCS_MD = ROOT / "docs/nn_v2/CELL_SCORES.md"
LADDER_MD = ROOT / "docs/nn_v2/LADDER.md"
EXPORT = ROOT / "scripts/export_nn_v2_cell_scores.py"
PY = Path("/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python")
PID_FILE = DEFAULT_OUT / "run.pid"
N15_ARMS = ("R1_ca", "R3_ca", "R3_tc", "R4_ca")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    return (path if path.is_absolute() else ROOT / path).resolve()


def resolve_chr21_excluded(ladder: Path) -> Path:
    sibling = ladder.parent / "chr21_excluded_v3"
    return (sibling if sibling.is_dir() else ladder.parent / "chr21_excluded").resolve()


def assert_ladder_has_models(
    ladder: Path, arms: tuple[str, ...] = N15_ARMS
) -> dict[str, Any]:
    models = ladder / "models"
    if not models.is_dir():
        raise RuntimeError(f"missing models dir: {models}")
    counts = {arm: len(list((models / arm).glob("r*_f*.pt"))) for arm in arms}
    for arm, n in counts.items():
        if n != 25:
            raise RuntimeError(f"{ladder}: expected 25 {arm} models, got {n}")
    return {"n_models_per_arm": 25, "arms": list(arms), "ladder": str(ladder)}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _attach_hashes(block: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(block, dict) or block.get("status") in {"DEFERRED", "NOT_NEEDED"}:
        return block
    out = dict(block)
    for key, hash_key in (
        ("cell_scores_path", "cell_scores_sha256"),
        ("donor_celltype_scores_path", "donor_celltype_scores_sha256"),
    ):
        path = Path(out[key])
        if path.is_file():
            out[hash_key] = _sha256(path)
    return out


def _chr21_line(chr21: dict[str, Any]) -> str:
    if "status" in chr21:
        return f"Chr21-excluded arm export: `{chr21['status']}`"
    if "n_cell_arm_rows" in chr21:
        return (
            f"Chr21-excluded export: {chr21['n_cell_arm_rows']} cell×arm rows from "
            f"`{chr21.get('source_run')}`."
        )
    return "Chr21-excluded arm export: unknown."


def render_markdown(payload: dict[str, Any], ladder: Path) -> str:
    main = payload.get("ladder_export") or payload.get("ladder_v2_export") or {}
    chr21 = payload.get("chr21_excluded_export") or {}
    return "\n".join(
        [
            "# N15 out-of-fold cell scores",
            "",
            f"Source models: `{ladder.resolve()}` "
            f"(canonical {ladder.name}; not copied into finish-base).",
            "",
            "| Item | Value |",
            "|---|---|",
            f"| Arms | {', '.join(main.get('arms') or [])} |",
            f"| Folds used | {main.get('folds_used')} |",
            f"| Cell×arm rows | {main.get('n_cell_arm_rows')} |",
            f"| Repeats per cell×arm | 5 (asserted={main.get('five_appearances_asserted')}) |",
            f"| Donor×cell-type rows | {main.get('n_donor_celltype_rows')} |",
            f"| R3_ca parameter_count | {(main.get('parameter_counts') or {}).get('R3_ca')} |",
            f"| n_library / n_batch | {main.get('n_library')} / {main.get('n_batch')} |",
            "",
            f"Outputs: `{main.get('cell_scores_path')}`, "
            f"`{main.get('donor_celltype_scores_path')}`, "
            f"`docs/nn_v2/cell_scores_export.json`.",
            "",
            _chr21_line(chr21 if isinstance(chr21, dict) else {}),
            "",
        ]
    )


def publish(spectrum_dir: Path, ladder: Path, *, smoke: bool = False) -> dict[str, Any]:
    name = "cell_scores_export_smoke.json" if smoke else "cell_scores_export.json"
    src = spectrum_dir / name
    if not src.is_file():
        raise RuntimeError(f"missing export evidence JSON: {src}")
    payload = json.loads(src.read_text())
    main = payload.get("ladder_export") or payload.get("ladder_v2_export")
    if not isinstance(main, dict):
        raise RuntimeError("export evidence missing ladder_export block")
    if str(Path(main["source_run"]).resolve()) != str(ladder.resolve()):
        raise RuntimeError(f"export source_run {main['source_run']} != canonical {ladder}")
    if not smoke:
        if int(main.get("n_cell_arm_rows") or 0) != 120_000:
            raise RuntimeError(f"expected 120000 rows, got {main.get('n_cell_arm_rows')}")
        if not main.get("five_appearances_asserted"):
            raise RuntimeError("five_appearances_asserted missing/false")
    payload["ladder_export"] = _attach_hashes(main)
    payload["ladder_v2_export"] = payload["ladder_export"]
    payload["chr21_excluded_export"] = _attach_hashes(payload.get("chr21_excluded_export"))
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    DOCS_JSON.write_text(text)
    md = render_markdown(payload, ladder)
    DOCS_MD.write_text(md)
    (spectrum_dir / "cell_scores_export.json").write_text(text)
    (spectrum_dir / "CELL_SCORES.md").write_text(md)
    chr21 = payload.get("chr21_excluded_export") or {}
    return {
        "wrote": str(DOCS_JSON),
        "source_run": main["source_run"],
        "n_cell_arm_rows": main.get("n_cell_arm_rows"),
        "chr21_status": chr21.get("status")
        or ("EXPORTED" if "n_cell_arm_rows" in chr21 else None),
    }


def update_ladder_md(payload: dict[str, Any]) -> None:
    if not LADDER_MD.is_file():
        return
    text = LADDER_MD.read_text()
    main = payload.get("ladder_export") or payload.get("ladder_v2_export") or {}
    source = Path(main.get("source_run") or "")
    chr21 = payload.get("chr21_excluded_export") or {}
    chr21_bit = _chr21_line(chr21 if isinstance(chr21, dict) else {})
    section = (
        "## Out-of-fold cell scores (N15)\n\n"
        f"Exported per-cell logits and MIL attention for "
        f"{', '.join(main.get('arms') or [])} from {source.name} fold models "
        f"({main.get('folds_used')} folds; every cell appears exactly 5 times per arm "
        f"before averaging). Compact donor×cell-type means in "
        f"`docs/nn_v2/donor_celltype_scores.csv.gz`. Full table: "
        f"`{main.get('cell_scores_path')}`. Evidence: "
        f"`docs/nn_v2/cell_scores_export.json`, `docs/nn_v2/CELL_SCORES.md`. "
        f"{chr21_bit}\n"
    )
    start = text.find("## Out-of-fold cell scores (N15)")
    if start < 0:
        return
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    LADDER_MD.write_text(text[:start] + section + "\n" + text[end:].lstrip("\n"))


def _promote_evidence(docs_staging: Path, spectrum_dir: Path, *, smoke: bool) -> Path:
    evid_name = "cell_scores_export_smoke.json" if smoke else "cell_scores_export.json"
    evid = docs_staging / evid_name
    if not evid.is_file():
        raise RuntimeError(f"exporter did not write {evid}")
    if not smoke:
        for name in (
            "donor_celltype_scores.csv.gz",
            "donor_celltype_scores_chr21_excluded.csv.gz",
        ):
            src = docs_staging / name
            if src.is_file():
                (ROOT / "docs/nn_v2" / name).write_bytes(src.read_bytes())
    payload = json.loads(evid.read_text())
    for key in ("ladder_export", "ladder_v2_export", "chr21_excluded_export"):
        block = payload.get(key)
        if not isinstance(block, dict) or "donor_celltype_scores_path" not in block:
            continue
        promoted = ROOT / "docs/nn_v2" / Path(block["donor_celltype_scores_path"]).name
        if promoted.is_file():
            block["donor_celltype_scores_path"] = str(promoted.relative_to(ROOT))
    out = spectrum_dir / evid_name
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return out


def run_export(
    ladder: Path,
    spectrum_dir: Path,
    *,
    smoke: bool = False,
    include_chr21_excluded: bool = True,
    chr21_run: Path | None = None,
) -> Path:
    spectrum_dir.mkdir(parents=True, exist_ok=True)
    docs_staging = spectrum_dir / "docs_staging"
    docs_staging.mkdir(parents=True, exist_ok=True)
    chr21 = chr21_run or resolve_chr21_excluded(ladder)
    cmd = [
        str(PY), str(EXPORT),
        "--run", str(ladder),
        "--spectrum-dir", str(spectrum_dir),
        "--out-docs", str(docs_staging),
        "--chr21-excluded-run", str(chr21),
    ]
    if include_chr21_excluded:
        cmd.append("--include-chr21-excluded")
    if smoke:
        cmd.append("--smoke")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}:{ROOT / 'scripts'}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "TORCH_NUM_THREADS"):
        env[k] = "1"
    logging.info("Running N15 cell-score export -> %s from %s", spectrum_dir, ladder)
    subprocess.run(cmd, check=True, cwd=str(ROOT), env=env)
    return _promote_evidence(docs_staging, spectrum_dir, smoke=smoke)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--chr21-excluded-run", type=Path, default=None)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--skip-chr21-excluded", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--update-ladder-md", action="store_true")
    args = parser.parse_args(argv)

    ladder = (args.ladder or resolve_canonical_ladder()).resolve()
    assert_ladder_has_models(ladder)

    if args.run:
        args.out.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()) + "\n")
        try:
            run_export(
                ladder, args.out, smoke=args.smoke,
                include_chr21_excluded=not args.skip_chr21_excluded,
                chr21_run=args.chr21_excluded_run,
            )
        finally:
            if PID_FILE.exists():
                PID_FILE.unlink()

    if args.publish:
        print(json.dumps(publish(args.out, ladder, smoke=args.smoke), indent=2))

    if args.update_ladder_md:
        if not DOCS_JSON.is_file():
            raise SystemExit("publish first so docs/nn_v2/cell_scores_export.json exists")
        update_ladder_md(json.loads(DOCS_JSON.read_text()))

    if not (args.run or args.publish or args.update_ladder_md):
        print(json.dumps({
            "ladder": str(ladder),
            "chr21_excluded": str(args.chr21_excluded_run or resolve_chr21_excluded(ladder)),
            "models_ok": True,
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
