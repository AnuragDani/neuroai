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
    monkeypatch.setattr(socket.socket, "connect", _deny_socket)
    monkeypatch.setattr(socket.socket, "connect_ex", _deny_socket)
    monkeypatch.setattr(subprocess, "run", _deny_subprocess)
    monkeypatch.setattr(subprocess, "Popen", _deny_subprocess)
    monkeypatch.setattr(subprocess, "call", _deny_subprocess)
    monkeypatch.setattr(subprocess, "check_call", _deny_subprocess)
    monkeypatch.setattr(subprocess, "check_output", _deny_subprocess)


@pytest.fixture
def launcher(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "scripts"))
    import launcher_head_capture

    return launcher_head_capture


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


def _run(launcher, repo, output, label=LABEL, free=HIGH_FREE, monkeypatch=None):
    if monkeypatch:
        monkeypatch.setattr(launcher.shutil, "disk_usage", lambda _p: type("U", (), {"free": free})())
    return launcher.preflight(repo=repo, output_dir=output, observed_at=label)


def _ok(launcher, repo, output, label=LABEL, free=HIGH_FREE, monkeypatch=None):
    res = _run(launcher, repo, output, label, free, monkeypatch)
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


def _refuse(launcher, repo, output, reason, label=LABEL, free=HIGH_FREE, monkeypatch=None, observed_at=None):
    res = _run(launcher, repo, output, label, free, monkeypatch)
    assert res["status"] == "REFUSED"
    assert res["reason"] == reason
    assert res["observed_at"] == observed_at
    assert res["requests_attempted"] == 0
    assert res["body_bytes"] == 0
    assert res["live_allowed"] is False
    assert res["runtime_controls"] == "UNVERIFIED"
    assert res["output_reserved"] is False
    assert res["scientific_gate_effect"] == "NONE"
    return res


def test_ok(launcher, workspace, monkeypatch):
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new", monkeypatch=monkeypatch)


def test_ok_low_disk(launcher, workspace, monkeypatch):
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new", free=HIGH_FREE, monkeypatch=monkeypatch)


@pytest.mark.parametrize("label", [
    "", "x" * 65, "a\x00b", "a\x7fb", "a\x80b", 123, None, b"2026", ["2026"],
])
def test_bad_label(launcher, workspace, label, monkeypatch):
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "BAD_LABEL", label, monkeypatch=monkeypatch)


def test_bad_label_no_disk(launcher, workspace, monkeypatch):
    def boom(_p):
        raise AssertionError("disk should not be checked")

    monkeypatch.setattr(launcher.shutil, "disk_usage", boom)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "BAD_LABEL", "a\x00b", monkeypatch=monkeypatch)


def test_unsafe_path_relative(launcher, workspace, monkeypatch):
    _refuse(launcher, workspace, Path("reports/generated/new"), "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_unsafe_path_outside(launcher, workspace, tmp_path, monkeypatch):
    _refuse(launcher, workspace, tmp_path / "out", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_unsafe_path_dotdot(launcher, workspace, monkeypatch):
    _refuse(launcher, workspace, workspace / "reports" / "generated" / ".." / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_output_exists(launcher, workspace, monkeypatch):
    out = workspace / "reports" / "generated" / "new"
    out.mkdir()
    _refuse(launcher, workspace, out, "OUTPUT_EXISTS", monkeypatch=monkeypatch)


def test_output_exists_file(launcher, workspace, monkeypatch):
    out = workspace / "reports" / "generated" / "new"
    out.write_text("x")
    _refuse(launcher, workspace, out, "OUTPUT_EXISTS", monkeypatch=monkeypatch)


def test_missing_input(launcher, workspace, monkeypatch):
    (workspace / PINNED[0]).unlink()
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "INPUT_UNAVAILABLE", monkeypatch=monkeypatch)


def test_symlink_input(launcher, workspace, monkeypatch):
    target = workspace / PINNED[0]
    target.unlink()
    (workspace / "link").write_text("x")
    os.symlink(workspace / "link", target)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_file_too_large(launcher, workspace, monkeypatch):
    target = workspace / PINNED[0]
    target.write_bytes(b"x" * 65537)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "FILE_TOO_LARGE", monkeypatch=monkeypatch)


def test_pin_mismatch(launcher, workspace, monkeypatch):
    target = workspace / PINNED[0]
    target.write_bytes(b"tampered")
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "PIN_MISMATCH", monkeypatch=monkeypatch)


