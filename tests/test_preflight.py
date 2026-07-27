"""Tests for the metadata preflight reporter.

Every input here is generated in the test process. No file is downloaded and no
real dataset is read.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from p22.cli import preflight as preflight_cli
from p22.data.preflight import (
    PreflightReport,
    inspect_h5ad,
    inspect_metadata,
    write_preflight_report,
)
from p22.data.schema import (
    ACCESS_FACTS,
    DEFAULT_SCHEMA,
    STATUS_BLOCKED,
    STATUS_INCONCLUSIVE,
    STATUS_PASS,
    UNKNOWN,
)
from p22.testing import make_synthetic_multimodal

FULL_ACCESS_FACTS = {fact: "recorded by researcher" for fact in ACCESS_FACTS}


@pytest.fixture(scope="module")
def dataset():
    return make_synthetic_multimodal(n_donors=6, cells_per_donor=8, seed=11)


@pytest.fixture
def metadata(dataset):
    return dataset.metadata.copy()


def _paired_kwargs(dataset):
    return {
        "view_shapes": {"view_a": dataset.view_a.shape, "view_b": dataset.view_b.shape},
        "view_cell_ids": {"view_a": dataset.cell_ids, "view_b": dataset.cell_ids},
    }


def test_complete_input_passes(dataset, metadata):
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS, **_paired_kwargs(dataset))
    assert report.status == STATUS_PASS
    assert report.blocking_problems == ()
    assert report.open_questions == ()
    assert report.sections["pairing"]["status"] == "paired"
    assert report.sections["network_access"] == "none"


def test_counts_are_reported(dataset, metadata):
    report = inspect_metadata(metadata, **_paired_kwargs(dataset))
    sections = report.sections
    assert sections["rows"]["n_rows"] == 48
    assert sections["donors"]["n_donors"] == 6
    assert sections["donors"]["cells_per_donor"]["min"] == 8
    assert sections["labels"]["n_classes"] == 3
    assert sum(sections["labels"]["class_counts"].values()) == 48
    assert sections["per_donor_class_counts"]["available"] is True
    assert sections["per_donor_class_counts"]["donors"] == 6
    assert sections["modalities"]["views"]["view_a"]["features"] == 16
    assert sections["modalities"]["views"]["view_b"]["rows_match_metadata"] is True


def test_unknown_access_facts_make_status_inconclusive(dataset, metadata):
    report = inspect_metadata(metadata, **_paired_kwargs(dataset))
    assert report.status == STATUS_INCONCLUSIVE
    assert report.sections["access_facts"] == {fact: UNKNOWN for fact in ACCESS_FACTS}
    assert len(report.open_questions) == len(ACCESS_FACTS)
    assert all("must be recorded by a human" in question for question in report.open_questions)


def test_unsupplied_pairing_is_unknown_not_guessed(metadata):
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS)
    assert report.status == STATUS_INCONCLUSIVE
    assert report.sections["pairing"]["status"] == UNKNOWN
    assert any("pairing between the two views is unknown" in q for q in report.open_questions)
    assert any("modality shapes were not supplied" in q for q in report.open_questions)


def test_partial_pairing_is_reported(dataset, metadata):
    kwargs = _paired_kwargs(dataset)
    kwargs["view_cell_ids"] = {
        "view_a": dataset.cell_ids,
        "view_b": dataset.cell_ids[:40],
    }
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS, **kwargs)
    assert report.sections["pairing"]["status"] == "partially paired"
    assert report.sections["pairing"]["cells_in_all_views"] == 40
    assert report.sections["pairing"]["metadata_cells_missing_from_a_view"] == 8
    assert report.status == STATUS_INCONCLUSIVE


def test_disjoint_views_are_blocked(dataset, metadata):
    kwargs = _paired_kwargs(dataset)
    kwargs["view_cell_ids"] = {
        "view_a": dataset.cell_ids[:24],
        "view_b": dataset.cell_ids[24:],
    }
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS, **kwargs)
    assert report.status == STATUS_BLOCKED
    assert any("no cell identifier is shared" in problem for problem in report.blocking_problems)


def test_missing_required_column_is_blocked(dataset, metadata):
    without_donor = metadata.drop(columns=["donor_id"])
    report = inspect_metadata(without_donor, access_facts=FULL_ACCESS_FACTS)
    assert report.status == STATUS_BLOCKED
    assert any("required column absent: donor_id" in p for p in report.blocking_problems)
    assert report.sections["donors"]["n_donors"] == UNKNOWN
    assert report.sections["per_donor_class_counts"]["available"] is False


def test_duplicate_cell_ids_are_blocked(dataset, metadata):
    metadata.loc[1, "cell_id"] = metadata.loc[0, "cell_id"]
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS, **_paired_kwargs(dataset))
    assert report.status == STATUS_BLOCKED
    assert report.sections["duplicates"]["duplicate_cell_ids"] == 1
    assert report.sections["duplicates"]["duplicate_rows"] == 2


def test_row_count_mismatch_is_blocked(dataset, metadata):
    report = inspect_metadata(
        metadata,
        view_shapes={"view_a": (47, 16), "view_b": dataset.view_b.shape},
        view_cell_ids={"view_a": dataset.cell_ids, "view_b": dataset.cell_ids},
        access_facts=FULL_ACCESS_FACTS,
    )
    assert report.status == STATUS_BLOCKED
    assert any("has 47 rows but metadata has 48" in p for p in report.blocking_problems)


def test_missingness_is_measured_and_blocks_required_columns(dataset, metadata):
    metadata.loc[2, "label"] = np.nan
    metadata.loc[3, "capture_batch"] = "  "
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS, **_paired_kwargs(dataset))
    missingness = report.sections["missingness"]
    assert missingness["label"]["missing"] == 1
    assert missingness["capture_batch"]["missing"] == 1
    assert missingness["donor_id"]["missing"] == 0
    assert report.status == STATUS_BLOCKED
    assert any("required column label has 1 missing" in p for p in report.blocking_problems)


def test_unexpected_columns_are_listed(dataset, metadata):
    metadata["extra_column"] = 1
    report = inspect_metadata(metadata, **_paired_kwargs(dataset))
    assert "extra_column" in report.sections["rows"]["unexpected_columns"]


def test_donor_with_single_cell_is_counted():
    frame = pd.DataFrame(
        {
            "cell_id": ["cell_0", "cell_1", "cell_2"],
            "donor_id": ["donor_0", "donor_0", "donor_1"],
            "label": [0, 1, 0],
        }
    )
    report = inspect_metadata(frame, access_facts=FULL_ACCESS_FACTS)
    assert report.sections["donors"]["donors_with_one_cell"] == 1
    assert report.sections["per_donor_class_counts"]["donors_missing_at_least_one_class"] == 1


def test_bad_input_types_are_rejected():
    with pytest.raises(TypeError, match="pandas DataFrame"):
        inspect_metadata({"cell_id": ["a"]})
    with pytest.raises(ValueError, match="no rows"):
        inspect_metadata(pd.DataFrame(columns=["cell_id", "donor_id", "label"]))


def test_schema_lists_unknown_access_facts():
    assert DEFAULT_SCHEMA.unknown_access_facts(None) == list(ACCESS_FACTS)
    assert DEFAULT_SCHEMA.unknown_access_facts(FULL_ACCESS_FACTS) == []
    partial = dict(FULL_ACCESS_FACTS)
    partial["licence"] = UNKNOWN
    assert DEFAULT_SCHEMA.unknown_access_facts(partial) == ["licence"]


def test_report_round_trips_to_json(dataset, metadata, tmp_path):
    report = inspect_metadata(metadata, access_facts=FULL_ACCESS_FACTS, **_paired_kwargs(dataset))
    written = write_preflight_report(report, tmp_path / "nested" / "report.json")
    payload = json.loads(written.read_text())
    assert payload["status"] == STATUS_PASS
    assert payload["rows"]["n_rows"] == 48
    assert payload["access_facts"]["licence"] == "recorded by researcher"
    assert isinstance(report, PreflightReport)


def _write_tiny_h5ad(path, dataset):
    import anndata

    obs = pd.DataFrame(
        {
            "donor": dataset.metadata["donor_id"].to_numpy(),
            "label": dataset.metadata["label"].to_numpy(),
        },
        index=pd.Index(dataset.cell_ids.astype(str), name="cell_id"),
    )
    adata = anndata.AnnData(X=dataset.view_a.astype("float32"), obs=obs)
    adata.write_h5ad(path)
    return path


def test_tiny_h5ad_is_inspectable(dataset, tmp_path):
    path = _write_tiny_h5ad(tmp_path / "tiny.h5ad", dataset)
    report = inspect_h5ad(path, donor_column="donor", access_facts=FULL_ACCESS_FACTS)
    assert report.sections["rows"]["n_rows"] == 48
    assert report.sections["donors"]["n_donors"] == 6
    assert report.sections["modalities"]["views"]["view_a"]["features"] == 16
    assert report.sections["source"].startswith("local file")
    # One view only, so pairing stays unknown rather than being assumed.
    assert report.sections["pairing"]["status"] == UNKNOWN
    assert report.status == STATUS_INCONCLUSIVE


def test_h5ad_rejects_remote_and_wrong_suffix(tmp_path):
    with pytest.raises(ValueError, match="local paths only"):
        inspect_h5ad("https://example.org/matrix.h5ad")
    with pytest.raises(ValueError, match="expected a .h5ad file"):
        inspect_h5ad(tmp_path / "matrix.csv")
    with pytest.raises(FileNotFoundError):
        inspect_h5ad(tmp_path / "absent.h5ad")


def test_cli_on_csv(dataset, metadata, tmp_path, capsys):
    csv_path = tmp_path / "metadata.csv"
    metadata.to_csv(csv_path, index=False)
    out_path = tmp_path / "report.json"
    exit_code = preflight_cli.main(
        [
            "--metadata-csv",
            str(csv_path),
            "--out",
            str(out_path),
            "--access-fact",
            "licence=CC-BY",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "status: INCONCLUSIVE" in captured
    payload = json.loads(out_path.read_text())
    assert payload["access_facts"]["licence"] == "CC-BY"
    assert payload["access_facts"]["access_level"] == UNKNOWN


def test_cli_fails_on_blocked(dataset, metadata, tmp_path):
    metadata = metadata.drop(columns=["donor_id"])
    csv_path = tmp_path / "metadata.csv"
    metadata.to_csv(csv_path, index=False)
    exit_code = preflight_cli.main(
        ["--metadata-csv", str(csv_path), "--out", str(tmp_path / "r.json"), "--fail-on-blocked"]
    )
    assert exit_code == 1


def test_cli_rejects_malformed_access_fact(dataset, metadata, tmp_path):
    csv_path = tmp_path / "metadata.csv"
    metadata.to_csv(csv_path, index=False)
    with pytest.raises(ValueError, match="expected NAME=VALUE"):
        preflight_cli.main(["--metadata-csv", str(csv_path), "--access-fact", "licence"])
