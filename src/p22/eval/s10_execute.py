"""S10 corrected-null serial executor (fits gated on R8 review).

Reuses S7 fit/pairing helpers and S10 corrected generator. Scientific
dispatch is refused until ``REVIEWED_HASHES`` are filled by independent R8
review PASS. Default workers=1 (serial); no ThreadPoolExecutor path.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from p22.eval.s7_ledger import sha256_file
from p22.eval.s10_analytic import (
    ALLOWED_RAW_ROOT,
    DECISION_GENERATOR_SEED,
    DECISION_MODEL_SEED,
    PROTOCOL_ID,
    SCIENTIFIC_ATTEMPT_CAP,
    SYNTHETIC_ARTIFACT_GIB_CAP,
    SYNTHETIC_FITTING_HOURS_CAP,
    TORCH_THREADS,
    TOTAL_FITS,
    WORKERS,
    allocate_s10_folds,
    assign_donor_labels,
    enumerate_s10_jobs,
    generate_corrected_arrays,
    refuse_if_not_allowed_raw_root,
    refuse_mismatched_protocol_hash,
    refuse_unreviewed_scientific_fits,
    s10_protocol_from_frozen,
    verify_oracle_invariants,
)

# Populated only after independent R8 review PASS on exact commit/file hashes.
# Empty / mismatched hashes keep scientific fits refused.
REVIEWED_HASHES: dict[str, str] = {
    "S10_PROTOCOL.json": "",
    "S10_SPLIT_MANIFEST.json": "",
    "src/p22/eval/s10_analytic.py": "",
    "src/p22/eval/s10_execute.py": "",
}

LEDGER_NAME = "attempt_ledger.jsonl"
PROVENANCE_NAME = "provenance.json"
COUNTER_NAME = "attempt_counter.json"
CHECKPOINT_MODELS = frozenset({"cross_attention", "token_concat"})
MARGINAL_BA_MAX = 0.60


class S10ExecuteRefusal(ValueError):
    """Refuse unauthorized or unsafe S10 execution."""


def reviewed_hashes_complete() -> bool:
    return bool(REVIEWED_HASHES) and all(
        isinstance(v, str) and len(v) == 64 for v in REVIEWED_HASHES.values()
    )


def verify_reviewed_hashes(
    *,
    workspace: Path,
    protocol_path: Path,
    split_path: Path,
) -> dict[str, str]:
    """Require exact R8-reviewed hashes before any research fit."""
    if not reviewed_hashes_complete():
        raise S10ExecuteRefusal(
            "REVIEWED_HASHES incomplete; R8 independent review PASS required "
            "before scientific fits"
        )
    paths = {
        "S10_PROTOCOL.json": Path(protocol_path),
        "S10_SPLIT_MANIFEST.json": Path(split_path),
        "src/p22/eval/s10_analytic.py": Path(workspace) / "src/p22/eval/s10_analytic.py",
        "src/p22/eval/s10_execute.py": Path(workspace) / "src/p22/eval/s10_execute.py",
    }
    live: dict[str, str] = {}
    for key, path in paths.items():
        if not path.is_file():
            raise S10ExecuteRefusal(f"missing reviewed artifact {key}: {path}")
        digest = sha256_file(path)
        live[key] = digest
        refuse_mismatched_protocol_hash(REVIEWED_HASHES[key], digest, label=key)
    return live


def prepare_raw_root(raw_root: Path | str) -> Path:
    """Create authorized S10 raw root; refuse S7/S8/S9 and symlink write-through."""
    root = Path(raw_root)
    refuse_if_not_allowed_raw_root(root)
    if root.exists():
        if root.is_symlink():
            raise S10ExecuteRefusal(f"raw root must not be a symlink: {root}")
    else:
        root.mkdir(parents=True, exist_ok=False)
    (root / "checkpoints").mkdir(exist_ok=True)
    (root / "donor_predictions").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    return root


def execution_defaults() -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "parallel_dispatch": False,
        "thread_pool_executor": False,
        "planned_fits": TOTAL_FITS,
        "scientific_cap": SCIENTIFIC_ATTEMPT_CAP,
        "fitting_hours_cap": SYNTHETIC_FITTING_HOURS_CAP,
        "artifact_gib_cap": SYNTHETIC_ARTIFACT_GIB_CAP,
        "allowed_raw_root": ALLOWED_RAW_ROOT,
        "decision_generator_seed": DECISION_GENERATOR_SEED,
        "decision_model_seed": DECISION_MODEL_SEED,
        "reserve_attempts_before_dispatch": True,
        "reviewed_hashes_complete": reviewed_hashes_complete(),
        "marginal_ba_max": MARGINAL_BA_MAX,
        "checkpoint_models": sorted(CHECKPOINT_MODELS),
        "note": (
            "Serial neural worker default. Scientific fits call "
            "refuse_unreviewed_scientific_fits until R8 fills REVIEWED_HASHES."
        ),
    }


def preflight_no_fit(
    *,
    workspace: Path,
    protocol_path: Path,
    split_path: Path,
    raw_root: Path | str,
) -> dict[str, Any]:
    """Hash/oracle/job/raw-root checks without scientific fits."""
    refuse_if_not_allowed_raw_root(raw_root)
    labels = assign_donor_labels(DECISION_GENERATOR_SEED)
    oracle = verify_oracle_invariants(labels)
    if oracle["oracle_gate"] != "PASS":
        raise S10ExecuteRefusal(f"oracle gate FAIL: {oracle}")
    splits = allocate_s10_folds(labels)
    frozen_split = json.loads(Path(split_path).read_text(encoding="utf-8"))
    if frozen_split["donor_labels"] != splits["donor_labels"]:
        raise S10ExecuteRefusal("split manifest diverges from live allocator")
    jobs = enumerate_s10_jobs()
    if len(jobs) != TOTAL_FITS:
        raise S10ExecuteRefusal(f"job count {len(jobs)} != {TOTAL_FITS}")
    # Touch corrected generator once (not a fit).
    _rna, _atac, _donor, _lab, _cells = generate_corrected_arrays(
        labels, rho=0.0, generator_seed=DECISION_GENERATOR_SEED
    )
    del _rna, _atac, _donor, _lab, _cells
    proto = s10_protocol_from_frozen()
    return {
        "protocol_id": PROTOCOL_ID,
        "oracle_gate": oracle["oracle_gate"],
        "n_jobs": len(jobs),
        "raw_root": str(raw_root),
        "protocol_sha256": sha256_file(protocol_path),
        "split_sha256": sha256_file(split_path),
        "analytic_sha256": sha256_file(
            Path(workspace) / "src/p22/eval/s10_analytic.py"
        ),
        "execute_sha256": sha256_file(
            Path(workspace) / "src/p22/eval/s10_execute.py"
        ),
        "execution_defaults": execution_defaults(),
        "protocol_fingerprint": proto.fingerprint,
        "scientific_fits_authorized": False,
    }


def run_scientific_batch(**_kwargs: Any) -> Mapping[str, Any]:
    """Hard refuse until R8 review authorizes hashes."""
    refuse_unreviewed_scientific_fits()
    raise AssertionError("unreachable")  # pragma: no cover
