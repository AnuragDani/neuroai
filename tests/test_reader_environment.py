"""The preflight reports capabilities; it never certifies a runnable reader."""

import importlib.util
from pathlib import Path

import pytest


def load_probe():
    spec = importlib.util.spec_from_file_location(
        "reader_environment", Path(__file__).parents[1] / "scripts/reader_environment.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bounded_read_preserves_missing_and_truncation(tmp_path):
    probe = load_probe()
    path = tmp_path / "control"
    assert probe.read_small(path) == {"error": "FileNotFoundError"}
    path.write_bytes(b"12345")
    assert probe.read_small(path, 4) == {"text": "1234", "truncated": True}
    assert probe.read_small(path, 5) == {"text": "12345", "truncated": False}


def test_missing_reader_is_not_a_pass(monkeypatch):
    probe = load_probe()
    monkeypatch.setattr(probe.shutil, "which", lambda _: None)
    result = probe.snapshot()
    assert result["reader_status"] == "NOT_RUN"
    assert result["controls_status"] == "UNVERIFIED"
    assert result["training_allowed"] is False
    assert result["executables"]["Rscript"] is None
    assert result["dependency_bytes_fetched_by_probe"] == 0


@pytest.mark.parametrize(
    "text, expected",
    [
        ("0::/", ""),
        ("0::/nested/job", "nested/job"),
        ("0::/../escape", None),
        ("1:memory:/legacy", None),
        ("0::/one\n0::/two", None),
    ],
)
def test_current_cgroup_selection(text, expected, tmp_path):
    probe = load_probe()
    assert probe.current_cgroup(text, tmp_path) == (
        None if expected is None else tmp_path / expected
    )
