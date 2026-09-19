# tests/test_launcher_head_capture.py
import hashlib
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PINNED = [
    "configs/development_object_source_contract.json",
    "docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md",
    "scripts/capture_development_head.py",
    "scripts/validate_development_head.py",
]
LABEL = "2026-09-08T00:00:00Z"
HIGH_FREE = 10737418240
LOW_FREE = 10737418239


def _deny_socket(*args, **kwargs):
    raise AssertionError("network denied")


def _deny_subprocess(*args, **kwargs):
    raise AssertionError("subprocess denied")


@pytest.fixture(autouse=True)
def deny_runtime(monkeypatch):
    monkeypatch.setattr(socket, "create_connection", _deny_socket)
    monkeypatch.setattr(socket, "getaddrinfo", _deny_socket)
    monkeypatch.setattr(socket, "gethostbyname", _deny_socket)
    monkeypatch.setattr(subprocess, "run", _deny_subprocess)
    monkeypatch.setattr(subprocess, "Popen", _deny_subprocess)
    monkeypatch.setattr(subprocess, "call", _deny_subprocess)
    monkeypatch.setattr(subprocess, "check_call", _deny_subprocess)
    monkeypatch.setattr(subprocess, "check_output", _deny_subprocess)


@pytest.fixture
def launcher(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    import launcher_head_capture

    return launcher


@pytest.fixture
def workspace(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for rel in PINNED:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    gen = root / "reports" / "generated"
    gen.mkdir(parents=True)
    return root


def _run(launcher, repo, output, label=LABEL, free=HIGH_FREE):
    import shutil as sh

    launcher.shutil.disk_usage = lambda _p: type("U", (), {"free": free})()
    return launcher.preflight(repo=repo, output_dir=output, observed_at=label)


def _ok(launcher, repo, output, label=LABEL, free=HIGH_FREE):
    res = _run(launcher, repo, output, label, free)
    assert res["status"] == "OFFLINE_PREFLIGHT_OK"
    assert res["reason"] is None
    assert res["observed_at"] == label
    assert res["requests_attempted"] == 0
    assert res["body_bytes"] == 0
    assert res["live_allowed"] is False
    assert res["runtime_controls"] == "UNVERIFIED"
    assert res["output_reserved"] is False
    assert res["scientific_gate_effect"] == "NONE"
    assert res["disk_free_bytes"] == free
    assert len(res["source_hashes"]) == 4
    for rel in PINNED:
        assert res["source_hashes"][rel] == hashlib.sha256((repo / rel).read_bytes()).hexdigest()
    return res


def _refuse(launcher, repo, output, reason, label=LABEL, free=HIGH_FREE):
    res = _run(launcher, repo, output, label, free)
    assert res["status"] == "REFUSED"
    assert res["reason"] == reason
    assert res["observed_at"] is None
    assert res["requests_attempted"] == 0
    assert res["body_bytes"] == 0
    assert res["live_allowed"] is False
    assert res["runtime_controls"] == "UNVERIFIED"
    assert res["output_reserved"] is False
    assert res["scientific_gate_effect"] == "NONE"
    return res


def test_ok(launcher, workspace):
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new")


def test_ok_low_disk(launcher, workspace):
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new", free=LOW_FREE)


@pytest.mark.parametrize("label", [
    "", "x" * 65, "a\x00b", "a\x7fb", "a\x80b", "a\x7fb", "a\x7fb", "a\x7fb",
    123, None, b"2026", ["2026"],
])
def test_bad_label(launcher, workspace, label):
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "BAD_LABEL", label)


def test_bad_label_no_disk(launcher, workspace):
    import shutil as sh

    def boom(_p):
        raise AssertionError("disk should not be checked")

    launcher.shutil.disk_usage = boom
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "BAD_LABEL", "a\x00b")


def test_unsafe_path_relative(launcher, workspace):
    _refuse(launcher, workspace, Path("reports/generated/new"), "UNSAFE_PATH")


def test_unsafe_path_outside(launcher, workspace, tmp_path):
    _refuse(launcher, workspace, tmp_path / "out", "UNSAFE_PATH")


def test_unsafe_path_dotdot(launcher, workspace):
    _refuse(launcher, workspace, workspace / "reports" / "generated" / ".." / "new", "UNSAFE_PATH")


def test_output_exists(launcher, workspace):
    out = workspace / "reports" / "generated" / "new"
    out.mkdir()
    _refuse(launcher, workspace, out, "OUTPUT_EXISTS")


def test_output_exists_file(launcher, workspace):
    out = workspace / "reports" / "generated" / "new"
    out.write_text("x")
    _refuse(launcher, workspace, out, "OUTPUT_EXISTS")


def test_missing_input(launcher, workspace):
    (workspace / PINNED[0]).unlink()
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "INPUT_UNAVAILABLE")


def test_symlink_input(launcher, workspace):
    target = workspace / PINNED[0]
    target.unlink()
    (workspace / "link").write_text("x")
    os.symlink(workspace / "link", target)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH")


def test_file_too_large(launcher, workspace):
    target = workspace / PINNED[0]
    target.write_bytes(b"x" * 65537)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "FILE_TOO_LARGE")


def test_pin_mismatch(launcher, workspace):
    target = workspace / PINNED[0]
    target.write_bytes(b"tampered")
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "PIN_MISMATCH")


def test_disk_error(launcher, workspace):
    import shutil as sh

    def boom(_p):
        raise OSError("disk error")

    launcher.shutil.disk_usage = boom
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "INPUT_UNAVAILABLE")


def test_disk_low(launcher, workspace):
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "DISK_HEADROOM", free=LOW_FREE - 1)


def test_repo_symlink(launcher, tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    for rel in PINNED:
        target = real / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    (real / "reports" / "generated").mkdir(parents=True)
    link = tmp_path / "link"
    os.symlink(real, link)
    _refuse(launcher, link, link / "reports" / "generated" / "new", "UNSAFE_PATH")


def test_generated_symlink(launcher, workspace):
    gen = workspace / "reports" / "generated"
    gen.rmdir()
    os.symlink(workspace / "reports", gen)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH")


def test_no_output_created(launcher, workspace):
    out = workspace / "reports" / "generated" / "new"
    _ok(launcher, workspace, out)
    assert not out.exists()


def test_input_unchanged(launcher, workspace):
    before = {rel: (workspace / rel).read_bytes() for rel in PINNED}
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new")
    after = {rel: (workspace / rel).read_bytes() for rel in PINNED}
    assert before == after


# END OF FILE
