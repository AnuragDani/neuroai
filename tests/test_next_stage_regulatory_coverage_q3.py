"""Q3 regulatory coverage: all 25 panels; structural vs regulatory labels."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COVERAGE_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
    / "regulatory_coverage.json"
)
COVERAGE_MD = COVERAGE_JSON.with_name("REGULATORY_COVERAGE.md")
SCRIPT = ROOT / "scripts" / "report_next_stage_regulatory_coverage.py"
H5AD = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/data/real/"
    "f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad"
)
ATAC = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22-gnhf-worktrees/"
    "p22-results-executio-debda8/reports/generated/"
    "atac_tiebreak_measured_20260921/counts/counts.npz"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_regulatory_coverage", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def coverage() -> dict:
    assert COVERAGE_JSON.is_file(), f"missing {COVERAGE_JSON}; run Q3 reporter first"
    return json.loads(COVERAGE_JSON.read_text())


def test_markdown_and_disposition(coverage: dict) -> None:
    assert COVERAGE_MD.is_file()
    text = COVERAGE_MD.read_text()
    assert "REGULATORY_ADEQUACY_UNRESOLVED" in text
    assert "STRUCTURAL_COVERAGE_PASS" in text
    assert coverage["disposition"] == "REGULATORY_ADEQUACY_UNRESOLVED"
    assert coverage["structural_adequacy"]["label"] == "STRUCTURAL_COVERAGE_PASS"
    assert (
        coverage["biological_regulatory_adequacy"]["label"]
        == "REGULATORY_ADEQUACY_UNRESOLVED"
    )


def test_all_25_panels_reported(coverage: dict) -> None:
    panels = coverage["panels"]
    assert len(panels) == 25
    assert coverage["summary"]["n_panels"] == 25
    keys = {(int(p["fold"]), int(p["repeat"])) for p in panels}
    assert keys == {(f, r) for f in range(5) for r in range(5)}
    for panel in panels:
        assert panel["n_regions"] == 256
        assert len(panel["per_type"]) == 15
        assert 0.0 <= panel["zero_cell_fraction"] <= 1.0
        assert 0.0 <= panel["gene_body_overlap_fraction"] <= 1.0
        assert panel["n_chr21_regions"] == int(round(panel["chr21_region_fraction"] * 256))


def test_labels_stay_distinct_and_alternate_is_single(coverage: dict) -> None:
    # Structural pass must not be smuggled into regulatory PASS
    assert coverage["disposition"] != "REGULATORY_ADEQUACY_PASS"
    assert coverage["alternate_representation"]["proposed"] is True
    assert "gene-activity" in coverage["alternate_representation"]["representation"]
    assert "ENDPOINT_UNRESOLVED" in coverage["alternate_representation"]["does_not_authorize"]
    assert coverage["biological_regulatory_adequacy"]["annotation_sources"][
        "regulatory_element_catalog"
    ] == "ABSENT_IN_REPO"


def test_interval_overlap_hand_examples() -> None:
    mod = _load_script()
    regions = ["chr1:10-20", "chr1:30-40", "chr2:1-5"]
    genes = [("chr1", 15, 25), ("chr1", 40, 50), ("chr2", 10, 20)]
    # body: first overlaps; second touches end-exclusive boundary only at 40 → no;
    # half-open [40,50) vs [30,40) → no overlap; chr2 no overlap
    assert mod.interval_overlap_count(regions, genes, flank=0) == 1
    # flank 0 on gene end-exclusive: gene [39,41) would overlap second
    assert mod.interval_overlap_count(regions, [("chr1", 39, 41)], flank=0) == 1
    # flank expands gene [12,13] to [10,15] overlapping first
    assert mod.interval_overlap_count(regions, [("chr1", 12, 13)], flank=2) == 1


@pytest.mark.skipif(not (H5AD.is_file() and ATAC.is_file()), reason="shared inputs missing")
def test_independent_replay_matches_saved(coverage: dict) -> None:
    mod = _load_script()
    replay = mod.independent_panel_replay(
        coverage=coverage,
        atac_npz=ATAC,
        union_bed=ROOT / "configs/atac_tiebreak_union_2026-09-21.bed",
        region_sets_path=ROOT / "configs/atac_tiebreak_region_sets_2026-09-21.json",
        fold=0,
        repeat=0,
    )
    assert replay["regions_sha256_match"] is True
    assert replay["zero_cell_fraction_match"] is True
    assert replay["median_nonzero_regions_match"] is True
    assert replay["median_fragment_overlaps_match"] is True
    saved = coverage["independent_panel_replay"]
    assert saved["zero_cell_fraction_match"] is True
