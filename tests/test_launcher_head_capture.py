# tests/test_launcher_head_capture.py
import hashlib
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from types import SimpleNamespace

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
    root = tmp_path.resolve() / "repo"
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
        monkeypatch.setattr(launcher.shutil, "disk_usage", lambda _p: SimpleNamespace(free=free))
    result = launcher.preflight(repo=repo, output_dir=output, observed_at=label)
    assert set(result) == {
        "status",
        "reason",
        "observed_at",
        "source_hashes",
        "disk_free_bytes",
        "requests_attempted",
        "body_bytes",
        "live_allowed",
        "runtime_controls",
        "output_reserved",
        "scientific_gate_effect",
    }
    assert len(json.dumps(result)) < 4096
    return result


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


def _refuse(launcher, repo, output, reason, label=LABEL, free=HIGH_FREE, monkeypatch=None):
    res = _run(launcher, repo, output, label, free, monkeypatch)
    assert res["status"] == "REFUSED"
    assert res["reason"] == reason
    assert res["observed_at"] == (None if reason == "BAD_LABEL" else label)
    assert res["requests_attempted"] == 0
    assert res["body_bytes"] == 0
    assert res["live_allowed"] is False
    assert res["runtime_controls"] == "UNVERIFIED"
    assert res["output_reserved"] is False
    assert res["scientific_gate_effect"] == "NONE"
    return res


def test_ok(launcher, workspace, monkeypatch):
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new", monkeypatch=monkeypatch)


@pytest.mark.parametrize("label", ["a", "x" * 64])
def test_valid_label_boundaries(launcher, workspace, monkeypatch, label):
    _ok(
        launcher,
        workspace,
        workspace / "reports/generated/new",
        label=label,
        monkeypatch=monkeypatch,
    )


@pytest.mark.parametrize(
    "label",
    [
        "",
        "x" * 65,
        "a\x00b",
        "a\x7fb",
        "a\x80b",
        123,
        None,
        b"2026",
        ["2026"],
    ],
)
def test_bad_label(launcher, workspace, label, monkeypatch):
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "BAD_LABEL",
        label,
        monkeypatch=monkeypatch,
    )


def test_bad_label_no_disk(launcher, workspace, monkeypatch):
    def boom(_p):
        raise AssertionError("disk should not be checked")

    monkeypatch.setattr(launcher.shutil, "disk_usage", boom)
    _refuse(launcher, workspace, workspace / "reports/generated/new", "BAD_LABEL", "a\x00b")


def test_unsafe_path_relative(launcher, workspace, monkeypatch):
    _refuse(
        launcher, workspace, Path("reports/generated/new"), "UNSAFE_PATH", monkeypatch=monkeypatch
    )


def test_unsafe_path_outside(launcher, workspace, tmp_path, monkeypatch):
    _refuse(launcher, workspace, tmp_path / "out", "UNSAFE_PATH", monkeypatch=monkeypatch)


def test_unsafe_path_dotdot(launcher, workspace, monkeypatch):
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / ".." / "new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


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
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "INPUT_UNAVAILABLE",
        monkeypatch=monkeypatch,
    )


def test_symlink_input(launcher, workspace, monkeypatch):
    target = workspace / PINNED[0]
    target.unlink()
    (workspace / "link").write_text("x")
    os.symlink(workspace / "link", target)
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


def test_file_too_large(launcher, workspace, monkeypatch):
    target = workspace / PINNED[0]
    target.write_bytes(b"x" * 65537)
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "FILE_TOO_LARGE",
        monkeypatch=monkeypatch,
    )


def test_pin_mismatch(launcher, workspace, monkeypatch):
    target = workspace / PINNED[0]
    target.write_bytes(b"tampered")
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "PIN_MISMATCH",
        monkeypatch=monkeypatch,
    )


