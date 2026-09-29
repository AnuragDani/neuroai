#!/usr/bin/env python3
"""P3: N16-style spectrum on chr21-excluded (N11) per-cell scores.

Because the ladder is DOSAGE_DOMINATED, repeat the cell-state spectrum on
R3_ca scores from chr21_excluded_v3. Writes docs/nn_v2/v5/spectrum_chr21_excluded.json
and a ≤40-line reading. Label SPECTRUM_LOCALIZED:<types> or SPECTRUM_NULL.
No mechanism language.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CANON_POINTER = ROOT / "docs/nn_v2/v5/CANONICAL_LADDER.txt"
DEFAULT_SPECTRUM = ROOT / "reports/generated/nn_20260923/spectrum_v3"
EXPORT_JSON = ROOT / "docs/nn_v2/cell_scores_export.json"
CHR21_EXCLUDED_JSON = ROOT / "docs/nn_v2/chr21_excluded.json"
OUT_JSON = ROOT / "docs/nn_v2/v5/spectrum_chr21_excluded.json"
OUT_MD = ROOT / "docs/nn_v2/v5/SPECTRUM_CHR21_EXCLUDED.md"
PRIMARY_ARM = "R3_ca"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load_analyze():
    path = ROOT / "scripts/analyze_nn_v2_spectrum.py"
    spec = importlib.util.spec_from_file_location("analyze_nn_v2_spectrum", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def resolve_canonical_ladder(pointer: Path = CANON_POINTER) -> Path:
    text = pointer.read_text().strip()
    path = Path(text)
    return (path if path.is_absolute() else ROOT / path).resolve()


def resolve_chr21_scores(spectrum_dir: Path = DEFAULT_SPECTRUM) -> Path:
    path = spectrum_dir / "cell_scores_chr21_excluded.csv.gz"
    if not path.is_file():
        raise RuntimeError(f"missing chr21-excluded export: {path}")
    return path.resolve()


def assert_chr21_export_binds(export_json: Path = EXPORT_JSON) -> dict:
    if not export_json.is_file():
        raise RuntimeError(f"missing {export_json}")
    payload = json.loads(export_json.read_text())
    block = payload.get("chr21_excluded_export") or {}
    source = Path(block.get("source_run") or "").resolve()
    expected = (ROOT / "reports/generated/nn_20260923/chr21_excluded_v3").resolve()
    if source != expected:
        raise RuntimeError(f"chr21 export source_run {source} != {expected}")
    if int(block.get("n_cell_arm_rows") or 0) != 60_000:
        raise RuntimeError(f"expected 60000 rows, got {block.get('n_cell_arm_rows')}")
    return block


def assert_dosage_dominated(path: Path = CHR21_EXCLUDED_JSON) -> str:
    if not path.is_file():
        raise RuntimeError(f"missing {path}")
    payload = json.loads(path.read_text())
    label = str(payload.get("label") or payload.get("decision") or "")
    if "DOSAGE_DOMINATED" not in label:
        raise RuntimeError(f"P3 requires DOSAGE_DOMINATED; got {label!r}")
    return label


def _filter_arm(cells: pd.DataFrame, arm: str) -> pd.DataFrame:
    if "arm" not in cells.columns:
        return cells.copy()
    out = cells.loc[cells["arm"].astype(str) == arm].copy()
    if out.empty:
        raise RuntimeError(f"arm {arm!r} absent from chr21-excluded export")
    return out


def build_reading(payload: dict, *, max_lines: int = 40) -> str:
    """≤40-line factual reading; no mechanism language."""
    call = payload.get("spectrum_call", "SPECTRUM_NULL")
    src = payload.get("source") or {}
    n_elig = len(payload.get("eligible_types") or [])
    sig = [
        r["author_cell_type"]
        for r in payload.get("results") or []
        if r.get("s", {}).get("significant")
    ]
    lines = [
        "# P3: spectrum on chr21-excluded scores",
        "",
        f"Source: `{src.get('cell_scores_path')}` arm `{src.get('arm', PRIMARY_ARM)}` "
        f"(sha256 `{str(src.get('cell_scores_sha256') or '')[:12]}…`; "
        f"N11 run `{Path(str(src.get('chr21_excluded_run') or '')).name}`).",
        "",
        f"Prerequisite: N11 label `{src.get('n11_label', 'DOSAGE_DOMINATED')}`.",
        "",
        f"Call: `{call}`",
        "",
        f"Eligible author cell types: {n_elig}.",
        "",
        "| cell type | n donors DS | n donors CON | diff s | 95% CI | p (Holm) | sig |",
        "| --- | ---: | ---: | ---: | --- | ---: | :---: |",
    ]
    for r in payload.get("results") or []:
        s = r.get("s") or {}
        ci = f"[{s.get('ci_low', float('nan')):.3f}, {s.get('ci_high', float('nan')):.3f}]"
        lines.append(
            f"| {r['author_cell_type']} | {r.get('n_donors_ds')} | {r.get('n_donors_con')} | "
            f"{s.get('diff', float('nan')):.3f} | {ci} | "
            f"{s.get('p_holm', float('nan')):.4f} | "
            f"{'yes' if s.get('significant') else 'no'} |"
        )
    lines += [
        "",
        (
            f"Reading: {'Holm-significant DS−CON types: ' + ', '.join(sig) + '.' if sig else 'no eligible cell type shows a Holm-significant DS−CON difference in donor-mean model score.'} "
            f"Label `{call}`. Cohort-internal only; not external validation."
        ),
        "",
    ]
    text = "\n".join(lines)
    n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    if n_lines > max_lines:
        raise RuntimeError(f"reading has {n_lines} lines; max {max_lines}")
    return text


def run_spectrum(
    *,
    spectrum_dir: Path = DEFAULT_SPECTRUM,
    n_boot: int = 2000,
    n_perm: int = 10000,
    seed: int = 22,
    arm: str = PRIMARY_ARM,
) -> dict:
    mod = _load_analyze()
    ladder = resolve_canonical_ladder()
    n11_label = assert_dosage_dominated()
    export = assert_chr21_export_binds()
    scores_path = resolve_chr21_scores(spectrum_dir)
    cells = pd.read_csv(scores_path)
    block = _filter_arm(cells, arm)
    payload = mod.analyze_cells(block, n_boot=n_boot, n_perm=n_perm, seed=seed)
    payload["arm"] = arm
    sha = mod._sha256(scores_path)
    if sha != export.get("cell_scores_sha256"):
        raise RuntimeError(
            "chr21 cell_scores sha256 mismatch vs cell_scores_export.json "
            f"({sha} != {export.get('cell_scores_sha256')})"
        )
    rel = (
        str(scores_path.relative_to(ROOT))
        if scores_path.is_relative_to(ROOT)
        else str(scores_path)
    )
    payload["source"] = {
        "cell_scores_path": rel,
        "cell_scores_sha256": sha,
        "arm": arm,
        "arms_in_export": sorted(set(cells["arm"].astype(str))) if "arm" in cells else [arm],
        "n_rows_analyzed": int(len(block)),
        "ladder_source": str(ladder.resolve()),
        "chr21_excluded_run": str(
            Path(export.get("source_run") or "").resolve()
        ),
        "export_evidence": "docs/nn_v2/cell_scores_export.json",
        "export_sha256": export.get("cell_scores_sha256"),
        "n11_label": n11_label,
        "n11_evidence": "docs/nn_v2/chr21_excluded.json",
    }
    payload["task"] = "P3"
    payload["label"] = payload["spectrum_call"]
    return payload


def publish(payload: dict, *, out_json: Path = OUT_JSON, out_md: Path = OUT_MD) -> dict:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    out_md.write_text(build_reading(payload))
    return {
        "wrote": str(out_json),
        "reading": str(out_md),
        "spectrum_call": payload.get("spectrum_call"),
        "label": payload.get("label"),
        "n_eligible": len(payload.get("eligible_types") or []),
        "n_lines_reading": out_md.read_text().count("\n") + 1,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spectrum-dir", type=Path, default=DEFAULT_SPECTRUM)
    parser.add_argument("--arm", default=PRIMARY_ARM)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--n-perm", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)

    n_boot = 50 if args.smoke else args.n_boot
    n_perm = 100 if args.smoke else args.n_perm
    payload = None

    if args.run:
        logging.info(
            "P3 spectrum chr21-excluded arm=%s n_boot=%d n_perm=%d",
            args.arm, n_boot, n_perm,
        )
        payload = run_spectrum(
            spectrum_dir=args.spectrum_dir,
            n_boot=n_boot,
            n_perm=n_perm,
            seed=args.seed,
            arm=args.arm,
        )
        staging = args.spectrum_dir / (
            "spectrum_chr21_excluded_smoke.json" if args.smoke else "spectrum_chr21_excluded.json"
        )
        staging.write_text(json.dumps(payload, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "spectrum_call": payload["spectrum_call"],
                    "label": payload["label"],
                    "n_eligible": len(payload.get("eligible_types") or []),
                    "staging": str(staging),
                },
                indent=2,
            )
        )

    if args.publish:
        if payload is None:
            staging = args.spectrum_dir / "spectrum_chr21_excluded.json"
            if not staging.is_file():
                raise SystemExit(f"missing {staging}; run with --run first")
            payload = json.loads(staging.read_text())
        print(json.dumps(publish(payload), indent=2))

    if not (args.run or args.publish):
        print(
            json.dumps(
                {
                    "ladder": str(resolve_canonical_ladder()),
                    "chr21_scores": str(resolve_chr21_scores(args.spectrum_dir)),
                    "n11_label": assert_dosage_dominated(),
                    "export_ok": True,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
