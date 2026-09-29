#!/usr/bin/env python3
"""P1/N16: cell-state spectrum on the canonical ladder_v3 N15 export."""

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
DOCS_JSON = ROOT / "docs/nn_v2/spectrum.json"
DOCS_MD = ROOT / "docs/nn_v2/SPECTRUM.md"
LADDER_MD = ROOT / "docs/nn_v2/LADDER.md"
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


def resolve_cell_scores(spectrum_dir: Path = DEFAULT_SPECTRUM) -> Path:
    path = spectrum_dir / "cell_scores.csv.gz"
    if not path.is_file():
        raise RuntimeError(f"missing N15 export: {path}")
    return path.resolve()


def resolve_chr21_scores(spectrum_dir: Path = DEFAULT_SPECTRUM) -> Path | None:
    path = spectrum_dir / "cell_scores_chr21_excluded.csv.gz"
    return path.resolve() if path.is_file() else None


def assert_export_binds_ladder(ladder: Path, export_json: Path = EXPORT_JSON) -> dict:
    if not export_json.is_file():
        raise RuntimeError(f"missing {export_json}")
    payload = json.loads(export_json.read_text())
    main = payload.get("ladder_export") or payload.get("ladder_v2_export") or {}
    source = Path(main.get("source_run") or "").resolve()
    if source != ladder.resolve():
        raise RuntimeError(f"export source_run {source} != canonical {ladder}")
    if int(main.get("n_cell_arm_rows") or 0) != 120_000:
        raise RuntimeError(f"expected 120000 rows, got {main.get('n_cell_arm_rows')}")
    return payload


def _filter_arm(cells: pd.DataFrame, arm: str) -> pd.DataFrame:
    if "arm" not in cells.columns:
        return cells.copy()
    out = cells.loc[cells["arm"].astype(str) == arm].copy()
    if out.empty:
        raise RuntimeError(f"arm {arm!r} absent from export")
    return out


def _analyze_arm(mod, cells, arm, *, n_boot, n_perm, seed):
    block = _filter_arm(cells, arm)
    payload = mod.analyze_cells(block, n_boot=n_boot, n_perm=n_perm, seed=seed)
    payload["arm"] = arm
    return payload, block


def build_chr21_compare(
    mod,
    chr21_path: Path | None,
    *,
    n_boot: int,
    n_perm: int,
    seed: int,
    primary_call: str,
) -> dict:
    if chr21_path is None:
        return {
            "status": "NOT_NEEDED",
            "reason": "chr21-excluded cell-score export missing beside spectrum_v3",
        }
    cells = pd.read_csv(chr21_path)
    payload, block = _analyze_arm(
        mod, cells, PRIMARY_ARM, n_boot=n_boot, n_perm=n_perm, seed=seed
    )
    agree = payload["spectrum_call"] == primary_call
    return {
        "status": "COMPARED",
        "reason": (
            f"chr21-excluded R3_ca call `{payload['spectrum_call']}` "
            f"{'agrees with' if agree else 'differs from'} primary `{primary_call}`"
        ),
        "arm": PRIMARY_ARM,
        "cell_scores_path": str(chr21_path),
        "cell_scores_sha256": mod._sha256(chr21_path),
        "n_rows_analyzed": int(len(block)),
        "spectrum_call": payload["spectrum_call"],
        "n_eligible": len(payload.get("eligible_types") or []),
        "eligible_types": payload.get("eligible_types") or [],
        "primary_spectrum_call": primary_call,
        "calls_agree": agree,
        "detail": payload,
    }


def run_spectrum(
    ladder: Path,
    spectrum_dir: Path,
    *,
    n_boot: int = 2000,
    n_perm: int = 10000,
    seed: int = 22,
    arm: str = PRIMARY_ARM,
) -> dict:
    mod = _load_analyze()
    export = assert_export_binds_ladder(ladder)
    cell_scores = resolve_cell_scores(spectrum_dir)
    cells = pd.read_csv(cell_scores)
    payload, block = _analyze_arm(mod, cells, arm, n_boot=n_boot, n_perm=n_perm, seed=seed)
    main = export.get("ladder_export") or export.get("ladder_v2_export") or {}
    payload["source"] = {
        "cell_scores_path": str(cell_scores.relative_to(ROOT))
        if cell_scores.is_relative_to(ROOT)
        else str(cell_scores),
        "cell_scores_sha256": mod._sha256(cell_scores),
        "arm": arm,
        "arms_in_export": sorted(set(cells["arm"].astype(str))) if "arm" in cells else [arm],
        "n_rows_analyzed": int(len(block)),
        "ladder_source": str(ladder.resolve()),
        "export_evidence": "docs/nn_v2/cell_scores_export.json",
        "export_sha256": main.get("cell_scores_sha256"),
    }
    if payload["source"]["cell_scores_sha256"] != main.get("cell_scores_sha256"):
        raise RuntimeError(
            "cell_scores sha256 mismatch vs cell_scores_export.json "
            f"({payload['source']['cell_scores_sha256']} != {main.get('cell_scores_sha256')})"
        )
    payload["chr21_excluded_compare"] = build_chr21_compare(
        mod,
        resolve_chr21_scores(spectrum_dir),
        n_boot=n_boot,
        n_perm=n_perm,
        seed=seed,
        primary_call=payload["spectrum_call"],
    )
    # Drop nested full detail from docs JSON size; keep summary fields on compare.
    detail = payload["chr21_excluded_compare"].pop("detail", None)
    if detail is not None:
        payload["chr21_excluded_compare"]["significant_types"] = [
            r["author_cell_type"]
            for r in detail.get("results") or []
            if r.get("s", {}).get("significant")
        ]
    return payload


