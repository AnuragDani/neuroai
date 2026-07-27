"""Tests for the legacy Tasic evidence manifest and its README boundary."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = REPO_ROOT / "scripts" / "build_legacy_manifest.py"
MANIFEST_PATH = REPO_ROOT / "legacy" / "tasic_proxy_view" / "manifest.json"
README_PATH = REPO_ROOT / "legacy" / "tasic_proxy_view" / "README.md"
VALID_LABELS = {"verified", "experimental result", "proposed", "inference", "unknown"}


def load_builder():
    name = "build_legacy_manifest_under_test"
    spec = importlib.util.spec_from_file_location(name, BUILDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return load_builder()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_records_eight_files(manifest):
    assert len(manifest["files"]) == 8
    assert len({entry["relative_path"] for entry in manifest["files"]}) == 8


def test_manifest_records_required_fields(manifest):
    for entry in manifest["files"]:
        assert entry["relative_path"].startswith("experiments/")
        assert isinstance(entry["bytes"], int) and entry["bytes"] > 0
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
        assert entry["generator"]
        assert entry["evidence_label"] in VALID_LABELS
        assert entry["description"]


def test_manifest_declares_read_only_legacy_mode(manifest):
    assert manifest["data_mode"] == "legacy read-only"
    assert manifest["source_dataset"]["matrix_tracked_in_repository"] is False
    assert len(manifest["boundary"]) >= 5


def test_manifest_matches_files_on_disk(builder, manifest):
    assert builder.verify_manifest(manifest) == []


def test_rebuild_is_stable(builder, manifest):
    rebuilt = builder.build_manifest()
    assert rebuilt["files"] == manifest["files"]


def test_verify_fails_when_checksum_changes(builder, manifest):
    tampered = json.loads(json.dumps(manifest))
    tampered["files"][0]["sha256"] = "0" * 64
    problems = builder.verify_manifest(tampered)
    assert any("checksum changed" in problem for problem in problems)


def test_verify_fails_when_size_changes(builder, manifest):
    tampered = json.loads(json.dumps(manifest))
    tampered["files"][1]["bytes"] = tampered["files"][1]["bytes"] + 1
    problems = builder.verify_manifest(tampered)
    assert any("byte size changed" in problem for problem in problems)


def test_verify_fails_when_entry_missing(builder, manifest):
    tampered = json.loads(json.dumps(manifest))
    dropped = tampered["files"].pop()
    problems = builder.verify_manifest(tampered)
    assert any(dropped["relative_path"] in problem for problem in problems)


def test_verify_fails_when_expected_file_disappears(builder, manifest, tmp_path):
    problems = builder.verify_manifest(manifest, repo=tmp_path)
    assert len(problems) == len(manifest["files"])
    assert all("disappeared" in problem for problem in problems)


def test_collect_raises_when_expected_file_missing(builder, tmp_path):
    with pytest.raises(FileNotFoundError):
        builder.collect_files(repo=tmp_path)


def test_readme_states_boundary_and_labels():
    text = README_PATH.read_text(encoding="utf-8")
    assert "legacy read-only" in text
    for label in ("verified", "experimental result", "inference", "unknown", "proposed"):
        assert label in text
    for boundary in (
        "Not independent two-modality validation",
        "Not condition-specific evidence",
        "Not an explanation of mechanism",
        "Not leakage-controlled",
        "Not donor-aware",
    ):
        assert boundary in text, boundary


def test_readme_avoids_causal_language():
    text = README_PATH.read_text(encoding="utf-8").lower()
    for phrase in ("proves that", "because the model attends", "causal", "mechanistically"):
        assert phrase not in text, phrase
