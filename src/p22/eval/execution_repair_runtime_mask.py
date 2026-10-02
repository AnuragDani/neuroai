"""E1 runtime chromosome-mask helpers for execution repair (2026-10-02).

Kept outside M8 ``REQUIRED_LOCK_KEYS`` so locked metrics/target modules remain
byte-stable while feature construction still enforces whole-target-chromosome
exclusion at runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from p22.eval.masked_atac_metrics import assert_chromosome_mask_exclusivity


def load_union_bed_chroms(path: str | Path) -> list[str]:
    """Return chromosome labels in BED row order (0-based half-open intervals)."""
    chroms: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 3:
            raise ValueError(f"malformed BED row: {line!r}")
        chrom, start_s, end_s = fields[0], fields[1], fields[2]
        start, end = int(start_s), int(end_s)
        if end <= start:
            raise ValueError(f"non-positive half-open interval: {line!r}")
        chroms.append(str(chrom))
    if not chroms:
        raise ValueError(f"empty union BED: {path}")
    return chroms


def enforce_runtime_feature_mask(
    *,
    region_chroms: Sequence[str],
    visible_indices: Sequence[int],
    target_index: int,
    target_chrom: str,
) -> dict[str, Any]:
    """Runtime gate for feature construction (E1).

    Rejects target-index leakage into visible ATAC, any same-chromosome visible
    region, and target-chromosome / target-index disagreement. Callers must still
    fit panel depth on visible columns only (never target-inclusive depth).
    """
    chroms = [str(c) for c in region_chroms]
    if not chroms:
        raise ValueError("region_chroms empty")
    tidx = int(target_index)
    if tidx < 0 or tidx >= len(chroms):
        raise ValueError(f"target_index {tidx} out of range for {len(chroms)} regions")
    vis = [int(i) for i in visible_indices]
    if tidx in set(vis):
        raise ValueError(f"target index {tidx} leaked into visible ATAC features")
    want_chrom = str(target_chrom)
    got_chrom = chroms[tidx]
    if got_chrom != want_chrom:
        raise ValueError(
            f"target chrom mismatch: region {tidx} is {got_chrom!r}, "
            f"fold declares {want_chrom!r}"
        )
    assert_chromosome_mask_exclusivity(chroms, vis, want_chrom)
    return {
        "target_index": tidx,
        "target_chrom": want_chrom,
        "n_visible": len(vis),
        "chromosome_mask_exclusivity_ok": True,
        "target_excluded_from_visible": True,
        "target_inclusive_depth_refused": True,
        "runtime_mask_enforced": True,
    }
