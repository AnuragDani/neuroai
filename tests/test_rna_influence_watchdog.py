"""Deterministic watchdog races; no scientific workload or external process control."""

import json
import os

import pytest
from scripts import diagnose_rna_replication as cli


class OwnedProcess:
    def __init__(self):
        self.pid = os.getpid() + 100_000
        self.returncode = None
        self.killed = False
        self.wait_count = 0

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self):
        assert self.returncode is not None, "stop the owned child before reaping"
        self.wait_count += 1
        return self.returncode


@pytest.mark.parametrize("exit_code", [0, 7])
def test_observed_memory_stop_survives_concurrent_child_exit(tmp_path, monkeypatch, exit_code):
    process = OwnedProcess()
    monkeypatch.setattr(cli.subprocess, "Popen", lambda *args, **kwargs: process)

    def rss(pid):
        if pid == process.pid:
            process.returncode = exit_code  # Exit races the over-budget RSS response.
            return 1024
        return 64

    monkeypatch.setattr(cli, "_rss_bytes", rss)
    output = tmp_path / "race"
    report = cli.supervise(["owned-fixture"], output, stop_rss_bytes=512)
    assert report["status"] == "MEMORY_LIMIT"
    assert report["exit_code"] == exit_code
    assert report["peak_sampled_rss_bytes"] == 1024
    assert process.wait_count == 1 and not process.killed
    assert json.loads((output / "resources.json").read_text())["status"] == "MEMORY_LIMIT"


def test_monitor_failure_stops_and_reaps_owned_child(tmp_path, monkeypatch):
    process = OwnedProcess()
    monkeypatch.setattr(cli.subprocess, "Popen", lambda *args, **kwargs: process)

    def rss(pid):
        if pid == process.pid:
            raise OSError("child RSS unavailable")
        return 64

    monkeypatch.setattr(cli, "_rss_bytes", rss)
    report = cli.supervise(["owned-fixture"], tmp_path / "monitor-failure")
    assert report["status"] == "MONITOR_ERROR"
    assert report["reason"] == "child RSS unavailable"
    assert report["pid"] == process.pid and report["exit_code"] == -9
    assert process.killed and process.wait_count == 1


def test_missing_monitor_refuses_launch_and_existing_directory_is_preserved(tmp_path, monkeypatch):
    def missing_monitor(pid):
        raise OSError("monitor unavailable before launch")

    def forbidden_launch(*args, **kwargs):
        raise AssertionError("must not launch without an RSS monitor")

    monkeypatch.setattr(cli, "_rss_bytes", missing_monitor)
    monkeypatch.setattr(cli.subprocess, "Popen", forbidden_launch)
    output = tmp_path / "refused"
    report = cli.supervise(["must-not-launch"], output)
    assert report["status"] == "MONITOR_ERROR"
    assert report["pid"] is None and report["exit_code"] is None
    original = (output / "resources.json").read_bytes()
    with pytest.raises(FileExistsError):
        cli.supervise(["must-not-launch"], output)
    assert (output / "resources.json").read_bytes() == original