def test_disk_error(launcher, workspace, monkeypatch):
    def boom(_p):
        raise OSError("disk error")

    monkeypatch.setattr(launcher.shutil, "disk_usage", boom)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "INPUT_UNAVAILABLE", monkeypatch=monkeypatch)


def test_disk_low(launcher, workspace, monkeypatch):
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "DISK_HEADROOM", free=LOW_FREE, monkeypatch=monkeypatch)


def test_repo_symlink(launcher, tmp_path, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    for rel in PINNED:
        target = real / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    (real / "reports" / "generated").mkdir(parents=True)
    link = tmp_path / "link"
    os.symlink(real, link)
    _refuse(launcher, link, link / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_generated_symlink(launcher, workspace, monkeypatch):
    gen = workspace / "reports" / "generated"
    gen.rmdir()
    os.symlink(workspace / "reports", gen)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_no_output_created(launcher, workspace, monkeypatch):
    out = workspace / "reports" / "generated" / "new"
    _ok(launcher, workspace, out, monkeypatch=monkeypatch)
    assert not out.exists()


def test_input_unchanged(launcher, workspace, monkeypatch):
    before = {rel: (workspace / rel).read_bytes() for rel in PINNED}
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new", monkeypatch=monkeypatch)
    after = {rel: (workspace / rel).read_bytes() for rel in PINNED}
    assert before == after


def test_tamper_each_file(launcher, workspace, monkeypatch):
    for i, rel in enumerate(PINNED):
        target = workspace / rel
        original = target.read_bytes()
        target.write_bytes(original + b"tamper")
        _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "PIN_MISMATCH", monkeypatch=monkeypatch)
        target.write_bytes(original)


def test_fifo_refusal(launcher, workspace, monkeypatch):
    fifo_path = workspace / "fifo_test"
    os.mkfifo(fifo_path)
    target = workspace / PINNED[0]
    target.unlink()
    os.symlink(fifo_path, target)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_source_parent_symlink(launcher, workspace, monkeypatch):
    real_dir = workspace / "real_configs"
    real_dir.mkdir()
    shutil.copyfile(REPO / PINNED[0], real_dir / "development_object_source_contract.json")
    (workspace / "configs").rmdir()
    os.symlink(real_dir, workspace / "configs")
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_missing_generated_parent(launcher, workspace, monkeypatch):
    (workspace / "reports" / "generated").rmdir()
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_dangling_output_symlink(launcher, workspace, monkeypatch):
    out = workspace / "reports" / "generated" / "new"
    os.symlink(workspace / "nonexistent_target", out)
    _refuse(launcher, workspace, out, "OUTPUT_EXISTS", monkeypatch=monkeypatch)


def test_os_read_error(launcher, workspace, monkeypatch):
    original_open = os.open
    original_read = os.read

    def mock_open(path, flags, mode=0o777):
        if path == str(workspace / PINNED[0]):
            return original_open(path, flags, mode)
        return original_open(path, flags, mode)

    def mock_read(fd, size):
        if fd == 3:
            raise OSError("injected read error")
        return original_read(fd, size)

    monkeypatch.setattr(os, "open", mock_open)
    monkeypatch.setattr(os, "read", mock_read)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "INPUT_UNAVAILABLE", monkeypatch=monkeypatch)


def test_no_follow_flag_missing(launcher, workspace, monkeypatch):
    original_open = os.open

    def mock_open(path, flags, mode=0o777):
        if not (flags & os.O_NOFOLLOW):
            raise AssertionError("O_NOFOLLOW flag missing")
        return original_open(path, flags, mode)

    monkeypatch.setattr(os, "open", mock_open)
    _refuse(launcher, workspace, workspace / "reports" / "generated" / "new", "UNSAFE_PATH", monkeypatch=monkeypatch)


# END OF FILE
