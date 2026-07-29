"""Tests for runtime report (G0) and catalog preflight (G1)."""

from pathlib import Path

from p22.data.catalog import (
    EXPECTED_CELLS,
    EXPECTED_DONORS,
    CatalogContract,
    build_catalog_summary,
    evaluate_catalog_contract,
    run_catalog_preflight,
)
from p22.eval.runtime import collect_runtime_report


def test_runtime_report_passes_with_writable_generated_output(tmp_path: Path):
    source = tmp_path / "P22_down_syndrome_all_in_one.ipynb"
    source.write_text("# notebook\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='p22'\n", encoding="utf-8")
    (tmp_path / "src" / "p22").mkdir(parents=True)
    output = tmp_path / "reports" / "generated" / "down_syndrome"
    report = collect_runtime_report(
        project_root=tmp_path,
        data_root=tmp_path / "data" / "real",
        output_root=output,
        source_notebook=source,
        min_disk_gb=0.0,
    )
    assert report.status in {"PASS", "INCONCLUSIVE"}
    assert report.output_root == str(output)
    assert "reports/generated" in report.output_root


def test_catalog_contract_matches_expected_scale():
    collection = {
        "id": "0e9fd1d3-ef4c-47c6-a2e4-ef4bfadf7c79",
        "name": "DS collection",
        "datasets": [],
    }
    donor_ids = [f"GW_CON_{index:02d}" for index in range(15)] + [
        f"GW_DS_{index:02d}" for index in range(15)
    ]
    dataset = {
        "id": "f16c25da-15bd-46a4-9a3f-17093f27a2f1",
        "name": "Human fetal cortex in Down syndrome",
        "cell_count": EXPECTED_CELLS,
        "donor_id": donor_ids,
        "assay": [{"label": "10x multiome"}],
        "disease": [{"label": "complete trisomy 21"}, {"label": "normal"}],
        "development_stage": [{"label": f"stage_{index}"} for index in range(10)],
        "dataset_assets": [
            {"filetype": "H5AD", "file_size": 1_569_658_860, "s3_uri": "s3://x/local.h5ad"},
            {"filetype": "ATAC_FRAGMENT", "file_size": 9_000_000_000},
        ],
    }
    summary = build_catalog_summary(collection, dataset, CatalogContract())
    status, blocking, unknowns = evaluate_catalog_contract(summary)
    assert status == "INCONCLUSIVE"
    assert not blocking
    assert any("same-nucleus" in item for item in unknowns)
    assert summary["donor_count"] == EXPECTED_DONORS


def test_catalog_preflight_live_or_blocked():
    report = run_catalog_preflight()
    assert report.status in {"PASS", "INCONCLUSIVE", "BLOCKED"}
    assert report.catalog_url.endswith("/collections/0e9fd1d3-ef4c-47c6-a2e4-ef4bfadf7c79")
    if report.status != "BLOCKED":
        assert report.summary["cell_count"] == EXPECTED_CELLS
        assert report.summary["donor_count"] == EXPECTED_DONORS
