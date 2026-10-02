"""Helpers for post-smoke M8 lock tests: never permanently reset production counters."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

LOCKED_ZERO_COUNTER = {
    "stage": "masked_atac_pilot_20261001",
    "scientific_fits": {"used": 0, "cap": 40},
    "smoke_fits": {"used": 0, "cap": 5},
    "total_attempts": {"used": 0, "hard_cap": 40},
    "fitting_hours": {"used": 0.0, "cap": 6.0},
    "artifacts_gib": {"used": 0.0, "cap": 4.0},
    "network_bytes": 0,
    "workers": 1,
    "torch_threads": 2,
    "overwrite_policy": (
        "refuse_shared_old_roots_and_second_write_of_existing_sidecars"
    ),
    "note": (
        "M0 zeroed counters; reserve before dispatch; never reset after interruption"
    ),
}
LOCKED_ZERO_COUNTER_SHA256 = (
    "5a801b6c1aa821b4e11ad8058f044c11efb3b65d0ff8af1112b00b606e1b8be1"
)


@contextmanager
def temporarily_zeroed_attempt_counter(counter_path: Path) -> Iterator[bytes]:
    """Swap in the locked zero counter for hash-gate checks; restore exactly after.

    Production counters must not be permanently reset after M9 smoke/main.
    """
    original = counter_path.read_bytes()
    zero_text = json.dumps(LOCKED_ZERO_COUNTER, indent=2) + "\n"
    counter_path.write_text(zero_text, encoding="utf-8")
    try:
        yield original
    finally:
        counter_path.write_bytes(original)
