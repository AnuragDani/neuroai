"""The real paired acceptance gate refuses automatic scientific promotion."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from p22.eval.real_paired_acceptance import (
    ACCEPTED,
    REFUSED,
    REQUIRED_FAMILIES,
    AcceptanceError,
    build_evidence,
    evaluate_input_acceptance,
    load_manifest,
    load_requirements,
)

UNION_SHA = "u" * 64
H5AD_SHA = "a" * 64
GENE_SHA = "g" * 64
CELLS_SHA = "c" * 64
MATRIX_SHA = "m" * 64
REGIONS_SHA = "r" * 64


def requirements():
    return {
        "record_type": "real_paired_acceptance_requirements",
        "status": "PROSPECTIVE_DECLARATION_BEFORE_CORRECTED_REAL_RUN",
        "rna": {
            "matrix_key": "raw/X",
            "axis_key": "raw/var",
            "genome_build": "GRCh38",
            "require_integer_counts": True,
        },
        "atac": {
            "count_unit": "unique_fragment_overlap",
            "count_mode": "fragment",
            "unknown_policy": "error",
        },
        "regions": {
            "union_sha256": UNION_SHA,
            "n_union_regions": 480,
            "top_n": 256,
            "selection_uses_labels": False,
        },
        "population": {
            "n_donors": 30,
            "n_control": 15,
            "n_positive": 15,
            "label_rule": "disease == 'complete trisomy 21'",
        },
        "protocol": {
            "families": list(REQUIRED_FAMILIES),
            "donor_aggregation": "mean_predicted_probability",
            "donor_threshold": 0.5,
            "practical_margin": 0.07,
            "uncertainty_method": "donor_cluster_percentile_bootstrap",
            "uncertainty_seed": 22,
            "n_repeats": 5,
            "n_folds": 5,
            "split_seed": 0,
        },
    }


def evidence():
    folds = []
    for repeat in range(5):
        for fold in range(5):
            train = [f"train_{repeat}_{fold}_{index}" for index in range(24)]
            test = [f"test_{repeat}_{fold}_{index}" for index in range(6)]
            folds.append(
                {
                    "repeat": repeat,
                    "fold": fold,
                    "train_donors": train,
                    "test_donors": test,
                    "region_set_train_donors": train,
                    "region_set_test_donors": test,
                    "n_regions": 256,
                }
            )
    return {
        "rna": {
            "matrix_key": "raw/X",
            "axis_key": "raw/var",
            "genome_build": "GRCh38",
            "n_cells": 100,
            "n_genes": 50,
            "gene_axis_sha256": GENE_SHA,
            "integer_counts_validated": True,
            "h5ad_sha256": H5AD_SHA,
            "ordered_cells_sha256": CELLS_SHA,
        },
        "atac": {
            "matrix_sha256": MATRIX_SHA,
            "count_mode": "fragment",
            "count_unit": "unique_fragment_overlap",
            "unknown_policy": "error",
            "n_regions": 480,
            "n_cells": 100,
            "cells_sha256": CELLS_SHA,
            "regions_file_sha256": REGIONS_SHA,
        },
        "region_sets": {
            "union_sha256": UNION_SHA,
            "n_union_regions": 480,
            "selection_uses_labels": False,
            "top_n": 256,
            "union_decodes_from_regions_file": True,
        },
        "population": {
            "n_donors": 30,
            "n_control": 15,
            "n_positive": 15,
            "label_rule": "disease == 'complete trisomy 21'",
        },
        "folds": folds,
        "protocol": dict(requirements()["protocol"]),
    }


def manifest():
    return {
        "record_type": "real_paired_input_manifest",
        "rna": {
            "h5ad_sha256": H5AD_SHA,
            "cells_sha256": CELLS_SHA,
            "n_cells": 100,
            "n_genes": 50,
            "gene_axis_sha256": GENE_SHA,
        },
        "atac": {
            "matrix_sha256": MATRIX_SHA,
            "cells_sha256": CELLS_SHA,
            "n_cells": 100,
            "n_regions": 480,
            "regions_file_sha256": REGIONS_SHA,
        },
        "region_sets": {"union_sha256": UNION_SHA, "n_union_regions": 480},
    }


def decide(ev=None, man=None, **kwargs):
    return evaluate_input_acceptance(
        requirements(),
        manifest() if man is None else man,
        evidence() if ev is None else ev,
        n_folds_run=25,
        expected_n_folds=25,
        **kwargs,
    )


def test_valid_evidence_is_accepted_and_promotes():
    decision = decide()
    assert decision.status == ACCEPTED
    assert decision.scientific_claim_allowed is True
    assert decision.final_internal_estimate is True
    assert decision.blocking == ()


def test_missing_manifest_refuses_promotion():
    decision = evaluate_input_acceptance(
        requirements(), None, evidence(), n_folds_run=25, expected_n_folds=25
    )
    assert decision.status == REFUSED
    assert decision.scientific_claim_allowed is False
    assert "manifest_present" in decision.blocking


def test_old_processed_x_and_read_support_unit_are_refused():
    ev = evidence()
    ev["rna"]["matrix_key"] = "X"
    ev["rna"]["axis_key"] = "var"
    ev["rna"]["integer_counts_validated"] = False
    ev["atac"]["count_unit"] = "fragment_overlap_sum"
    decision = decide(ev)
    assert decision.status == REFUSED
    assert {"rna_representation", "atac_unit"} <= set(decision.blocking)


def test_incomplete_fold_run_cannot_be_a_final_estimate():
    decision = evaluate_input_acceptance(
        requirements(), manifest(), evidence(), n_folds_run=1, expected_n_folds=25
    )
    assert decision.status == ACCEPTED
    assert decision.final_internal_estimate is False


def test_rna_artifact_hash_mismatch_refused():
    man = manifest()
    man["rna"]["h5ad_sha256"] = "0" * 64
    assert decide(man=man).status == REFUSED
    assert "rna_artifact" in decide(man=man).blocking


def test_atac_artifact_hash_mismatch_refused():
    man = manifest()
    man["atac"]["matrix_sha256"] = "0" * 64
    decision = decide(man=man)
    assert decision.status == REFUSED
    assert "atac_artifact" in decision.blocking


def test_cell_identity_mismatch_refused():
    ev = evidence()
    ev["atac"]["cells_sha256"] = "d" * 64
    decision = decide(ev)
    assert decision.status == REFUSED
    assert "cell_identity" in decision.blocking


def test_region_identity_mismatch_refused():
    ev = evidence()
    ev["region_sets"]["union_decodes_from_regions_file"] = False
    decision = decide(ev)
    assert decision.status == REFUSED
    assert "region_identity" in decision.blocking


def test_held_out_donor_in_feature_discovery_refused():
    ev = evidence()
    entry = ev["folds"][0]
    entry["region_set_train_donors"] = entry["train_donors"][:-1] + [entry["test_donors"][0]]
    decision = decide(ev)
    assert decision.status == REFUSED
    assert "fold_provenance" in decision.blocking


def test_overlapping_train_test_donors_refused():
    ev = evidence()
    entry = ev["folds"][3]
    entry["test_donors"] = entry["test_donors"][:-1] + [entry["train_donors"][0]]
    entry["region_set_test_donors"] = entry["test_donors"]
    decision = decide(ev)
    assert decision.status == REFUSED
    assert "fold_provenance" in decision.blocking


def test_protocol_margin_and_family_mismatch_refused():
    ev = evidence()
    ev["protocol"]["practical_margin"] = 0.05
    ev["protocol"]["families"] = ev["protocol"]["families"][:-1]
    decision = decide(ev)
    assert decision.status == REFUSED
    assert "protocol_match" in decision.blocking


def test_requirements_must_be_prospective(tmp_path):
    path = tmp_path / "req.json"
    value = requirements()
    value["status"] = "RETROSPECTIVE"
    path.write_text(json.dumps(value))
    with pytest.raises(AcceptanceError):
        load_requirements(path)


def test_manifest_requires_correct_record_type(tmp_path):
    path = tmp_path / "man.json"
    value = manifest()
    value["record_type"] = "something_else"
    path.write_text(json.dumps(value))
    with pytest.raises(AcceptanceError):
        load_manifest(path)


def test_build_evidence_from_real_structures(tmp_path):
    regions = ["chr1:100-200", "chr10:300-400"]
    regions_file = tmp_path / "union.bed"
    regions_file.write_text("chr1\t100\t200\nchr10\t300\t400\n")
    region_sets = {
        "union_regions": regions,
        "union_sha256": UNION_SHA,
        "n_union_regions": 2,
        "selection_uses_labels": False,
        "top_n": 2,
        "per_fold": [
            {
                "repeat": 0,
                "fold": 0,
                "train_donors": ["A", "B"],
                "test_donors": ["C"],
                "regions": regions,
            }
        ],
    }
    folds = [
        SimpleNamespace(repeat=0, fold=0, train_donors=("A", "B"), test_donors=("C",))
    ]
    fingerprints = {
        "h5ad": {"sha256": H5AD_SHA},
        "genome_build": "GRCh38",
        "ordered_cells_sha256": CELLS_SHA,
        "rna_representation": {
            "matrix_key": "raw/X",
            "axis_key": "raw/var",
            "n_cells": 100,
            "n_genes": 50,
            "gene_axis_sha256": GENE_SHA,
            "integer_counts_validated": True,
        },
        "atac_matrix": {"sha256": MATRIX_SHA, "n_regions": 2},
    }
    built = build_evidence(
        fingerprints=fingerprints,
        region_sets=region_sets,
        folds=folds,
        protocol_evidence=dict(requirements()["protocol"]),
        population=dict(requirements()["population"]),
        atac_sidecar={
            "count_mode": "fragment",
            "count_unit": "unique_fragment_overlap",
            "unknown_policy": "error",
            "n_cells": 100,
            "cells_sha256": CELLS_SHA,
        },
        regions_file=regions_file,
    )
    assert built["region_sets"]["union_decodes_from_regions_file"] is True
    assert built["folds"][0]["region_set_train_donors"] == ["A", "B"]
    assert (
        built["atac"]["regions_file_sha256"]
        == hashlib.sha256(regions_file.read_bytes()).hexdigest()
    )
