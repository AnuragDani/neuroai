"""Read-only E1 capability inventory. No installs, subprocesses or fixture runs."""

import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path


def read_small(path: Path, limit: int = 4096) -> dict:
    try:
        with path.open("rb") as stream:
            value = stream.read(limit + 1)
        return {"text": value[:limit].decode("utf-8", "replace"), "truncated": len(value) > limit}
    except OSError as exc:
        return {"error": type(exc).__name__}


def current_cgroup(text: str, root: Path) -> Path | None:
    rows = [line[3:] for line in text.splitlines() if line.startswith("0::")]
    if len(rows) != 1 or not rows[0].startswith("/"):
        return None
    if ".." in Path(rows[0]).parts:
        return None
    candidate = (root / rows[0].lstrip("/")).resolve()
    return candidate if candidate.is_relative_to(root.resolve()) else None


def snapshot() -> dict:
    membership = read_small(Path("/proc/self/cgroup"))
    cgroup = (
        None
        if membership.get("truncated")
        else current_cgroup(membership.get("text", ""), Path("/sys/fs/cgroup"))
    )
    files = [Path("/proc/self/cgroup"), Path("/proc/self/status")]
    files += (
        [
            cgroup / name
            for name in (
                "cgroup.controllers",
                "cgroup.subtree_control",
                "memory.max",
                "memory.swap.max",
                "memory.peak",
                "memory.events",
                "pids.max",
            )
        ]
        if cgroup is not None
        else []
    )
    mounts = read_small(Path("/proc/mounts"), 65536)
    if "text" in mounts:
        # ponytail: retain relevant mount lines, not a general host inventory.
        mounts["text"] = "\n".join(
            line
            for line in mounts["text"].splitlines()
            if len(line.split()) >= 2
            and line.split()[1] in ("/", "/content", "/tmp", "/sys/fs/cgroup")
        )
    return {
        "schema": "p22-reader-environment-v1",
        "utc": datetime.now(UTC).isoformat(),
        "platform": sys.platform,
        "kernel": list(os.uname()) if hasattr(os, "uname") else None,
        "reader_status": "NOT_RUN",
        "controls_status": "UNVERIFIED",
        "training_allowed": False,
        "dependency_bytes_fetched_by_probe": 0,
        "executables": {
            name: shutil.which(name)
            for name in ("R", "Rscript", "timeout", "systemd-run", "unshare", "docker", "podman")
        },
        "cwd": str(Path.cwd()),
        "disk_free_bytes": shutil.disk_usage(Path.cwd()).free,
        "current_cgroup": str(cgroup) if cgroup is not None else None,
        "cgroup_write_access": os.access(cgroup, os.W_OK) if cgroup is not None else None,
        "files": {str(path): read_small(path) for path in files},
        "mounts": mounts,
    }


if __name__ == "__main__":
    print(json.dumps(snapshot(), indent=2))
