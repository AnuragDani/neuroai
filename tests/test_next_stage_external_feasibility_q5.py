"""Q5 external feasibility: NeMO contracts, role preservation, no payload download."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FEASIBILITY_JSON = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
    / "external_feasibility.json"
)
FEASIBILITY_MD = FEASIBILITY_JSON.with_name("EXTERNAL_FEASIBILITY.md")
SCRIPT = ROOT / "scripts" / "report_next_stage_external_feasibility.py"
SOURCE_IDENTITY = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/"
    "input_feasibility_20260912/source/source_identity.json"
)
EXPECTED_SOURCE_IDENTITY_SHA256 = (
    "45ed2cb478fa4b780f8f29f3e2499109f0a93a3e9610bcc298d1d7813f154735"
)


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_external_feasibility", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert FEASIBILITY_JSON.is_file(), f"missing {FEASIBILITY_JSON}; run Q5 reporter first"
    return json.loads(FEASIBILITY_JSON.read_text())


def test_markdown_and_overall_disposition(report: dict) -> None:
    assert FEASIBILITY_MD.is_file()
    text = FEASIBILITY_MD.read_text()
    assert "EXTERNAL_FEASIBILITY_BOUNDED" in text
    assert "PRESERVED" in text
    assert report["disposition"] == "EXTERNAL_FEASIBILITY_BOUNDED"
    assert report["overall_confirmatory_status"] == "UNRESOLVED"
    assert report["nemo_evaluation_role"] == "PRESERVED"
    assert report["network"]["new_requests_this_run"] == 0
    assert report["network"]["aggregate_new_download_bytes"] == 0
    assert report["fits"] == 0
    assert report["predictions"] is None


def test_contract_statuses(report: dict) -> None:
    contracts = report["contracts"]
    assert contracts["source_declaration"]["status"] == "ACCEPTED"
    assert contracts["qc_release_discrepancy"]["status"] == "UNRESOLVED"
    assert contracts["specimen_provenance"]["status"] == "UNRESOLVED"
    assert contracts["age_conventions"]["status"] == "ACCEPTED"
    assert contracts["feature_count_semantics"]["status"] == "UNRESOLVED"
    assert contracts["qc_release_discrepancy"]["class_unknown_cells"] == 3731
    assert contracts["qc_release_discrepancy"]["candidate_count_matches_published"] is True
    assert contracts["qc_release_discrepancy"]["exclusion_applied"] is False
    assert contracts["qc_release_discrepancy"]["qc_reproduced"] is False
    assert contracts["specimen_provenance"]["donor_id_overlap"] == []
    assert contracts["feature_count_semantics"]["payload_downloaded"] is False
    assert contracts["age_conventions"]["age_overlap"]["donors_per_class"] == {
        "0": 8,
        "1": 10,
    }


def test_nemo_metadata_anchors(report: dict) -> None:
    meta = report["nemo_metadata_report"]
    assert meta["metadata_cells"] == 117_532
    assert meta["published_cells"] == 113_801
    assert meta["count_difference"] == 3731
    assert meta["n_donors"] == 26
    assert meta["donors_per_class"] == {"0": 13, "1": 13}
    assert meta["annotation_diagnostics"]["status"] == (
        "ANNOTATION_COUNT_MATCH_QC_UNVERIFIED"
    )
    assert meta["annotation_diagnostics"]["candidate"]["qc_threshold_counters"] == {
        "atac_count_le_100": 1751,
        "mitochondrial_percent_ge_5": 6,
        "either": 1757,
    }
    assert meta["paired_matrices_checked"] is False
    assert meta["confirmatory_ready"] is False


def test_role_alternatives_and_invariants(report: dict) -> None:
    cmp_ = report["comparison_current_vs_external"]
    assert cmp_["nemo_switched_to_development"] is False
    assert cmp_["nemo_evaluation_role_preserved"] is True
    assert set(cmp_["external_candidate_nemo"]["blocking_contracts"]) >= {
        "qc_release_discrepancy",
        "specimen_provenance",
        "feature_count_semantics",
    }
    ids = {row["id"] for row in report["alternatives"]}
    assert ids == {"GSE280175", "GSE204684"}
    assert all(row["status"] == "EXPLORATORY_ONLY" for row in report["alternatives"])
    assert len(report["alternatives"]) == 2
    inv = report["scientific_invariants"]
    assert inv["primary"] == "B_NULL"
    assert inv["prior_s8"] == "NO FIT"
    assert inv["power"] == "POWER_UNESTABLISHED"
    assert inv["no_dataset_defect_from_null_alone"] is True


def test_live_offline_bag_and_identity_hash() -> None:
    mod = _load_script()
    assert SOURCE_IDENTITY.is_file()
    raw = SOURCE_IDENTITY.read_bytes()
    import hashlib

    assert hashlib.sha256(raw).hexdigest() == EXPECTED_SOURCE_IDENTITY_SHA256
    bag = Path(
        "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/"
        "input_feasibility_20260912/source/source-bag.tgz"
    ).read_bytes()
    report = {"decoded_bytes": 0}
    payload = mod.source.validate_bag(bag, report)
    assert payload["bytes"] == 1_540_753_269
    assert payload["md5"] == "796c8b3aa587b257af0a46615a437dba"
    assert "VuongWeber_2025_DSdevctx_atac_counts_20260128.mex.tar.gz" in payload["url"]
