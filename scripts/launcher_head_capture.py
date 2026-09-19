"""P22 launcher slice: read-only offline preflight observation.

Diagnostic-only. No timing, race, or native-control proof. Output path is not
reserved; future launcher must revalidate and own race/resource/authorization
safeguards. Not a live runner.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
from pathlib import Path

PINNED_FILES: tuple[tuple[str, str, int], ...] = (
    (
        "configs/development_object_source_contract.json",
        "9a13d8beafa5e00d81f8f985649a6a466c6b4fe3ebf008206f840c32316113f2",
        6429,
    ),
    (
        "docs/PAIRED_MULTIOME_REMAINING_EVIDENCE_2026-09-08.md",
        "66b1d8158f5b6c4260085cddb736db2d59de9df610e5dcac5ccfc2c4f63b18b9",
        14597,
    ),
    (
        "scripts/capture_development_head.py",
        "335d35c51b27d48704eaad62a695d74e6e91f456e3148b15abe8d3aff846029c",
        7088,
    ),
    (
        "scripts/validate_development_head.py",
        "c761489202fdbfaba5153f7a508aefa19028cf87f681bd473382c6c4c713ac9d",
        4753,
    ),
)
MAX_FILE_SIZE = 65536
MIN_DISK_FREE = 10737418240


def _bad_label(observed_at: object) -> bool:
    if not isinstance(observed_at, str):
        return True
    if not 1 <= len(observed_at) <= 64:
        return True
    return any(ord(ch) < 32 or 127 <= ord(ch) <= 159 for ch in observed_at)


def _safe_path(p: Path) -> bool:
    if not p.is_absolute():
        return False
    return ".." not in p.parts and "\0" not in str(p)


def _nonsymlink_ancestors(p: Path) -> bool:
    cur = p
    while True:
        try:
            if cur.is_symlink():
                return False
        except OSError:
            return False
        parent = cur.parent
        if parent == cur:
            return True
        cur = parent


def _check_pinned_file(repo: Path, rel: str, expected: str, expected_size: int) -> str | None:
    target = repo / rel
    if not _nonsymlink_ancestors(target):
        return "UNSAFE_PATH"
    try:
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    except AttributeError:
        return "INPUT_UNAVAILABLE"
    try:
        fd = os.open(target, flags)
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                return "UNSAFE_PATH"
            if st.st_size > MAX_FILE_SIZE:
                return "FILE_TOO_LARGE"
            if st.st_size != expected_size:
                return "PIN_MISMATCH"
            data = bytearray()
            while len(data) <= MAX_FILE_SIZE:
                chunk = os.read(fd, MAX_FILE_SIZE + 1 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
            if len(data) > MAX_FILE_SIZE:
                return "FILE_TOO_LARGE"
            if len(data) != expected_size or hashlib.sha256(data).hexdigest() != expected:
                return "PIN_MISMATCH"
            return None
        finally:
            os.close(fd)
    except OSError:
        return "INPUT_UNAVAILABLE"


def preflight(*, repo: Path, output_dir: Path, observed_at: str) -> dict:
    result: dict = {
        "status": "REFUSED",
        "reason": None,
        "observed_at": None,
        "source_hashes": {},
        "disk_free_bytes": None,
        "requests_attempted": 0,
        "body_bytes": 0,
        "live_allowed": False,
        "runtime_controls": "UNVERIFIED",
        "output_reserved": False,
        "scientific_gate_effect": "NONE",
    }

    if _bad_label(observed_at):
        result["reason"] = "BAD_LABEL"
        return result
    result["observed_at"] = observed_at

    if not isinstance(repo, Path) or not isinstance(output_dir, Path):
        result["reason"] = "UNSAFE_PATH"
        return result
    if not _safe_path(repo) or not _safe_path(output_dir):
        result["reason"] = "UNSAFE_PATH"
        return result
    try:
        if not _nonsymlink_ancestors(repo) or not repo.is_dir():
            result["reason"] = "UNSAFE_PATH"
            return result

        generated = repo / "reports" / "generated"
        if not _nonsymlink_ancestors(generated) or not generated.is_dir():
            result["reason"] = "UNSAFE_PATH"
            return result
        if output_dir.parent != generated:
            result["reason"] = "UNSAFE_PATH"
            return result
        if output_dir.exists() or output_dir.is_symlink():
            result["reason"] = "OUTPUT_EXISTS"
            return result
    except OSError:
        result["reason"] = "UNSAFE_PATH"
        return result

    for rel, expected, _size in PINNED_FILES:
        err = _check_pinned_file(repo, rel, expected, _size)
        if err is not None:
            result["reason"] = err
            return result
        result["source_hashes"][rel] = expected

    try:
        free = shutil.disk_usage(repo).free
    except OSError:
        result["reason"] = "INPUT_UNAVAILABLE"
        return result
    if not isinstance(free, int) or isinstance(free, bool):
        result["reason"] = "DISK_HEADROOM"
        return result
    result["disk_free_bytes"] = free
    if free < MIN_DISK_FREE:
        result["reason"] = "DISK_HEADROOM"
        return result

    result["status"] = "OFFLINE_PREFLIGHT_OK"
    return result
