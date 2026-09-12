"""No Docker required: verify launch bounds and independent sparse transcript checks."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def script_import_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))


def reader():
    spec = importlib.util.spec_from_file_location(
        "run_r_fixture", Path(__file__).parents[1] / "scripts/run_r_fixture.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_limits_and_no_network_or_mounts():
    args = reader().create_args("p22-test", "sha256:" + "0" * 64, ["Rscript", "-"], 4096)
    for option, value in (
        ("--memory", "4096m"),
        ("--memory-swap", "4096m"),
        ("--network", "none"),
        ("--pids-limit", "32"),
        ("--user", "65534:65534"),
        ("--log-driver", "none"),
    ):
        assert args[args.index(option) + 1] == value
    assert "--read-only" in args and "--mount" not in args and "--privileged" not in args
    assert args[args.index("--pull") + 1] == "never"


def test_sparse_transcript_is_checked_independently():
    module = reader()
    valid = "\n".join(module.EXPECTED_LINES)
    module.verify_transcript(valid)
    for bad in (
        valid.replace("\t7", "\t8"),
        valid.replace("donor_2", "donor_9"),
        valid.replace("dgCMatrix", "matrix"),
        valid + "\nENTRY\t1\t1\t9",
    ):
        with pytest.raises(ValueError):
            module.verify_transcript(bad)


@pytest.mark.parametrize(
    "field",
    [
        "Memory",
        "MemorySwap",
        "NetworkMode",
        "ReadonlyRootfs",
        "PidsLimit",
        "NanoCpus",
        "ShmSize",
        "CapDrop",
        "SecurityOpt",
        "Tmpfs",
        "Privileged",
        "LogConfig",
        "User",
        "Mounts",
        "Volumes",
        "CapAdd",
        "Devices",
        "Healthcheck",
    ],
)
def test_changed_control_refuses_before_start(monkeypatch, field):
    module = reader()
    inspected = {
        "HostConfig": {
            "Memory": 4096 * 1024**2,
            "MemorySwap": 4096 * 1024**2,
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "PidsLimit": 32,
            "NanoCpus": 2000000000,
            "ShmSize": 1024**2,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges"],
            "LogConfig": {"Type": "none"},
            "Tmpfs": {"/tmp": "rw,nosuid,nodev,noexec,size=64m,mode=1777"},
            "Privileged": False,
        },
        "Config": {"User": "65534:65534", "Volumes": None, "Healthcheck": {"Test": ["NONE"]}},
        "Mounts": [],
    }
    module.verify_container(inspected, 4096)
    if field in ("User", "Volumes"):
        inspected["Config"][field] = "invalid"
    elif field == "Healthcheck":
        inspected["Config"][field] = {"Test": ["CMD-SHELL", "unexpected"]}
    elif field == "Mounts":
        inspected[field] = [{"Type": "volume"}]
    else:
        inspected["HostConfig"][field] = (
            {"Type": "json-file"} if field == "LogConfig" else "invalid"
        )
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: pytest.fail("started"))

    def docker(args, **kwargs):
        calls.append(args[0])
        return json.dumps([inspected])

    monkeypatch.setattr(module, "docker", docker)
    with pytest.raises(ValueError, match="CONTAINER_LIMIT_MISMATCH"):
        module.run_owned("sha256:" + "0" * 64, ["Rscript", "-"])
    assert calls == ["inspect", "rm"]


def test_missing_dependency_remains_not_run(tmp_path, monkeypatch):
    module = reader()
    image = module.pinned_config()["image_config_digest"]
    monkeypatch.setattr(module.shutil, "which", lambda _: "docker")
    monkeypatch.setattr(module, "docker", lambda *args, **kwargs: image)
    monkeypatch.setattr(
        module,
        "run_owned",
        lambda *args, **kwargs: {
            "timeout": False,
            "state": {"ExitCode": 1},
            "output": "NOT_RUN: Matrix absent",
        },
    )
    result = module.run(tmp_path / "result")
    assert result["status"] == "NOT_RUN"
    assert result["reason"] == "READER_DEPENDENCY_ABSENT"
    assert result["scientific_gate_effect"] == "NONE"