def publish(payload: dict, *, out_json: Path = DOCS_JSON, out_md: Path = DOCS_MD) -> dict:
    mod = _load_analyze()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    md_payload = dict(payload)
    src = dict(md_payload.get("source") or {})
    ladder_name = Path(src.get("ladder_source") or "").name or "canonical"
    src["_ladder_label"] = ladder_name
    md_payload["source"] = src
    mod._write_md(md_payload, out_md)
    text = out_md.read_text().replace("ladder_v2 OOF export", f"{ladder_name} OOF export")
    out_md.write_text(text)
    return {
        "wrote": str(out_json),
        "spectrum_call": payload.get("spectrum_call"),
        "n_eligible": len(payload.get("eligible_types") or []),
        "chr21_compare": (payload.get("chr21_excluded_compare") or {}).get("status"),
        "ladder_source": src.get("ladder_source"),
    }


def update_ladder_md(payload: dict) -> None:
    if not LADDER_MD.is_file():
        return
    call = payload.get("spectrum_call", "SPECTRUM_NULL")
    n_elig = len(payload.get("eligible_types") or [])
    src = payload.get("source") or {}
    ladder_name = Path(src.get("ladder_source") or "").name or "canonical"
    compare = payload.get("chr21_excluded_compare") or {}
    compare_bit = (
        f"Chr21-excluded score compare `{compare.get('status')}` "
        f"(call `{compare.get('spectrum_call', 'n/a')}`; "
        f"agree={compare.get('calls_agree', 'n/a')})."
        if compare.get("status") == "COMPARED"
        else f"Chr21-excluded score compare `{compare.get('status')}`."
    )
    section = (
        "## Cell-state spectrum (N16)\n\n"
        f"Donor-mean {src.get('arm', PRIMARY_ARM)} scores from the {ladder_name} N15 "
        f"export (`spectrum_v3`): **{call}** ({n_elig} eligible types). {compare_bit} "
        "Evidence: `docs/nn_v2/spectrum.json`, `docs/nn_v2/SPECTRUM.md`.\n"
    )
    text = LADDER_MD.read_text()
    start = text.find("## Cell-state spectrum (N16)")
    if start < 0:
        return
    end = text.find("\n## ", start + 1)
    if end < 0:
        end = len(text)
    LADDER_MD.write_text(text[:start] + section + "\n" + text[end:].lstrip("\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ladder", type=Path, default=None)
    parser.add_argument("--spectrum-dir", type=Path, default=DEFAULT_SPECTRUM)
    parser.add_argument("--arm", default=PRIMARY_ARM)
    parser.add_argument("--n-boot", type=int, default=2000)
    parser.add_argument("--n-perm", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=22)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--update-ladder-md", action="store_true")
    args = parser.parse_args(argv)

    ladder = (args.ladder or resolve_canonical_ladder()).resolve()
    n_boot = 50 if args.smoke else args.n_boot
    n_perm = 100 if args.smoke else args.n_perm

    payload = None
    if args.run:
        logging.info(
            "N16 spectrum on %s arm=%s n_boot=%d n_perm=%d",
            ladder.name, args.arm, n_boot, n_perm,
        )
        payload = run_spectrum(
            ladder,
            args.spectrum_dir,
            n_boot=n_boot,
            n_perm=n_perm,
            seed=args.seed,
            arm=args.arm,
        )
        staging = args.spectrum_dir / ("spectrum_smoke.json" if args.smoke else "spectrum.json")
        staging.write_text(json.dumps(payload, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "spectrum_call": payload["spectrum_call"],
                    "n_eligible": len(payload.get("eligible_types") or []),
                    "chr21_compare": payload["chr21_excluded_compare"].get("status"),
                    "staging": str(staging),
                },
                indent=2,
            )
        )

    if args.publish:
        if payload is None:
            staging = args.spectrum_dir / "spectrum.json"
            if not staging.is_file():
                raise SystemExit(f"missing {staging}; run with --run first")
            payload = json.loads(staging.read_text())
        print(json.dumps(publish(payload), indent=2))

    if args.update_ladder_md:
        if not DOCS_JSON.is_file():
            raise SystemExit("publish first so docs/nn_v2/spectrum.json exists")
        update_ladder_md(json.loads(DOCS_JSON.read_text()))

    if not (args.run or args.publish or args.update_ladder_md):
        print(
            json.dumps(
                {
                    "ladder": str(ladder),
                    "cell_scores": str(resolve_cell_scores(args.spectrum_dir)),
                    "chr21_scores": str(resolve_chr21_scores(args.spectrum_dir)),
                    "export_ok": True,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
