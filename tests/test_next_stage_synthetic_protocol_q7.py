"""Q7 synthetic protocol freeze: fit arithmetic, split support, oracle/shuffle."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
)
PROTOCOL_JSON = OUT / "SYNTHETIC_PROTOCOL.json"
PROTOCOL_MD = OUT / "SYNTHETIC_PROTOCOL.md"
SPLIT_JSON = OUT / "SPLIT_MANIFEST.json"
LEDGER_JSON = OUT / "FIT_LEDGER.json"
SCRIPT = ROOT / "scripts" / "report_next_stage_synthetic_protocol.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_synthetic_protocol", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert PROTOCOL_JSON.is_file(), f"missing {PROTOCOL_JSON}; run Q7 reporter first"
    return json.loads(PROTOCOL_JSON.read_text())


@pytest.fixture(scope="module")
def split_manifest() -> dict:
    assert SPLIT_JSON.is_file()
    return json.loads(SPLIT_JSON.read_text())


def test_markdown_disposition_and_invariants(report: dict) -> None:
    assert PROTOCOL_MD.is_file()
    text = PROTOCOL_MD.read_text()
    assert "PROTOCOL_FROZEN" in text
    assert "S9_analytic_pairing_use_synthetic_20260930" in text
    assert "SEPARATE_NON_PRIMARY" in text
    assert report["disposition"] == "PROTOCOL_FROZEN"
    assert report["protocol_id"] == "S9_analytic_pairing_use_synthetic_20260930"
    assert report["fits"] == 0
    assert report["scientific_invariants"]["primary"] == "B_NULL"
    assert report["scientific_invariants"]["prior_s8"] == "NO FIT"
    assert report["null"]["rejects_chance_bernoulli_ba_band"] is True
    assert report["seeds"]["calibration_decision_disjoint"] is True


def test_fit_arithmetic_matches_ledger_and_cap(report: dict) -> None:
    ledger = json.loads(LEDGER_JSON.read_text())
    fa = report["resources"]["fit_arithmetic"]
    assert fa["total_attempted_fits"] == 49
    assert fa["cap"] == 60
    assert fa["fits_within_cap"] is True
    assert fa["smoke_fold0_rho1"] == 7
    assert fa["screen_rho0"] == 21
    assert fa["screen_rho1"] == 21
    assert ledger["selected_attempted_fits"] == 49
    assert report["resources"]["planned_attempted_fits"] == 49
    assert report["seeds"]["decision_generator_seed"] == 9001
    assert 9001 not in report["seeds"]["headroom_generator_seeds"]


def test_split_manifest_both_classes_and_coverage(split_manifest: dict) -> None:
    assert split_manifest["n_folds"] == 3
    assert split_manifest["n_donors"] == 24
    assert split_manifest["class_balance"] == {"0": 12, "1": 12}
    seen = []
    for fold_idx, fold in split_manifest["folds"].items():
        for part in ("train", "val", "test"):
            counts = fold["class_counts"][part]
            assert counts["0"] >= 1 and counts["1"] >= 1, (fold_idx, part, counts)
        train, val, test = (
            set(fold["train_donors"]),
            set(fold["val_donors"]),
            set(fold["test_donors"]),
        )
        assert not (train & val or train & test or val & test)
        assert len(train) == 12 and len(val) == 4 and len(test) == 8
        seen.extend(fold["test_donors"])
    assert len(seen) == 24 and len(set(seen)) == 24
    assert split_manifest["validation"]["both_classes_every_partition"] is True


def test_live_allocation_matches_manifest(split_manifest: dict) -> None:
    mod = _load_script()
    labels = mod.assign_donor_labels(mod.DECISION_GENERATOR_SEED)
    live = mod.allocate_s9_folds(labels)
    assert live["donor_labels"] == split_manifest["donor_labels"]
    for fold_idx in ("0", "1", "2"):
        assert live["folds"][fold_idx]["test_donors"] == split_manifest["folds"][fold_idx][
            "test_donors"
        ]
        assert live["folds"][fold_idx]["train_donors"] == split_manifest["folds"][
            fold_idx
        ]["train_donors"]


def test_oracle_shuffle_invariants(report: dict) -> None:
    mod = _load_script()
    labels = mod.assign_donor_labels(mod.DECISION_GENERATOR_SEED)
    oracle = mod.verify_oracle_invariants(labels)
    assert oracle["oracle_gate"] == "PASS"
    assert oracle["rho1_oracle_ba"] >= 0.90
    assert oracle["rho0_oracle_ba"] <= 0.70
    assert oracle["rho1_shuffled_oracle_ba"] <= 0.70
    toy = report["oracle"]["toy_verification"]
    assert toy["oracle_gate"] == "PASS"
    assert toy["rho1_oracle_ba"] == pytest.approx(oracle["rho1_oracle_ba"])
    # Advantage contrast is labelled separate / non-primary.
    assert report["evaluation"]["advantage_contrast"]["label"] == "SEPARATE_NON_PRIMARY"
    assert report["evaluation"]["primary_statistic"]["applies_to"] == "cross_attention"


def test_primary_vs_null_and_no_chance_band(report: dict) -> None:
    primary = report["evaluation"]["primary_statistic"]
    null_gate = report["evaluation"]["fitted_mechanism_null_gate"]
    assert primary["rho"] == 1.0
    assert null_gate["rho"] == 0.0
    assert "PAIRING_POSITIVE" in primary["definition"]
    assert "CI lower <= 0" in null_gate["definition"] or "CI lower ≤ 0" in null_gate[
        "definition"
    ]
    assert report["null"]["kind"] == "fitted_pairing_plant_null"
    assert "ENDPOINT_UNRESOLVED" in report["unresolved_flags_retained"]
