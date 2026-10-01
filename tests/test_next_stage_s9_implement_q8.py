"""Q8 S9 implement: oracle, pairing, donor isolation, gradients, reload, refusals."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from p22.eval.s9_analytic import (
    ARMS,
    DECISION_GENERATOR_SEED,
    NEURAL_ARMS,
    PROTOCOL_ID,
    TOTAL_FITS,
    S9Refusal,
    allocate_s9_folds,
    assert_donor_isolation,
    assign_donor_labels,
    check_finite_gradients,
    check_state_dict_reload_equality,
    enumerate_s9_jobs,
    fold_row_indices,
    generate_analytic_arrays,
    permute_atac_within_donor,
    refuse_if_not_allowed_raw_root,
    refuse_mismatched_protocol_hash,
    refuse_unreviewed_trainability,
    s9_protocol_from_frozen,
    verify_oracle_invariants,
)
from p22.models.fusion import VIEW_A, VIEW_B

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
)
IMPLEMENT_JSON = OUT / "implement.json"
IMPLEMENT_MD = OUT / "IMPLEMENT.md"
PROTOCOL_JSON = OUT / "SYNTHETIC_PROTOCOL.json"
SCRIPT = ROOT / "scripts" / "report_next_stage_s9_implement.py"


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "report_next_stage_s9_implement", SCRIPT
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def report() -> dict:
    assert IMPLEMENT_JSON.is_file(), f"missing {IMPLEMENT_JSON}; run Q8 reporter first"
    return json.loads(IMPLEMENT_JSON.read_text())


def test_markdown_disposition_and_zero_fits(report: dict) -> None:
    assert IMPLEMENT_MD.is_file()
    text = IMPLEMENT_MD.read_text()
    assert "IMPLEMENT_PASS" in text
    assert PROTOCOL_ID in text
    assert "REFUSED_UNTIL_CHECKPOINT_C" in text or "trainability" in text.lower()
    assert report["disposition"] == "IMPLEMENT_PASS"
    assert report["protocol_id"] == PROTOCOL_ID
    assert report["research_fits_executed"] == 0
    assert report["fits"] == 0
    assert report["scientific_invariants"]["primary"] == "B_NULL"
    assert report["scientific_invariants"]["prior_s8"] == "NO FIT"
    assert report["trainability_with_learning"] == "REFUSED_UNTIL_CHECKPOINT_C"


def test_job_coverage_and_hashes(report: dict) -> None:
    assert report["job_coverage"]["total"] == TOTAL_FITS == 49
    assert report["job_coverage"]["smoke"] == 7
    assert report["job_coverage"]["screen"] == 42
    assert report["job_coverage"]["within_cap"] is True
    assert report["job_coverage"]["job_ids_unique"] is True
    jobs = enumerate_s9_jobs()
    assert len(jobs) == 49
    assert len({j["fit_id"] for j in jobs}) == 49
    proto_sha = report["hashes"]["SYNTHETIC_PROTOCOL.json"]
    assert len(proto_sha) == 64
    assert Path(PROTOCOL_JSON).is_file()


def test_oracle_and_pairing_marginals() -> None:
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    oracle = verify_oracle_invariants(labels)
    assert oracle["oracle_gate"] == "PASS"
    assert oracle["rho1_oracle_ba"] == 1.0
    assert oracle["rho1_shuffled_oracle_ba"] == 0.5
    rna, atac, donor, _, _ = generate_analytic_arrays(
        labels, rho=1.0, generator_seed=DECISION_GENERATOR_SEED
    )
    shuffled = permute_atac_within_donor(atac, donor, seed=4001)
    for name in sorted(set(donor.tolist()), key=str):
        idx = np.flatnonzero(donor == name)
        assert np.allclose(np.sort(atac[idx], axis=0), np.sort(shuffled[idx], axis=0))


def test_donor_isolation_and_leakage_refusal() -> None:
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    split = allocate_s9_folds(labels)
    rna, atac, donor, label_col, _ = generate_analytic_arrays(
        labels, rho=1.0, generator_seed=DECISION_GENERATOR_SEED
    )
    del rna, atac, label_col
    positions = fold_row_indices(donor, split["folds"]["0"])
    assert_donor_isolation(positions, donor)
    leak = {
        "train": positions["train"],
        "val": positions["val"],
        "test": np.concatenate([positions["test"], positions["train"][:2]]),
    }
    with pytest.raises(S9Refusal, match="leakage"):
        assert_donor_isolation(leak, donor)


def test_finite_gradients_and_reload() -> None:
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    rna, atac, _donor, label_col, _ = generate_analytic_arrays(
        labels, rho=1.0, generator_seed=DECISION_GENERATOR_SEED
    )
    views = {VIEW_A: rna.astype(np.float32), VIEW_B: atac.astype(np.float32)}
    proto = s9_protocol_from_frozen()
    for arm in NEURAL_ARMS:
        g = check_finite_gradients(arm, views, label_col, proto)
        assert g["finite"] is True, arm
        r = check_state_dict_reload_equality(arm, views, proto)
        assert r["passed"] is True, arm


def test_refusals_protocol_root_trainability() -> None:
    with pytest.raises(S9Refusal, match="hash mismatch"):
        refuse_mismatched_protocol_hash("a" * 64, "b" * 64)
    with pytest.raises(S9Refusal):
        refuse_if_not_allowed_raw_root("reports/generated/nn_s7_covariance_20260929/")
    with pytest.raises(S9Refusal):
        refuse_if_not_allowed_raw_root("reports/generated/nn_s8_demo/")
    refuse_if_not_allowed_raw_root("reports/generated/nn_s9_analytic_pairing_20260930/")
    with pytest.raises(S9Refusal, match="trainability"):
        refuse_unreviewed_trainability()
    assert len(ARMS) == 7


def test_reporter_rewrites_stable_disposition(tmp_path: Path, report: dict) -> None:
    # Copy frozen inputs into tmp and rewrite implement outputs.
    import shutil

    for name in (
        "SYNTHETIC_PROTOCOL.json",
        "SPLIT_MANIFEST.json",
        "FIT_LEDGER.json",
    ):
        shutil.copy2(OUT / name, tmp_path / name)
    mod = _load_script()
    summary = mod.write_outputs(tmp_path)
    assert summary["disposition"] == "IMPLEMENT_PASS"
    fresh = json.loads((tmp_path / "implement.json").read_text())
    assert fresh["disposition"] == report["disposition"]
    assert fresh["job_coverage"]["total"] == report["job_coverage"]["total"]
    assert fresh["oracle"]["oracle_gate"] == "PASS"
