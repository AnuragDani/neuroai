"""A source URL and matching cell totals cannot pass scientific input gates."""

import copy
import hashlib
import json

import pytest
from scripts import audit_multiome as audit
from scripts import resolve_nemo_source as source

from tests.test_resolve_nemo_source import Opener, Response, bag, pin


def save(path, value):
    path.write_text(json.dumps(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def records(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence.md"
    evidence.write_text("primary source fixture")
    evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
    monkeypatch.setattr(source, "EVIDENCE_PATH", evidence)
    monkeypatch.setattr(source, "EVIDENCE_SHA256", evidence_hash)
    monkeypatch.setattr(audit, "DEVELOPMENT_EVIDENCE_PATH", evidence)
    monkeypatch.setattr(audit, "DEVELOPMENT_EVIDENCE_SHA256", evidence_hash)
    raw = bag()
    pin(monkeypatch, raw)
    source.resolve(tmp_path / "source", opener=Opener(Response(raw)))
    source_path = tmp_path / "source/source_identity.json"
    development = {
        "schema_version": 1,
        "record_kind": "development_object_feasibility",
        "created_utc": "2026-09-12T21:00:00+00:00",
        "selected_object": "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz",
        "source_evidence": {"path": str(evidence), "sha256": evidence_hash},
        "checks": {
            "R": None,
            "Rscript": None,
            "pyreadr": False,
            "rpy2": False,
            "reader_support": "ABSENT_IN_CHECKED_ENVIRONMENT",
            "reader_proof": None,
            "command": "offline fixture inventory",
        },
        "resources": {
            "disk_free_bytes": 20 * 1024**3,
            "host_memory_bytes": 32 * 1024**3,
            "available_memory_bytes": 16 * 1024**3,
            "listed_compressed_size": "7.6G",
            "compressed_bytes": None,
            "decoded_bytes": None,
            "peak_rss_bytes": None,
            "working_disk_bytes": None,
            "unknown_reason": "not inspected",
        },
        "inspection_questions": ["assays", "raw counts", "QC", "donors", "regions", "provenance"],
        "next_action": {
            "id": "ENABLE_R_READER_FIXTURE",
            "description": "Tiny reader fixture",
            "runtime": "isolated R",
            "limits": {
                "network_bytes": 2 * 1024**3,
                "decoded_bytes": 4 * 1024**3,
                "working_disk_bytes": 6 * 1024**3,
                "peak_rss_bytes": 4 * 1024**3,
                "wall_seconds": 1800,
                "minimum_free_disk_bytes": 10 * 1024**3,
                "fixture_input_bytes": 1024**2,
            },
            "enforcement": "bounded supervisor",
            "outputs": ["fixture result"],
            "stop_rule": "stop after fixture",
            "authority": "outside current cycle",
        },
        "scientific_acceptance": False,
        "model_training_performed": False,
    }
    development_path = tmp_path / "development.json"
    dev_hash = save(development_path, development)
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return source_path, source_hash, development_path, dev_hash


def report():
    from p22.data.atac_features import audit_peak_spaces

    return {
        "preflight_status": "COMPLETED",
        "training_allowed": False,
        "model_training_performed": False,
        "manifest_sha256": "a" * 64,
        "files": [],
        "geo": {"retained_cell_barcode_mapping": "PILOT_EXACT_RELEASE_JOIN"},
        "external": {"metadata_cells": 113801, "published_cells": 113801},
        "atac_compatibility": audit_peak_spaces(
            {"A": ["chr1:0-10"], "B": ["chr1:5-15"]},
            genome_builds={"A": "unknown", "B": "unknown"},
            count_units={"A": "fragments", "B": "tn5_insertions"},
        ),
    }


def test_separate_gates_and_next_action(records):
    inputs = audit.load_feasibility_inputs(*records)
    decision = audit.build_input_decision(report(), inputs)
    assert decision["training_allowed"] is False
    assert decision["model_training_performed"] is False
    assert decision["m4"]["status"] == "NEEDS_RECOUNT"
    assert decision["external"]["source_identity"]["status"] == "PASS"
    assert decision["external"]["qc_count_stage"]["status"] == "UNRESOLVED"
    assert decision["development"]["exact_measured_regions"]["status"] == "FAIL"
    assert decision["development"]["donor_pairing"]["status"] == "UNRESOLVED"
    assert decision["cross_cohort"]["exact_measured_regions"]["status"] == "UNRESOLVED"
    assert decision["next_action"]["id"] == "ENABLE_R_READER_FIXTURE"
    assert "uninspected" in audit.render_input_decision(decision).lower()


@pytest.mark.parametrize(
    "case",
    [
        "hash",
        "missing",
        "ledger",
        "payload",
        "source_hash",
        "raw_bag",
        "reader",
        "resource",
        "acceptance",
        "duplicate",
    ],
)
def test_malformed_or_tampered_records_rejected(records, case):
    source_path, source_hash, dev_path, dev_hash = records
    source_record = json.loads(source_path.read_text())
    development = json.loads(dev_path.read_text())
    if case == "hash":
        source_hash = "0" * 64
    elif case == "missing":
        del source_record["body_bytes"]
    elif case == "ledger":
        source_record["body_bytes"] += 1
    elif case == "payload":
        source_record["resolved_payload"]["url"] = "https://example.org/changed"
    elif case == "source_hash":
        source_record["source_evidence"]["sha256"] = "f" * 64
    elif case == "raw_bag":
        (source_path.parent / "source-bag.tgz").write_bytes(b"changed")
    elif case == "reader":
        development["checks"]["reader_support"] = "PROVEN"
    elif case == "resource":
        development["resources"]["compressed_bytes"] = 0
    elif case == "acceptance":
        development["scientific_acceptance"] = True
    elif case == "duplicate":
        dev_path.write_text('{"schema_version":1,"schema_version":2}')
        dev_hash = hashlib.sha256(dev_path.read_bytes()).hexdigest()
    if case != "hash":
        source_hash = save(source_path, source_record)
    if case != "duplicate":
        dev_hash = save(dev_path, development)
    with pytest.raises(ValueError):
        audit.load_feasibility_inputs(source_path, source_hash, dev_path, dev_hash)


def test_source_failure_does_not_change_development_priority(records):
    source_path, _, dev_path, dev_hash = records
    value = json.loads(source_path.read_text())
    value.update(
        request_attempted=False,
        requests=[],
        headers=dict.fromkeys(source.HEADER_NAMES),
        body_bytes=0,
        decoded_bytes=0,
        elapsed_seconds=0,
        body_sha256=None,
        raw_bag_path=None,
        matched_members=[],
        resolved_payload=None,
        stop_reason="SOURCE_IDENTITY_UNRESOLVED",
    )
    inputs = audit.load_feasibility_inputs(
        source_path, save(source_path, value), dev_path, dev_hash
    )
    decision = audit.build_input_decision(report(), inputs)
    assert decision["external"]["source_identity"]["status"] == "UNRESOLVED"
    assert decision["next_action"]["id"] == "ENABLE_R_READER_FIXTURE"
    value["body_bytes"] = 1
    with pytest.raises(ValueError):
        audit.load_feasibility_inputs(source_path, save(source_path, value), dev_path, dev_hash)


def test_failed_audit_cannot_become_scientific_decision(records):
    value = copy.deepcopy(report())
    value["preflight_status"] = "FAILED"
    with pytest.raises(ValueError):
        audit.build_input_decision(value, audit.load_feasibility_inputs(*records))


def test_cli_writes_decision_and_refuses_overwrite_or_partial_evidence(records, tmp_path):
    from tests.test_multiome import asset, geo_soft, mex_assets, nemo_metadata

    manifest = {
        "schema_version": 1,
        "geo": {
            "soft": asset(tmp_path / "family.soft", geo_soft().encode()),
            "published_donors": 1,
            "published_cells": 2,
            "pilot_library": "L1",
            "combined_mex": mex_assets(tmp_path),
            "comparison_library": "L2",
            "comparison_features": mex_assets(tmp_path, "compare")["features"],
        },
        "external": {
            "metadata": asset(
                tmp_path / "metadata.csv", nemo_metadata().to_csv(index=False).encode()
            ),
            "published_donors": 2,
            "published_cells": 2,
            "condition_map": {"Ctrl": 0, "Ts21": 1},
            "columns": {},
            "age_unit": "obstetric_GW",
            "age_source": "documented LMP",
        },
    }
    config = tmp_path / "manifest.json"
    save(config, manifest)
    source_path, source_hash, dev_path, dev_hash = records
    output = tmp_path / "audit"
    args = [
        "--manifest",
        str(config),
        "--output-dir",
        str(output),
        "--source-identity",
        str(source_path),
        "--source-identity-sha256",
        source_hash,
        "--development-feasibility",
        str(dev_path),
        "--development-feasibility-sha256",
        dev_hash,
        "--max-input-bytes",
        "1700000000",
        "--max-expanded-bytes",
        "268435456",
        "--max-nnz",
        "10000000",
        "--cell-cap",
        "256",
    ]
    assert audit.main(args) == 0
    assert (output / "INPUT_DECISION.md").is_file()
    decision = json.loads((output / "input_decision.json").read_text())
    assert decision["training_allowed"] is False
    assert decision["model_training_performed"] is False
    with pytest.raises(SystemExit):
        audit.main(args)
    with pytest.raises(SystemExit):
        audit.main(args[:10])


@pytest.mark.parametrize(
    "changed", ["--max-input-bytes", "--max-expanded-bytes", "--max-nnz", "--cell-cap", "omitted"]
)
def test_decision_cli_rejects_changed_frozen_caps(records, tmp_path, changed):
    source_path, source_hash, dev_path, dev_hash = records
    output = tmp_path / "bad-caps"
    args = [
        "--manifest",
        str(tmp_path / "unused.json"),
        "--output-dir",
        str(output),
        "--source-identity",
        str(source_path),
        "--source-identity-sha256",
        source_hash,
        "--development-feasibility",
        str(dev_path),
        "--development-feasibility-sha256",
        dev_hash,
    ]
    caps = {
        "--max-input-bytes": "1700000000",
        "--max-expanded-bytes": "268435456",
        "--max-nnz": "10000000",
        "--cell-cap": "256",
    }
    if changed == "omitted":
        del caps["--max-input-bytes"]
    else:
        caps[changed] = "1"
    for flag, value in caps.items():
        args += [flag, value]
    with pytest.raises(SystemExit):
        audit.main(args)
    assert not output.exists()
