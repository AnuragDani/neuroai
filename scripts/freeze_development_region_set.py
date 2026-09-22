"""Freeze a training-fold-only ATAC region set for the development cohort.

The development cohort's per-library cellranger-arc peak lists share no common
exact intervals, so a paired ATAC matrix cannot reuse any single library's peak
space. This module builds the frozen common region set the accepted protocol
requires: the exact-interval union of the *training-fold* libraries' peaks, with
a pre-registered selection rule (top-N by training-library prevalence, ties
broken by chromosome, start, end).

Peaks are called per library from fragments, so this discovery uses no disease
labels and no held-out donors. It produces a region-set record, not counts; the
counts are recovered separately by bounded remote tabix queries.

Selection is exact-interval only: overlapping-but-not-identical intervals are
never merged or projected, matching the repository's no-approximation policy.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

PEAK_MODALITY = "Peaks"
DEFAULT_TOP_N = 512
TIE_BREAK_HISTORICAL = "historical"
TIE_BREAK_SHA256 = "sha256"
TIE_BREAK_CHOICES = (TIE_BREAK_HISTORICAL, TIE_BREAK_SHA256)
DEFAULT_TIE_BREAK = TIE_BREAK_HISTORICAL
DEFAULT_TIE_BREAK_SALT = "p22-atac-tiebreak-v1"
_INTERVAL = re.compile(r"([^:\s]+):(\d+)-(\d+)")


def parse_features_peaks(path: str | Path) -> list[str]:
    """Return canonical ``chrom:start-end`` intervals for Peaks rows in a features file."""
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    intervals: list[str] = []
    seen: set[str] = set()
    with opener(path, "rt") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) != 6:
                raise ValueError(f"features row needs 6 columns: {path.name}")
            modality, chromosome, start, end = fields[2], fields[3], fields[4], fields[5]
            if modality != PEAK_MODALITY:
                continue
            start_i, end_i = int(start), int(end)
            if start_i < 0 or end_i <= start_i:
                raise ValueError(
                    f"invalid peak interval in {path.name}: {chromosome}:{start}-{end}"
                )
            interval = f"{chromosome}:{start_i}-{end_i}"
            if interval in seen:
                raise ValueError(f"duplicate peak interval in {path.name}: {interval}")
            seen.add(interval)
            intervals.append(interval)
    if not intervals:
        raise ValueError(f"no Peaks rows in {path.name}")
    return intervals


def _sort_key(interval: str):
    match = _INTERVAL.fullmatch(interval)
    if match is None:
        raise ValueError(f"invalid region: {interval}")
    chromosome, start, end = match.groups()
    return (chromosome, int(start), int(end))


def _hash_tie_key(interval: str, salt: str) -> str:
    """Fixed sha256 ordering for a canonical region within a prevalence tie."""
    return hashlib.sha256((salt + "\n" + interval).encode("utf-8")).hexdigest()


def _ranking_key(interval: str, prevalence: int, *, tie_break: str, tie_break_salt: str):
    """Total ordering key: prevalence first, then the declared tie-break.

    Historical mode reproduces the original (chromosome, start, end) tie-break.
    The sha256 mode removes lexicographic chromosome preference inside a tie
    without changing prevalence priority or the candidate set.
    """
    if tie_break == TIE_BREAK_HISTORICAL:
        return (-prevalence, _sort_key(interval))
    if tie_break == TIE_BREAK_SHA256:
        return (-prevalence, _hash_tie_key(interval, tie_break_salt), interval)
    raise ValueError(f"unknown tie_break: {tie_break!r}")


def _selection_rule(
    tie_break: str,
    tie_break_salt: str,
    *,
    prevalence_subject: str = "training-library",
) -> str:
    base = f"top-N exact intervals by {prevalence_subject} prevalence; "
    if tie_break == TIE_BREAK_HISTORICAL:
        return base + "ties broken by (chromosome, start, end)"
    return (
        base
        + "ties broken by sha256(salt + '\\n' + region) with salt "
        + f"{tie_break_salt!r}, then region"
    )


def build_region_set(
    features_dir: str | Path,
    train_libraries: list[str],
    *,
    top_n: int = DEFAULT_TOP_N,
    tie_break: str = DEFAULT_TIE_BREAK,
    tie_break_salt: str = DEFAULT_TIE_BREAK_SALT,
) -> dict:
    """Build the frozen union + selected region set from training libraries."""
    if not train_libraries:
        raise ValueError("at least one training library is required")
    if len(set(train_libraries)) != len(train_libraries):
        raise ValueError("duplicate training libraries")
    if type(top_n) is not int or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    if tie_break not in TIE_BREAK_CHOICES:
        raise ValueError(f"tie_break must be one of {TIE_BREAK_CHOICES}")
    if not isinstance(tie_break_salt, str) or not tie_break_salt:
        raise ValueError("tie_break_salt must be a non-empty string")
    features_dir = Path(features_dir)
    prevalence: dict[str, int] = {}
    per_library: dict[str, dict] = {}
    for library in train_libraries:
        path = features_dir / f"GSE305146_{library}_features.tsv.gz"
        if not path.exists():
            raise FileNotFoundError(f"missing features file: {path}")
        raw = path.read_bytes()
        intervals = parse_features_peaks(path)
        per_library[library] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "n_peaks": len(intervals),
        }
        for interval in intervals:
            prevalence[interval] = prevalence.get(interval, 0) + 1
    ranked = sorted(
        prevalence,
        key=lambda region: _ranking_key(
            region,
            prevalence[region],
            tie_break=tie_break,
            tie_break_salt=tie_break_salt,
        ),
    )
    selected = ranked[:top_n]
    return {
        "record_type": "frozen_development_region_set",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "selection_rule": _selection_rule(tie_break, tie_break_salt),
        "tie_break": tie_break,
        "tie_break_salt": tie_break_salt if tie_break == TIE_BREAK_SHA256 else None,
        "interval_convention": "chr:start-end 0-based half-open (cellranger-arc)",
        "count_unit": "fragment_overlap_sum",
        "n_train_libraries": len(train_libraries),
        "train_libraries": sorted(train_libraries),
        "n_union_regions": len(prevalence),
        "n_selected": len(selected),
        "top_n": top_n,
        "regions": selected,
        "regions_sha256": hashlib.sha256("\n".join(selected).encode()).hexdigest(),
        "prevalence_max": max(prevalence.values()),
        "per_library": per_library,
        "label_independence": (
            "peaks called per library from fragments; no disease labels or held-out donors used"
        ),
    }


def derive_train_libraries(
    obs_h5ad: str | Path,
    *,
    repeat: int = 0,
    fold: int = 0,
    n_repeats: int = 5,
    n_folds: int = 5,
    split_seed: int = 0,
) -> dict:
    """Derive the training-fold libraries from the frozen donor-aware split plan."""
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
    wanted = [item for item in folds if item.repeat == repeat and item.fold == fold]
    if len(wanted) != 1:
        raise ValueError("requested repeat/fold is not in the split plan")
    chosen = wanted[0]
    libraries = sorted(
        obs.loc[obs["donor_id"].isin(chosen.train_donors), "library"].astype(str).unique()
    )
    return {
        "repeat": chosen.repeat,
        "fold": chosen.fold,
        "split_seed": chosen.split_seed,
        "n_train_donors": len(chosen.train_donors),
        "n_test_donors": len(chosen.test_donors),
        "train_donors": list(chosen.train_donors),
        "test_donors": list(chosen.test_donors),
        "train_libraries": libraries,
    }


def write_regions_file(record: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for region in record["regions"]:
        match = _INTERVAL.fullmatch(region)
        if match is None:
            raise ValueError(f"invalid region: {region}")
        chromosome, start, end = match.groups()
        lines.append(f"{chromosome}\t{start}\t{end}")
    path.write_text("\n".join(lines) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features-dir", required=True, type=Path)
    parser.add_argument("--obs-h5ad", default=None, type=Path)
    parser.add_argument("--train-libraries-file", default=None, type=Path)
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--n-repeats", type=int, default=5)
    parser.add_argument("--n-folds", type=int, default=5)
    parser.add_argument("--split-seed", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument(
        "--tie-break",
        choices=TIE_BREAK_CHOICES,
        default=DEFAULT_TIE_BREAK,
        help="tie-break inside equal training-library prevalence",
    )
    parser.add_argument("--tie-break-salt", default=DEFAULT_TIE_BREAK_SALT)
    parser.add_argument("--regions-file", default=None, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.train_libraries_file:
        libraries = [
            line.strip()
            for line in args.train_libraries_file.read_text().splitlines()
            if line.strip()
        ]
        fold_record = {"source": f"explicit list {args.train_libraries_file}"}
    elif args.obs_h5ad:
        fold_record = derive_train_libraries(
            args.obs_h5ad,
            repeat=args.repeat,
            fold=args.fold,
            n_repeats=args.n_repeats,
            n_folds=args.n_folds,
            split_seed=args.split_seed,
        )
        libraries = fold_record["train_libraries"]
    else:
        raise SystemExit("one of --train-libraries-file or --obs-h5ad is required")
    record = build_region_set(
        args.features_dir,
        libraries,
        top_n=args.top_n,
        tie_break=args.tie_break,
        tie_break_salt=args.tie_break_salt,
    )
    record["fold"] = fold_record
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    if args.regions_file:
        write_regions_file(record, args.regions_file)
    print(
        json.dumps(
            {
                "n_train_libraries": record["n_train_libraries"],
                "n_union_regions": record["n_union_regions"],
                "n_selected": record["n_selected"],
                "regions_sha256": record["regions_sha256"],
                "tie_break": record["tie_break"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
