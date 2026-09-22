"""Freeze per-fold training-only ATAC region sets and their union for repeated splits.

The single-fold pilot froze one region set from the training libraries of pilot fold
(repeat 0, fold 0). A repeated donor-split comparison needs a region set per outer
fold so that no test donor's own peaks inform the feature space. Deriving each fold's
top-N set is cheap (features files are already local), and the union of the per-fold
sets is small enough to quantify once from the indexed fragment and then subset per
fold. That keeps feature discovery training-only for every fold without a per-fold
network recount.

This produces a region-set record and a union BED, not counts. The counts are
recovered separately by bounded remote tabix queries on the union BED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from freeze_development_region_set import (  # noqa: E402
    DEFAULT_TIE_BREAK,
    DEFAULT_TIE_BREAK_SALT,
    TIE_BREAK_CHOICES,
    TIE_BREAK_SHA256,
    _selection_rule,
    _sort_key,
    build_region_set,
    write_regions_file,
)

FOLD_KEYS = (
    "repeat",
    "fold",
    "split_seed",
    "n_train_donors",
    "n_test_donors",
    "train_donors",
    "test_donors",
    "train_libraries",
)


def derive_all_fold_libraries(
    obs_h5ad: str | Path,
    *,
    n_repeats: int = 5,
    n_folds: int = 5,
    split_seed: int = 0,
) -> list[dict]:
    """Return training libraries per outer fold from the frozen split plan."""
    import anndata as ad

    from p22.data.group_splits import iter_repeated_stratified_group_folds

    backed = ad.read_h5ad(obs_h5ad, backed="r")
    try:
        obs = backed.obs[["library", "donor_id", "disease"]].copy()
    finally:
        backed.file.close()
    obs = obs.reset_index()
    obs["label"] = (obs["disease"] == "complete trisomy 21").astype(int)
    folds = list(
        iter_repeated_stratified_group_folds(
            obs["donor_id"], obs["label"], n_repeats, n_folds, split_seed
        )
    )
    records = []
    for fold in folds:
        libraries = sorted(
            obs.loc[obs["donor_id"].isin(fold.train_donors), "library"].astype(str).unique()
        )
        records.append(
            {
                "repeat": fold.repeat,
                "fold": fold.fold,
                "split_seed": fold.split_seed,
                "n_train_donors": len(fold.train_donors),
                "n_test_donors": len(fold.test_donors),
                "train_donors": list(fold.train_donors),
                "test_donors": list(fold.test_donors),
                "train_libraries": libraries,
            }
        )
    return records


def build_repeated_region_sets(
    features_dir: str | Path,
    folds: list[dict],
    *,
    top_n: int,
    tie_break: str = DEFAULT_TIE_BREAK,
    tie_break_salt: str = DEFAULT_TIE_BREAK_SALT,
    count_unit: str = "fragment_overlap_sum",
) -> dict:
    """Build each fold's training-only region set and their union."""
    if not folds:
        raise ValueError("at least one fold is required")
    if tie_break not in TIE_BREAK_CHOICES:
        raise ValueError(f"tie_break must be one of {TIE_BREAK_CHOICES}")
    per_fold: list[dict] = []
    union: dict[str, int] = {}
    library_provenance: dict[str, dict] = {}
    for fold in folds:
        record = build_region_set(
            features_dir,
            fold["train_libraries"],
            top_n=top_n,
            tie_break=tie_break,
            tie_break_salt=tie_break_salt,
        )
        regions = record["regions"]
        per_fold.append(
            {
                **{key: fold[key] for key in FOLD_KEYS},
                "n_union_regions": record["n_union_regions"],
                "prevalence_max": record["prevalence_max"],
                "regions": regions,
                "regions_sha256": record["regions_sha256"],
            }
        )
        for library, provenance in record["per_library"].items():
            library_provenance.setdefault(library, provenance)
        for region in regions:
            union[region] = union.get(region, 0) + 1
    union_regions = sorted(union, key=_sort_key)
    return {
        "record_type": "frozen_repeated_development_region_sets",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "selection_rule": "per outer fold: "
        + _selection_rule(
            tie_break,
            tie_break_salt,
            prevalence_subject="that fold's training-library",
        ),
        "tie_break": tie_break,
        "tie_break_salt": tie_break_salt if tie_break == TIE_BREAK_SHA256 else None,
        "interval_convention": "chr:start-end 0-based half-open (cellranger-arc)",
        "count_unit": count_unit,
        "top_n": top_n,
        "n_folds": len(per_fold),
        "per_fold": per_fold,
        "union_regions": union_regions,
        "union_sha256": hashlib.sha256("\n".join(union_regions).encode()).hexdigest(),
        "n_union_regions": len(union_regions),
        "union_fold_prevalence": {region: union[region] for region in union_regions},
        "library_provenance": library_provenance,
        "label_independence": (
            "peaks called per library from fragments; each fold's set uses only its "
            "training libraries, so no test donor's peaks enter that fold's feature space"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-dir", required=True, type=Path)
    parser.add_argument("--obs-h5ad", required=True, type=Path)
    parser.add_argument("--n-repeats", type=int, default=5)
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--split-seed", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=256)
    parser.add_argument(
        "--tie-break",
        choices=TIE_BREAK_CHOICES,
        default=DEFAULT_TIE_BREAK,
        help="tie-break inside equal training-library prevalence",
    )
    parser.add_argument("--tie-break-salt", default=DEFAULT_TIE_BREAK_SALT)
    parser.add_argument("--count-unit", default="fragment_overlap_sum")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--union-bed", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    folds = derive_all_fold_libraries(
        args.obs_h5ad,
        n_repeats=args.n_repeats,
        n_folds=args.n_folds,
        split_seed=args.split_seed,
    )
    record = build_repeated_region_sets(
        args.features_dir,
        folds,
        top_n=args.top_n,
        tie_break=args.tie_break,
        tie_break_salt=args.tie_break_salt,
        count_unit=args.count_unit,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    write_regions_file({"regions": record["union_regions"]}, args.union_bed)
    print(
        json.dumps(
            {
                "n_folds": record["n_folds"],
                "n_union_regions": record["n_union_regions"],
                "union_sha256": record["union_sha256"],
                "tie_break": record["tie_break"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
