"""Bounded HEAD launcher for P22 E2-M1/M2/M3.

Verifies source hashes, code pins, image identity, and offline/synthetic
transport before any potential network request. Refuses live invocation
without explicit authorization and verified controls.
"""

import hashlib
import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from validate_development_head import parse_head_evidence

PINNED_URL = (
    "https://ftp.ncbi.nlm.nih.gov/geo/series/GSE305nnn/GSE305146/suppl/"
    "GSE305146_seur_integr_labelled_exc_lin_PCW10_20.rda.gz"
)
PINNED_HOST = "ftp.ncbi.nlm.nih.gov"
DEADLINE_SECONDS = 15.0
MAX_HEADER_BYTES = 65536
MAX_OUTPUT_BYTES = 1048576
MIN_FREE_DISK_BYTES = 10737418240
MAX_MEMORY_BYTES = 268435456
MAX_SWAP_BYTES = 0

CONTRACT_SHA = "9a13d8beafa5e00d81f8f985649a6a466c6b4fe3ebf008206f840c32316113f2"
NOTE_SHA = "66b1d8158f5b6c4260085cddb736db2d59de9df610e5dcac5ccfc2c4f63b18b9"
CORE_SHA = "335d35c51b27d48704eaad62a695d74e6e91f456e3148b15abe8d3aff846029c"
PARSER_SHA = "c761489202fdbfaba5153f7a508aefa19028cf87f681bd473382c6c4c713ac9d"
IMAGE_ID = "sha256:f462f91ca01ce7751254e3b528af0fccc3746f158a4a7a73675186718307e47e"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_source_hashes(contract_path: Path, note_path: Path) -> bool:
    try:
        contract_bytes = contract_path.read_bytes()
        note_bytes = note_path.read_bytes()
        contract_sha = hashlib.sha256(contract_bytes).hexdigest()
        note_sha = hashlib.sha256(note_bytes).hexdigest()
        return contract_sha == CONTRACT_SHA and note_sha == NOTE_SHA
    except Exception:
        return False


def verify_code_pins(core_path: Path, parser_path: Path) -> bool:
    try:
        core_sha = _sha256_file(core_path)
        parser_sha = _sha256_file(parser_path)
        return core_sha == CORE_SHA and parser_sha == PARSER_SHA
    except Exception:
        return False


def verify_image(image_id: str) -> bool:
    if image_id != IMAGE_ID:
        return False
    try:
        result = subprocess.run(
            ["docker", "--context", "desktop-linux", "image", "inspect", image_id, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip() == image_id
    except Exception:
        return False


def check_free_disk(output_dir: Path) -> bool:
    try:
        stat = os.statvfs(output_dir)
        free_bytes = stat.f_bavail * stat.f_frsize
        return free_bytes >= MIN_FREE_DISK_BYTES
    except Exception:
        return False


def create_container(name: str, image: str) -> bool:
    args = [
        "docker", "--context", "desktop-linux", "create",
        "--name", name,
        "--pull", "never",
        "--interactive",
        "--no-healthcheck",
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "--memory", f"{MAX_MEMORY_BYTES // (1024*1024)}m",
        "--memory-swap", f"{MAX_MEMORY_BYTES // (1024*1024)}
