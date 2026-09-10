"""Frozen post-hoc RNA donor influence; never replaces replication evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

CONFIG_SHA256 = "d51a69cc997fe3a80615ea76bdf9d9504a5334c05fe09eb8fe77a623d266cf58"


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _unique_object(pairs: list[tuple]) -> dict:
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate key in frozen config")
    return result


def load_config(path: str | Path) -> dict:
    """Only the independently reviewed contract is executable; paths are root-relative."""
    with Path(path).open() as handle:
        config = json.load(handle, object_pairs_hook=_unique_object)
    if canonical_hash(config) != CONFIG_SHA256:
        raise ValueError("frozen config mismatch; review a new protocol before execution")
    return config
