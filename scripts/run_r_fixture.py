#!/usr/bin/env python
"""Run only synthetic R fixtures and native isolation checks in the pinned local image."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from acquire_r_image import pinned_config

ROOT = Path(__file__).resolve().parents[1]
DOCKER = ["docker", "--context", "desktop-linux"]
EXPECTED_LINES = [
    "CLASS\tdgCMatrix",
    "ROWS\tchr1:0-10,chr1:20-30,chr2:5-9",
    "COLUMNS\tcell_a,cell_b,cell_c,cell_d",
    "DONORS\tdonor_1,donor_1,donor_2,donor_2",
    "ENTRY\t1\t1\t2",
    "ENTRY\t3\t1\t7",
    "ENTRY\t2\t2\t1",
    "ENTRY\t1\t4\t5",
    "SPARSE_ROUNDTRIP_PASS",
    "SCIENTIFIC_GATES_UNCHANGED",
]
FIXTURE_SHA256 = "aef9ccc1a8c19bf0ab53f848a5edcbb86bbb76195a3dbd288a0520dec67e36e7"


def create_args(name, image, command, memory):
    return (
        DOCKER
        + [
            "create",
            "--name",
            name,
            "--pull",
            "never",
            "--interactive",
            "--no-healthcheck",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "65534:65534",
            "--memory",
            f"{memory}m",
            "--memory-swap",
            f"{memory}m",
            "--pids-limit",
            "32",
            "--cpus",
            "2",
            "--log-driver",
            "none",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777",
            "--shm-size",
            "1m",
            "--entrypoint",
            command[0],
            image,
        ]
        + command[1:]
    )


def docker(args, *, timeout=10):
    return subprocess.run(
        DOCKER + args, text=True, capture_output=True, timeout=timeout, check=True
    ).stdout.strip()


def verify_transcript(output):
    lines = output.splitlines()
    if any(lines.count(expected) != 1 for expected in EXPECTED_LINES):
        raise ValueError("SPARSE_TRANSCRIPT_MISMATCH")
    if sum(line.startswith("ENTRY\t") for line in lines) != 4:
        raise ValueError("SPARSE_ENTRY_COUNT")


def verify_container(inspected, memory):
    config = inspected["HostConfig"]
    expected = {
        "Memory": memory * 1024**2,
        "MemorySwap": memory * 1024**2,
        "NetworkMode": "none",
        "ReadonlyRootfs": True,
        "PidsLimit": 32,
        "NanoCpus": 2000000000,
        "ShmSize": 1024**2,
        "CapDrop": ["ALL"],
        "SecurityOpt": ["no-new-privileges"],
        "Tmpfs": {"/tmp": "rw,nosuid,nodev,noexec,size=64m,mode=1777"},
        "Privileged": False,
    }
    if (
        any(config.get(key) != value for key, value in expected.items())
        or config.get("LogConfig", {}).get("Type") != "none"
        or inspected["Config"].get("User") != "65534:65534"
        or inspected.get("Mounts")
        or inspected["Config"].get("Volumes")
        or inspected["Config"].get("Healthcheck", {}).get("Test") != ["NONE"]
        or config.get("CapAdd")
        or config.get("Devices")
    ):
        raise ValueError("CONTAINER_LIMIT_MISMATCH")
    return expected


def run_owned(image, command, *, payload="", seconds=15, memory=4096):
    name = "p22-r-fixture-" + uuid.uuid4().hex[:12]
    record = {"name": name, "command": command, "timeout": False}
    subprocess.run(
        create_args(name, image, command, memory), check=True, capture_output=True, timeout=10
    )
    try:
        inspected = json.loads(docker(["inspect", name]))[0]
        record["limits"] = verify_container(inspected, memory)
        process = subprocess.Popen(
            DOCKER + ["start", "--attach", "--interactive", name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            output, _ = process.communicate(payload, timeout=seconds)
        except subprocess.TimeoutExpired:
            record["timeout"] = True
            # Killing the owned container stops its cgroup, not just the CLI/PID parent.
            docker(["kill", name])
            output, _ = process.communicate(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
        record["output"] = output
        record["state"] = json.loads(docker(["inspect", name]))[0]["State"]
        if record["state"]["Running"] or record["state"]["Pid"] != 0:
            raise ValueError("DESCENDANTS_NOT_STOPPED")
        return record
    finally:
        # Only this UUID-named container; never prune or stop pre-existing workloads.
        docker(["rm", "--force", name])


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "status": "NOT_RUN",
        "cases": [],
        "dataset_bytes": 0,
        "scientific_gate_effect": "NONE",
        "unsupported_classes": ["Seurat", "ChromatinAssay"],
    }
    start = time.monotonic()
    try:
        if not shutil.which("docker"):
            return report
        config = pinned_config()
        image = config["image_config_digest"]
        if docker(["image", "inspect", image, "--format", "{{.Id}}"]) != image:
            raise ValueError("PINNED_IMAGE_ABSENT")
        report["image_id"] = image
        script = (ROOT / "scripts/inspect_development_object.R").read_text()
        report["fixture_code_sha256"] = hashlib.sha256(script.encode()).hexdigest()
        if report["fixture_code_sha256"] != FIXTURE_SHA256:
            raise ValueError("FIXTURE_CODE_CHANGED")
        report["status"] = "FAIL"
        for mode, error in (
            ("valid", None),
            ("bad_counts", "COUNTS"),
            ("bad_ids", "IDS"),
            ("bad_fields", "FIELDS"),
            ("bad_intervals", "INTERVALS"),
            ("reuse", "OUTPUT_EXISTS"),
        ):
            case = run_owned(image, ["Rscript", "--vanilla", "-", mode], payload=script)
            report["cases"].append(case)
            if case["timeout"]:
                raise ValueError("FIXTURE_TIMEOUT")
            if error:
                if case["state"]["ExitCode"] == 0 or error not in case["output"]:
                    raise ValueError("EXPECTED_REFUSAL_MISSING")
            else:
                if case["state"]["ExitCode"] == 127 or "NOT_RUN: Matrix absent" in case["output"]:
                    report["status"] = "NOT_RUN"
                    raise ValueError("READER_DEPENDENCY_ABSENT")
                if case["state"]["ExitCode"] != 0:
                    raise ValueError("FIXTURE_FAILED")
                verify_transcript(case["output"])
        controls = run_owned(
            image,
            [
                "sh",
                "-c",
                "cat /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.swap.max; "
                "if touch /etc/p22-refuse 2>/dev/null; then exit 4; fi; "
                "if dd if=/dev/zero of=/tmp/over bs=1048576 count=65 2>/dev/null; then exit 5; fi; "
                "echo WRITE_LIMIT_PASS",
            ],
        )
        report["cases"].append(controls)
        if controls["state"]["ExitCode"] != 0 or not all(
            line in controls["output"].splitlines()
            for line in ["4294967296", "0", "WRITE_LIMIT_PASS"]
        ):
            raise ValueError("CONTROL_PROBE_FAILED")
        tree = run_owned(
            image,
            ["sh", "-c", "sh -c 'sleep 120 & echo CHILD=$!; wait' & echo PARENT=$!; wait"],
            seconds=3,
        )
        report["cases"].append(tree)
        if not tree["timeout"] or "CHILD=" not in tree["output"] or "PARENT=" not in tree["output"]:
            raise ValueError("TREE_TIMEOUT_NOT_PROVEN")
        oom = run_owned(
            image,
            [
                "Rscript",
                "--vanilla",
                "-e",
                "system('sleep 120 &'); x <- raw(512*1024^2); Sys.sleep(120)",
            ],
            seconds=15,
            memory=128,
        )
        report["cases"].append(oom)
        if oom["timeout"] or not oom["state"]["OOMKilled"]:
            raise ValueError("OOM_STOP_NOT_PROVEN")
        report["status"] = "PASS_FIXTURE_ONLY"
    except Exception as error:
        report["error_type"] = type(error).__name__
        report["reason"] = str(error) if isinstance(error, ValueError) else "LOCAL_READER_FAILED"
    finally:
        report["elapsed_seconds"] = time.monotonic() - start
        (output / "fixture.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    result = run(parser.parse_args().output_dir)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS_FIXTURE_ONLY" else 1)
