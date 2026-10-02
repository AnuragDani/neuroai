"""E0 portable provenance: archives, measured digests, 30 sidecars."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from p22.eval.execution_repair_provenance import (
    DEFAULT_ATAC_REL,
    DEFAULT_H5AD_REL,
    build_provenance_report,
    default_atac_path,
    default_h5ad_path,
    verify_archives,
    verify_measured_inputs,
    verify_pilot_sidecars,
)
from p22.eval import masked_atac_pilot as pilot

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "tasks" / "provenance_e0.json"
OUT_MD = ROOT / "tasks" / "PROVENANCE_E0.md"
CONTRACT = ROOT / "configs" / "execution_repair_portable_inputs_2026-10-02.json"


@pytest.fixture(scope="module")
def report() -> dict:
    assert CONTRACT.is_file(), f"missing {CONTRACT}"
    return build_provenance_report(ROOT)


def test_contract_and_report_files(report: dict) -> None:
    assert CONTRACT.is_file()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["stage"] == "E0"
    assert "atac_counts_npz" in contract["paths"]
    assert report["disposition"] == "PORTABLE_PROVENANCE_PASS"
    assert OUT_JSON.is_file(), "run scripts/report_execution_repair_provenance_e0.py"
    assert OUT_MD.is_file()
    text = OUT_MD.read_text(encoding="utf-8")
    assert "PORTABLE_PROVENANCE_PASS" in text
    assert "B_NULL" in text
    assert "NOT_AUTHORIZED" in text


def test_measured_inputs_portable(report: dict) -> None:
    measured = verify_measured_inputs(ROOT)
    assert measured["all_required_digests_match"] is True
    assert measured["matrix"]["match"] is True
    assert measured["union_bed"]["match"] is True
    assert measured["region_sets"]["match"] is True
    assert measured["ordered_cells_from_counts_json"]["match"] is True
    assert measured["former_worktree_atac_resolves"] is False
    assert default_atac_path(ROOT).is_file()
    assert default_h5ad_path(ROOT).is_file()
    assert str(pilot.DEFAULT_ATAC) == DEFAULT_ATAC_REL
    assert str(pilot.DEFAULT_H5AD) == DEFAULT_H5AD_REL
    assert "P22-gnhf-worktrees" not in str(pilot.DEFAULT_ATAC)
    assert report["checks"]["canonical_paths_resolve_without_worktrees"] is True


def test_archives_and_missing_worktrees(report: dict) -> None:
    archives = verify_archives(ROOT)
    assert archives["n_archives"] == 28
    assert archives["all_archives_match"] is True
    assert archives["all_live_worktrees_absent"] is True
    assert report["checks"]["archives_immutable_hashes_ok"] is True


def test_thirty_sidecars_and_ledger_pins(report: dict) -> None:
    sidecars = verify_pilot_sidecars(ROOT)
    assert sidecars["n_sidecars_expected"] == 30
    assert sidecars["all_sidecars_match"] is True
    assert sidecars["all_ledger_pins_match"] is True
    assert report["checks"]["pilot_sidecars_retain_exact_hashes"] is True
    assert report["scientific_status_unchanged"]["masked_atac_m9"] == "NOT_AUTHORIZED"
    assert report["scientific_status_unchanged"]["primary"] == "B_NULL"
