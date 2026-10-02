"""M1 input/masking: hash contracts, half-open overlap, chromosome mask."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/masked_atac_pilot_20261001"
    / "input_and_masking.json"
)
OUT_MD = OUT_JSON.with_name("INPUT_AND_MASKING.md")
SCRIPT = ROOT / "scripts" / "report_masked_atac_input_and_masking.py"
H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/"
    "p22-results-executio-debda8/reports/generated/"
    "atac_tiebreak_measured_20260921/counts/counts.npz"
)
BED = ROOT / "configs" / "atac_tiebreak_union_2026-09-21.bed"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_masked_atac_input_and_masking", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert OUT_JSON.is_file(), f"missing {OUT_JSON}; run M1 reporter first"
    return json.loads(OUT_JSON.read_text())


def test_markdown_and_disposition(report: dict) -> None:
    assert OUT_MD.is_file()
    text = OUT_MD.read_text()
    assert "INPUT_AND_MASKING_PASS" in text
    assert report["disposition"] == "INPUT_AND_MASKING_PASS"
    assert "B_NULL" in text
    assert "target-ID" in text.lower() or "Target-ID" in text


def test_half_open_boundary_and_toy_overlap() -> None:
    mod = _load_script()
    assert mod.half_open_overlap(("chr1", 10, 20), ("chr1", 20, 30)) is False
    assert mod.half_open_overlap(("chr1", 10, 20), ("chr1", 19, 25)) is True
    assert mod.half_open_overlap(("chr1", 10, 20), ("chr2", 10, 20)) is False
    toy = [
        (0, "chr1", 10, 20, "chr1:10-20"),
        (1, "chr1", 15, 25, "chr1:15-25"),
        (2, "chr1", 30, 40, "chr1:30-40"),
        (3, "chr2", 1, 5, "chr2:1-5"),
    ]
    pairs = mod.overlapping_interval_pairs(toy)
    assert len(pairs) == 1
    assert pairs[0]["region_a"] == "chr1:10-20"
    assert pairs[0]["region_b"] == "chr1:15-25"
    # ID-only still sees overlapping partner; chromosome mask removes it
    leak = mod.target_leakage_summary(toy)
    assert leak["target_id_removal"][
        "targets_with_interval_overlapping_visible_region"
    ] == 2
    assert leak["whole_target_chromosome_mask"][
        "targets_with_interval_overlapping_visible_region"
    ] == 0
    assert leak["whole_target_chromosome_mask"][
        "targets_with_same_chromosome_visible_region"
    ] == 0


def test_hash_overlap_and_mask_contract(report: dict) -> None:
    inp = report["inputs"]
    assert inp["matrix_sha256_match"] is True
    assert inp["bed_sha256_match"] is True
    assert inp["region_sets_sha256_match"] is True
    assert inp["ordered_cells_sha256_match"] is True
    assert inp["n_regions"] == 465
    assert inp["n_cells"] == 248998
    assert inp["n_donors"] == 30
    ov = report["overlap_and_masking"]
    assert ov["n_overlapping_interval_pairs"] == 58
    assert ov["n_chromosomes_with_overlapping_pairs"] == 9
    assert ov["half_open_boundary_checks"][
        "adjacent_chr1_10_20_vs_20_30_overlap"
    ] is False
    assert ov["half_open_boundary_checks"][
        "interior_chr1_10_20_vs_19_25_overlap"
    ] is True
    leak = ov["leakage"]
    assert (
        leak["target_id_removal"][
            "targets_with_interval_overlapping_visible_region"
        ]
        > 0
    )
    assert leak["whole_target_chromosome_mask"][
        "eliminates_shared_fragment_risk_under_documented_semantics"
    ] is True
    assert leak["whole_target_chromosome_mask"]["min_visible_regions"] > 0
    assert report["checks"]["target_id_removal_insufficient"] is True
    assert report["inherited_panel_provenance"][
        "strict_inner_train_only_panel_construction"
    ] is False
    assert report["preserved_labels"]["primary"] == "B_NULL"
    assert report["preserved_labels"]["S10"] == "INVALID"
    assert report["claim_level"] == 2


@pytest.mark.skipif(
    not (H5AD.is_file() and ATAC.is_file() and BED.is_file()),
    reason="shared inputs missing",
)
def test_live_bed_overlap_count_matches_report(report: dict) -> None:
    mod = _load_script()
    regions = mod.parse_bed_regions(BED)
    assert len(regions) == 465
    pairs = mod.overlapping_interval_pairs(regions)
    assert len(pairs) == report["overlap_and_masking"][
        "n_overlapping_interval_pairs"
    ]
    assert len(pairs) == 58
    # Assert visible ATAC chroms differ from target under chromosome mask
    for _idx, chrom, _s, _e, _lab in regions[::50]:
        visible = mod.visible_regions_chromosome_mask(regions, chrom)
        assert all(r[1] != chrom for r in visible)
        assert len(visible) >= 415