def test_disk_error(launcher, workspace, monkeypatch):
    def boom(_p):
        raise OSError("disk error")

    monkeypatch.setattr(launcher.shutil, "disk_usage", boom)
    _refuse(launcher, workspace, workspace / "reports/generated/new", "INPUT_UNAVAILABLE")


def test_disk_low(launcher, workspace, monkeypatch):
    result = _refuse(
        launcher,
        workspace,
        workspace / "reports/generated/new",
        "DISK_HEADROOM",
        free=LOW_FREE,
        monkeypatch=monkeypatch,
    )
    assert result["disk_free_bytes"] == LOW_FREE


def test_repo_symlink(launcher, tmp_path, monkeypatch):
    real = tmp_path.resolve() / "real"
    real.mkdir()
    for rel in PINNED:
        target = real / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, target)
    (real / "reports" / "generated").mkdir(parents=True)
    link = tmp_path / "link"
    os.symlink(real, link)
    _refuse(
        launcher,
        link,
        link / "reports" / "generated" / "new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


def test_generated_symlink(launcher, workspace, monkeypatch):
    gen = workspace / "reports" / "generated"
    gen.rmdir()
    os.symlink(workspace / "reports", gen)
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


def test_no_output_created(launcher, workspace, monkeypatch):
    out = workspace / "reports" / "generated" / "new"
    _ok(launcher, workspace, out, monkeypatch=monkeypatch)
    assert not out.exists()


def test_input_unchanged(launcher, workspace, monkeypatch):
    before = {rel: (workspace / rel).read_bytes() for rel in PINNED}
    _ok(launcher, workspace, workspace / "reports" / "generated" / "new", monkeypatch=monkeypatch)
    after = {rel: (workspace / rel).read_bytes() for rel in PINNED}
    assert before == after


@pytest.mark.parametrize("rel", PINNED)
def test_tamper_each_file(launcher, workspace, monkeypatch, rel):
    target = workspace / rel
    original = target.read_bytes()
    target.write_bytes(bytes([original[0] ^ 1]) + original[1:])
    result = _refuse(
        launcher,
        workspace,
        workspace / "reports/generated/new",
        "PIN_MISMATCH",
        monkeypatch=monkeypatch,
    )
    assert list(result["source_hashes"]) == PINNED[: PINNED.index(rel)]


@pytest.mark.parametrize("kind", ["fifo", "directory"])
def test_nonregular_input_refused(launcher, workspace, monkeypatch, kind):
    target = workspace / PINNED[0]
    target.unlink()
    if kind == "fifo":
        os.mkfifo(target)
    else:
        target.mkdir()
    _refuse(
        launcher,
        workspace,
        workspace / "reports/generated/new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


def test_source_parent_symlink(launcher, workspace, monkeypatch):
    real_dir = workspace / "real_configs"
    real_dir.mkdir()
    shutil.copyfile(REPO / PINNED[0], real_dir / "development_object_source_contract.json")
    (workspace / PINNED[0]).unlink()
    (workspace / "configs").rmdir()
    os.symlink(real_dir, workspace / "configs")
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


def test_missing_generated_parent(launcher, workspace, monkeypatch):
    (workspace / "reports" / "generated").rmdir()
    _refuse(
        launcher,
        workspace,
        workspace / "reports" / "generated" / "new",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


def test_dangling_output_symlink(launcher, workspace, monkeypatch):
    out = workspace / "reports" / "generated" / "new"
    os.symlink(workspace / "nonexistent_target", out)
    _refuse(launcher, workspace, out, "OUTPUT_EXISTS", monkeypatch=monkeypatch)


@pytest.mark.parametrize("flag", ["O_NOFOLLOW", "O_NONBLOCK"])
def test_missing_safety_flag_refuses_before_open(launcher, workspace, monkeypatch, flag):
    def forbidden(*args, **kwargs):
        raise AssertionError("open without required controls")

    monkeypatch.delattr(os, flag)
    monkeypatch.setattr(os, "open", forbidden)
    result = launcher.preflight(
        repo=workspace, output_dir=workspace / "reports/generated/new", observed_at=LABEL
    )
    assert result["status"] == "REFUSED"
    assert result["reason"] == "INPUT_UNAVAILABLE"


@pytest.mark.parametrize("operation", ["open", "fstat", "read", "close"])
def test_file_io_failure_refuses_and_closes(launcher, workspace, monkeypatch, operation):
    real_close = os.close
    closed = []

    def close(fd):
        real_close(fd)
        closed.append(fd)
        if operation == "close":
            raise OSError("private close detail")

    def failure(*args, **kwargs):
        raise OSError("private I/O detail")

    with monkeypatch.context() as patch:
        patch.setattr(os, "close", close)
        if operation != "close":
            patch.setattr(os, operation, failure)
        result = launcher.preflight(
            repo=workspace, output_dir=workspace / "reports/generated/new", observed_at=LABEL
        )
    assert result["status"] == "REFUSED"
    assert result["reason"] == "INPUT_UNAVAILABLE"
    assert len(closed) == (0 if operation == "open" else 1)
    assert result["source_hashes"] == {}


@pytest.mark.parametrize("extra", [1, 70000])
def test_growing_file_never_accepts_pinned_prefix(launcher, workspace, monkeypatch, extra):
    data = (workspace / PINNED[0]).read_bytes() + b"x" * extra
    position = 0
    requested = []

    def read(fd, size):
        nonlocal position
        requested.append((position, size))
        chunk = data[position : position + size]
        position += len(chunk)
        return chunk

    monkeypatch.setattr(os, "read", read)
    result = launcher.preflight(
        repo=workspace, output_dir=workspace / "reports/generated/new", observed_at=LABEL
    )
    assert result["status"] == "REFUSED"
    assert result["reason"] == ("FILE_TOO_LARGE" if extra == 70000 else "PIN_MISMATCH")
    assert position <= 65537
    assert all(0 < size <= 65537 - offset for offset, size in requested)
    assert result["source_hashes"] == {}


@pytest.mark.parametrize("free", [True, 10737418240.0, "10737418240", None])
def test_disk_observation_requires_integer(launcher, workspace, monkeypatch, free):
    result = _run(
        launcher, workspace, workspace / "reports/generated/new", free=free, monkeypatch=monkeypatch
    )
    assert result["status"] == "REFUSED"
    assert result["disk_free_bytes"] is None


def test_bad_label_has_no_filesystem_observation(launcher, workspace, monkeypatch):
    output = workspace / "reports/generated/new"

    def forbidden(*args, **kwargs):
        raise AssertionError("bad label touched filesystem")

    with monkeypatch.context() as patch:
        patch.setattr(os, "open", forbidden)
        patch.setattr(Path, "stat", forbidden)
        patch.setattr(Path, "lstat", forbidden)
        patch.setattr(shutil, "disk_usage", forbidden)
        result = launcher.preflight(repo=workspace, output_dir=output, observed_at="bad\n")
    assert result["reason"] == "BAD_LABEL"
    assert result["observed_at"] is None
    assert result["source_hashes"] == {}
    assert result["disk_free_bytes"] is None


def test_nul_output_path_refused(launcher, workspace, monkeypatch):
    _refuse(
        launcher,
        workspace,
        workspace / "reports/generated/new\0",
        "UNSAFE_PATH",
        monkeypatch=monkeypatch,
    )


@pytest.mark.parametrize("method", ["is_dir", "exists"])
def test_path_observation_error_refused(launcher, workspace, monkeypatch, method):
    output = workspace / "reports/generated/new"

    def failure(*args, **kwargs):
        raise OSError("private path detail")

    with monkeypatch.context() as patch:
        patch.setattr(Path, method, failure)
        result = launcher.preflight(repo=workspace, output_dir=output, observed_at=LABEL)
    assert result["reason"] == "UNSAFE_PATH"
    assert result["status"] == "REFUSED"
