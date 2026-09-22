"""Tests for visible modes, R1-R6 board, and census planning."""

import json
from pathlib import Path

import pytest

from p22.data.catalog import EXPECTED_CELLS, EXPECTED_H5AD_BYTES
from p22.data.census import (
    census_blocked_placeholder,
    data_scale_section,
    estimate_download_gb,
    planned_acquisition_from_catalog,
)
from p22.eval.data_scale import R_IDS, empty_scale_board, make_scale
from p22.eval.modes import (
    MODE_APPROVED_REAL,
    MODE_METADATA_CENSUS,
    MODE_SIMULATION,
    VISIBLE_MODES,
    detect_colab,
    resolve_mode,
)


def test_visible_modes_are_exactly_three():
    assert VISIBLE_MODES == (MODE_SIMULATION, MODE_METADATA_CENSUS, MODE_APPROVED_REAL)


def test_resolve_mode_allows_h5ad_preflight_without_approval():
    selection = resolve_mode(MODE_APPROVED_REAL, professor_approved=False, run_real_data=True)
    assert selection.allow_h5ad_download is True
    assert selection.allow_model_fit is False


def test_resolve_mode_allows_download_when_approved():
    selection = resolve_mode(
        MODE_APPROVED_REAL,
        professor_approved=True,
        run_real_data=True,
        run_model=True,
    )
    assert selection.allow_h5ad_download is True
    assert selection.allow_model_fit is True


def test_resolve_mode_blocks_model_without_approval():
    selection = resolve_mode(
        MODE_APPROVED_REAL,
        professor_approved=False,
        run_real_data=True,
        run_model=True,
    )
    assert selection.allow_h5ad_download is True
    assert selection.allow_model_fit is False
    assert "model fitting blocked" in selection.blocking_problems[0]


def test_simulation_never_downloads():
    selection = resolve_mode(MODE_SIMULATION, professor_approved=True, run_real_data=True)
    assert selection.allow_h5ad_download is False


def test_detect_colab_false_locally():
    assert detect_colab() is False


def test_r_board_has_six_stages():
    assert R_IDS == ("R1", "R2", "R3", "R4", "R5", "R6")
    board = empty_scale_board()
    board.set(make_scale("R1", "INCONCLUSIVE", notes="checksum pending"))
    assert board.status_map()["R1"] == "INCONCLUSIVE"
    assert board.as_rows()[5]["status"] == "PENDING"


def test_planned_acquisition_blocked_without_download_permission():
    summary = {
        "cell_count": EXPECTED_CELLS,
        "donor_count": 30,
        "h5ad_asset": {"url": "https://example/h5ad", "file_size": EXPECTED_H5AD_BYTES},
        "atac_fragment_asset": {"present": True},
    }
    record = planned_acquisition_from_catalog(
        summary,
        collection_id="c",
        dataset_id="d",
        allow_download=False,
    )
    assert record.status == "BLOCKED"
    assert estimate_download_gb() == pytest.approx(1.57, abs=0.02)


def test_census_placeholder_and_data_scale_section():
    census = census_blocked_placeholder("approval absent")
    assert census.status == "BLOCKED"
    assert census.to_dict()["not_a_model_cap"] is True
    acquisition = planned_acquisition_from_catalog(
        {
            "cell_count": EXPECTED_CELLS,
            "donor_count": 30,
            "h5ad_asset": {},
            "atac_fragment_asset": {},
        },
        collection_id="c",
        dataset_id="d",
    )
    section = data_scale_section(acquisition, census)
    assert section["caps"]["capped_output_is_not_full_dataset"] is True
    assert section["inferential_scale"]["unit"] == "donor"


def test_canonical_notebook_exposes_fair_same_cap_result():
    notebook_path = Path(__file__).parents[1] / "P22_down_syndrome_all_in_one.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    markdown = "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"
    )
    code = "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )

    assert "Fair same-cell comparison" in markdown
    assert "same_cap_summary" in code
    assert "same_cap_sensitivity.png" in code
    assert "git clone" not in code
    assert "Corrected real paired workflow" in markdown
    assert "summarize_measurement_correction" in code
    assert notebook["cells"][1]["metadata"]["jupyter"]["source_hidden"] is True
    assert notebook["cells"][1]["metadata"]["collapsed"] is True
