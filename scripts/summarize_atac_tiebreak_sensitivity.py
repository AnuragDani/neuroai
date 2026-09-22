"""Summarize the ATAC hash-tie-break representation sensitivity (Phase 1 diagnostics).

Reads the historical and sha256-tie-break repeated region-set records and the cached
per-library features, then reports per-fold and union chromosome distributions,
overlap, selected-region prevalence summaries, donor/library discovery isolation and
a deterministic rebuild check. Produces a compact JSON record; it fits no model and
uses no disease outcome.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from freeze_development_region_set import (  # noqa: E402
    _sort_key,
    build_region_set,
    parse_features_peaks,
)

HISTORICAL_TIE_BREAK = "historical"
SHA256_TIE_BREAK = "sha256"


def _chrom(region: str) -> str:
    return region.split(":", 1)[0]


def _chrom_distribution(regions: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(_chrom(r) for r in regions).items()))


def _prevalence_histogram(regions: list[str], prevalence: dict[str, int]) -> dict[str, int]:
    counts = Counter(prevalence[r] for r in regions)
    return {str(k): counts[k] for k in sorted(counts)}


def load_prevalence(features_dir: Path, libraries: list[str]) -> dict[str, int]:
    prevalence: dict[str, int] = {}
    for library in libraries:
        for interval in parse_features_peaks(features_dir / f"GSE305146_{library}_features.tsv.gz"):
            prevalence[interval] = prevalence.get(interval, 0) + 1
    return prevalence


def donor_library_map(obs_h5ad: Path) -> dict[str, set[str]]:
    import anndata as ad

    backed = ad.read_h5ad(obs_h5ad, backed="r")
    try:
        obs = backed.obs[["library", "donor_id"]].copy()
    finally:
        backed.file.close()
    mapping: dict[str, set[str]] = {}
    for donor, group in obs.groupby("donor_id", observed=True):
        mapping[str(donor)] = set(group["library"].astype(str))
    return mapping


def summarize(
    features_dir: Path,
    historical: dict,
    sha256: dict,
    *,
    top_n: int,
    obs_h5ad: Path | None = None,
) -> dict:
    if historical["n_folds"] != sha256["n_folds"]:
        raise ValueError("fold counts differ between representations")
    mapping = donor_library_map(obs_h5ad) if obs_h5ad else None
    per_fold = []
    union_hist_set: set[str] = set()
    union_sha_set: set[str] = set()
    discovery_isolated = True
    for h_fold, s_fold in zip(historical["per_fold"], sha256["per_fold"], strict=True):
        if (h_fold["repeat"], h_fold["fold"]) != (s_fold["repeat"], s_fold["fold"]):
            raise ValueError("fold order differs between representations")
        h_regions = h_fold["regions"]
        s_regions = s_fold["regions"]
        union_hist_set.update(h_regions)
        union_sha_set.update(s_regions)
        prevalence = load_prevalence(features_dir, h_fold["train_libraries"])
        if mapping is not None:
            train_libraries = set(h_fold["train_libraries"])
            expected_train = set().union(*(mapping[d] for d in h_fold["train_donors"]))
            test_libraries = set().union(*(mapping[d] for d in h_fold["test_donors"]))
            if train_libraries != expected_train or (train_libraries & test_libraries):
                discovery_isolated = False
        h_set, s_set = set(h_regions), set(s_regions)
        inter = len(h_set & s_set)
        union_size = len(h_set | s_set)
        per_fold.append(
            {
                "repeat": h_fold["repeat"],
                "fold": h_fold["fold"],
                "n_train_libraries": len(h_fold["train_libraries"]),
                "n_historical": len(h_regions),
                "n_sha256": len(s_regions),
                "intersection": inter,
                "jaccard": round(inter / union_size, 6) if union_size else 0.0,
                "chrom_historical": _chrom_distribution(h_regions),
                "chrom_sha256": _chrom_distribution(s_regions),
                "prevalence_historical": _prevalence_histogram(h_regions, prevalence),
                "prevalence_sha256": _prevalence_histogram(s_regions, prevalence),
            }
        )
    union_hist = sorted(union_hist_set, key=_sort_key)
    union_sha = sorted(union_sha_set, key=_sort_key)
    # Rebuild the sha256 union once to prove deterministic ranking on real inputs.
    rebuilt = build_region_set(
        features_dir,
        sha256["per_fold"][0]["train_libraries"],
        top_n=top_n,
        tie_break=SHA256_TIE_BREAK,
        tie_break_salt=sha256["tie_break_salt"],
    )
    deterministic = rebuilt["regions"] == sha256["per_fold"][0]["regions"]
    return {
        "record_type": "atac_tiebreak_sensitivity_diagnostics",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "top_n": top_n,
        "historical_union_sha256": historical["union_sha256"],
        "sha256_union_sha256": sha256["union_sha256"],
        "historical_n_union_regions": historical["n_union_regions"],
        "sha256_n_union_regions": sha256["n_union_regions"],
        "union_intersection": len(union_hist_set & union_sha_set),
        "union_historical_only": len(union_hist_set - union_sha_set),
        "union_sha256_only": len(union_sha_set - union_hist_set),
        "union_chrom_historical": _chrom_distribution(union_hist),
        "union_chrom_sha256": _chrom_distribution(union_sha),
        "union_sha256_rebuild_matches_fold0": deterministic,
        "no_test_library_in_discovery": discovery_isolated,
        "per_fold": per_fold,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-dir", required=True, type=Path)
    parser.add_argument("--historical", required=True, type=Path)
    parser.add_argument("--sha256", required=True, type=Path)
    parser.add_argument("--obs-h5ad", default=None, type=Path)
    parser.add_argument("--top-n", type=int, default=256)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    historical = json.loads(args.historical.read_text())
    sha256 = json.loads(args.sha256.read_text())
    record = summarize(
        args.features_dir,
        historical,
        sha256,
        top_n=args.top_n,
        obs_h5ad=args.obs_h5ad,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: record[k] for k in (
        "historical_n_union_regions",
        "sha256_n_union_regions",
        "union_intersection",
        "union_historical_only",
        "union_sha256_only",
        "union_sha256_rebuild_matches_fold0",
        "no_test_library_in_discovery",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
