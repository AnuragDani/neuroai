"""S7 preflight and fold setup for the bounded prospective synthetic control.

Builds provenance hashes, prepares five donor folds with cell-id mapping under
the frozen screen generator tag, and gates CA/TC parameter match before fits.
Includes the S7-v2-only SHA256 donor quota splitter (v1 StratifiedGroupKFold
path unchanged). Does not search scenarios, seeds or hyperparameters. No
real-disease-label fits.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from p22.data.group_splits import (
    iter_repeated_stratified_group_folds,
    validate_group_folds,
)
from p22.data.nn_inputs import (
    LABEL_DISEASE,
    NNInputs,
    FoldArrays,
    load_nn_inputs,
    prepare_nn_fold,
    region_indices,
)
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.multiome_runner import paired_model
from p22.eval.planted_signal import fake_donor_labels, s7_label_tag
from p22.eval.s7_confirmation import S7_CONFIRM_SEEDS
from p22.eval.s7_ledger import (
    S7_N_FOLDS,
    S7_SCREEN_SEED,
    Provenance,
    check_param_match,
    count_parameters,
    sha256_bytes,
    sha256_file,
)
from p22.eval.s7_runner import S7_PROTOCOL
from p22.eval.s7_screen import fold_cell_ids

S7_PROTOCOL_ID = "S7_covariance_20260929"
INVALID_PREFLIGHT = "INVALID_PREFLIGHT"
# Screen seed 1001 plus confirmation seeds 2001–2010 (11 declared packs).
S7_V2_DECLARED_SEEDS: tuple[int, ...] = (S7_SCREEN_SEED, *S7_CONFIRM_SEEDS)
S7_V2_N_DECLARED_SEEDS = len(S7_V2_DECLARED_SEEDS)
S7_V2_N_TRIPLETS = S7_V2_N_DECLARED_SEEDS * S7_N_FOLDS
assert S7_V2_N_DECLARED_SEEDS == 11
assert S7_V2_N_TRIPLETS == 55
S7_SPEC_REL = Path("tasks/nn/finish_20260928/BENCHMARK_SPEC.json")
S7_CONFIG_REL = Path("configs/nn_inputs_2026-09-23.json")
S7_RESULT_REL = Path("docs/nn_v2/s7")
S7_WORKTREE_REPORTS_REL = Path("reports/generated/nn_s7_covariance_20260929")
S7_DURABLE_ROOT = Path(
    "/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929"
)
S7_CAP = 256
S7_N_RNA_VIEW = 2000
S7_N_ATAC_VIEW = 256

# S7-v2 deterministic donor quota splitter (never StratifiedGroupKFold).
S7_V2_SPLIT_PREFIX = "s7-split-v2"
S7_V2_CLASS0_OUTER_QUOTAS: tuple[int, ...] = (4, 3, 3, 3, 3)
S7_V2_CLASS1_OUTER_QUOTAS: tuple[int, ...] = (2, 3, 3, 3, 3)
S7_V2_INNER_VAL_PER_CLASS = 4
S7_V2_EXPECTED_N_CLASS0 = 16
S7_V2_EXPECTED_N_CLASS1 = 14
S7_V2_EXPECTED_N_DONORS = (
    S7_V2_EXPECTED_N_CLASS0 + S7_V2_EXPECTED_N_CLASS1
)

# Fitting sources whose hash change after outcomes invalidates the run.
S7_FITTING_SOURCE_RELS: tuple[Path, ...] = (
    Path("src/p22/eval/planted_signal.py"),
    Path("src/p22/eval/s7_ledger.py"),
    Path("src/p22/eval/s7_runner.py"),
    Path("src/p22/eval/s7_screen.py"),
    Path("src/p22/eval/s7_pairing.py"),
    Path("src/p22/eval/s7_pairing_exec.py"),
    Path("src/p22/eval/s7_confirmation.py"),
    Path("src/p22/eval/s7_confirm_exec.py"),
    Path("src/p22/eval/s7_handoff.py"),
    Path("src/p22/eval/s7_pipeline.py"),
    Path("src/p22/eval/s7_setup.py"),
    Path("src/p22/eval/multiome_runner.py"),
    Path("src/p22/training/loop.py"),
)


def s7_v2_split_digest(
    *,
    split_seed: int,
    generator_seed: int,
    stage: str,
    label: int,
    donor_id: str,
) -> str:
    """SHA256 digest for one donor under the frozen S7-v2 ranking string."""
    payload = "\n".join(
        [
            S7_V2_SPLIT_PREFIX,
            str(int(split_seed)),
            str(int(generator_seed)),
            str(stage),
            str(int(label)),
            str(donor_id),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def s7_v2_rank_donors(
    donor_ids: Sequence[str],
    *,
    split_seed: int,
    generator_seed: int,
    stage: str,
    label: int,
) -> list[str]:
    """Rank donors by (digest, donor_id); deterministic and order-invariant."""
    unique = sorted({str(d) for d in donor_ids})
    return sorted(
        unique,
        key=lambda donor: (
            s7_v2_split_digest(
                split_seed=split_seed,
                generator_seed=generator_seed,
                stage=stage,
                label=label,
                donor_id=donor,
            ),
            donor,
        ),
    )


def collect_s7_v2_donor_labels(
    donor_ids: Sequence[Any],
    labels: Sequence[Any],
) -> dict[str, int]:
    """Map each donor to its fake label; refuse mixed-label or empty input."""
    donors = [str(d) for d in donor_ids]
    labs = [int(x) for x in labels]
    if len(donors) != len(labs):
        raise ValueError(
            f"donor_ids length {len(donors)} != labels length {len(labs)}"
        )
    if not donors:
        raise ValueError("S7-v2 split requires at least one donor row")
    by_donor: dict[str, int] = {}
    for donor, label in zip(donors, labs, strict=True):
        if label not in (0, 1):
            raise ValueError(f"S7-v2 fake label must be 0 or 1; got {label}")
        prior = by_donor.get(donor)
        if prior is None:
            by_donor[donor] = label
        elif prior != label:
            raise ValueError(
                f"S7-v2 mixed-label donor refused: {donor} has {prior} and {label}"
            )
    return by_donor


def _assert_s7_v2_class_balance(donor_labels: Mapping[str, int]) -> dict[int, int]:
    counts = {0: 0, 1: 0}
    for label in donor_labels.values():
        if label not in counts:
            raise ValueError(f"S7-v2 unexpected donor label {label}")
        counts[int(label)] += 1
    if (
        counts[0] != S7_V2_EXPECTED_N_CLASS0
        or counts[1] != S7_V2_EXPECTED_N_CLASS1
    ):
        raise ValueError(
            "S7-v2 requires exactly "
            f"{S7_V2_EXPECTED_N_CLASS0}/{S7_V2_EXPECTED_N_CLASS1} "
            f"class-0/1 donors; found {counts[0]}/{counts[1]}"
        )
    if len(donor_labels) != S7_V2_EXPECTED_N_DONORS:
        raise ValueError(
            f"S7-v2 requires {S7_V2_EXPECTED_N_DONORS} unique donors; "
            f"found {len(donor_labels)}"
        )
    return counts


def _class_counts(donors: Sequence[str], donor_labels: Mapping[str, int]) -> dict[str, int]:
    counts = {"0": 0, "1": 0}
    for donor in donors:
        counts[str(int(donor_labels[donor]))] += 1
    return counts


def allocate_s7_v2_donor_folds(
    donor_ids: Sequence[Any],
    labels: Sequence[Any],
    *,
    split_seed: int = 0,
    generator_seed: int,
    n_folds: int = S7_N_FOLDS,
) -> dict[str, Any]:
    """Allocate S7-v2 outer test and inner train/val donor partitions.

    Uses frozen class-quota SHA256 ranking only. Does not consult features,
    predictions, or metrics. Leaves the v1 StratifiedGroupKFold path untouched.
    """
    if int(n_folds) != S7_N_FOLDS:
        raise ValueError(f"S7-v2 requires n_folds={S7_N_FOLDS}; got {n_folds}")
    if len(S7_V2_CLASS0_OUTER_QUOTAS) != S7_N_FOLDS:
        raise ValueError("class-0 outer quotas must cover five folds")
    if len(S7_V2_CLASS1_OUTER_QUOTAS) != S7_N_FOLDS:
        raise ValueError("class-1 outer quotas must cover five folds")
    if sum(S7_V2_CLASS0_OUTER_QUOTAS) != S7_V2_EXPECTED_N_CLASS0:
        raise ValueError("class-0 outer quotas must sum to 16")
    if sum(S7_V2_CLASS1_OUTER_QUOTAS) != S7_V2_EXPECTED_N_CLASS1:
        raise ValueError("class-1 outer quotas must sum to 14")

    donor_labels = collect_s7_v2_donor_labels(donor_ids, labels)
    class_balance = _assert_s7_v2_class_balance(donor_labels)

    ranked0 = s7_v2_rank_donors(
        [d for d, lab in donor_labels.items() if lab == 0],
        split_seed=split_seed,
        generator_seed=generator_seed,
        stage="outer",
        label=0,
    )
    ranked1 = s7_v2_rank_donors(
        [d for d, lab in donor_labels.items() if lab == 1],
        split_seed=split_seed,
        generator_seed=generator_seed,
        stage="outer",
        label=1,
    )

    folds: dict[str, Any] = {}
    seen_test: list[str] = []
    cursor0 = 0
    cursor1 = 0
    for fold_idx in range(S7_N_FOLDS):
        n0 = S7_V2_CLASS0_OUTER_QUOTAS[fold_idx]
        n1 = S7_V2_CLASS1_OUTER_QUOTAS[fold_idx]
        test0 = ranked0[cursor0 : cursor0 + n0]
        test1 = ranked1[cursor1 : cursor1 + n1]
        cursor0 += n0
        cursor1 += n1
        test_donors = sorted(test0 + test1)
        if len(test_donors) != 6:
            raise ValueError(
                f"fold {fold_idx} expected 6 test donors; got {len(test_donors)}"
            )
        if len(set(test_donors)) != len(test_donors):
            raise ValueError(f"fold {fold_idx} duplicate test donors: {test_donors}")
        overlap = set(test_donors) & set(seen_test)
        if overlap:
            raise ValueError(
                f"S7-v2 donor overlap across outer tests refused: {sorted(overlap)}"
            )
        seen_test.extend(test_donors)

        remaining = sorted(set(donor_labels) - set(test_donors))
        if len(remaining) != 24:
            raise ValueError(
                f"fold {fold_idx} expected 24 remaining donors; got {len(remaining)}"
            )
        rem0 = [d for d in remaining if donor_labels[d] == 0]
        rem1 = [d for d in remaining if donor_labels[d] == 1]
        inner_stage = f"inner:{fold_idx}"
        ranked_rem0 = s7_v2_rank_donors(
            rem0,
            split_seed=split_seed,
            generator_seed=generator_seed,
            stage=inner_stage,
            label=0,
        )
        ranked_rem1 = s7_v2_rank_donors(
            rem1,
            split_seed=split_seed,
            generator_seed=generator_seed,
            stage=inner_stage,
            label=1,
        )
        if (
            len(ranked_rem0) < S7_V2_INNER_VAL_PER_CLASS
            or len(ranked_rem1) < S7_V2_INNER_VAL_PER_CLASS
        ):
            raise ValueError(
                f"fold {fold_idx} lacks four donors/class for inner validation"
            )
        val_donors = sorted(
            ranked_rem0[:S7_V2_INNER_VAL_PER_CLASS]
            + ranked_rem1[:S7_V2_INNER_VAL_PER_CLASS]
        )
        train_donors = sorted(
            ranked_rem0[S7_V2_INNER_VAL_PER_CLASS:]
            + ranked_rem1[S7_V2_INNER_VAL_PER_CLASS:]
        )
        if len(val_donors) != 8 or len(train_donors) != 16:
            raise ValueError(
                f"fold {fold_idx} expected train/val 16/8; "
                f"got {len(train_donors)}/{len(val_donors)}"
            )
        parts = (set(train_donors), set(val_donors), set(test_donors))
        if len(parts[0] | parts[1] | parts[2]) != S7_V2_EXPECTED_N_DONORS:
            raise ValueError(f"fold {fold_idx} partitions miss donors")
        if parts[0] & parts[1] or parts[0] & parts[2] or parts[1] & parts[2]:
            raise ValueError(f"fold {fold_idx} overlapping train/val/test donors")
        for part_name, part in (
            ("train", train_donors),
            ("val", val_donors),
            ("test", test_donors),
        ):
            counts = _class_counts(part, donor_labels)
            if counts["0"] < 1 or counts["1"] < 1:
                raise ValueError(
                    f"fold {fold_idx} {part_name} lacks both fake classes: {counts}"
                )

        folds[str(fold_idx)] = {
            "train_donors": train_donors,
            "val_donors": val_donors,
            "test_donors": test_donors,
            "train_class_counts": _class_counts(train_donors, donor_labels),
            "val_class_counts": _class_counts(val_donors, donor_labels),
            "test_class_counts": _class_counts(test_donors, donor_labels),
            "outer_quotas": {
                "class0": n0,
                "class1": n1,
            },
        }

    if cursor0 != len(ranked0) or cursor1 != len(ranked1):
        raise ValueError("outer quota cursors did not consume all ranked donors")
    if len(seen_test) != S7_V2_EXPECTED_N_DONORS or len(set(seen_test)) != S7_V2_EXPECTED_N_DONORS:
        raise ValueError(
            "S7-v2 outer tests must cover each donor exactly once; "
            f"covered {len(set(seen_test))} unique / {len(seen_test)} listed"
        )

    return {
        "split_seed": int(split_seed),
        "generator_seed": int(generator_seed),
        "n_folds": S7_N_FOLDS,
        "donor_labels": dict(sorted(donor_labels.items())),
        "class_balance": {"0": class_balance[0], "1": class_balance[1]},
        "outer_class0_quotas": list(S7_V2_CLASS0_OUTER_QUOTAS),
        "outer_class1_quotas": list(S7_V2_CLASS1_OUTER_QUOTAS),
        "folds": folds,
        "test_donors_once": sorted(seen_test),
    }


class S7V2PreflightError(ValueError):
    """Hard stop before any S7-v2 fit; scientific label INVALID_PREFLIGHT."""

    def __init__(self, message: str) -> None:
        if not str(message).startswith(INVALID_PREFLIGHT):
            message = f"{INVALID_PREFLIGHT}: {message}"
        super().__init__(message)
        self.label = INVALID_PREFLIGHT


def _rows_for_donors(metadata: pd.DataFrame, donors: Sequence[str]) -> np.ndarray:
    wanted = {str(d) for d in donors}
    donor_col = metadata["donor_id"].astype(str).to_numpy()
    return np.flatnonzero(np.isin(donor_col, list(wanted))).astype(np.int64)


def s7_v2_cell_id_hash(cell_ids: Sequence[Any]) -> str:
    """Stable SHA256 over UTF-8 cell IDs (order-preserving)."""
    payload = "\n".join(str(x) for x in cell_ids).encode("utf-8")
    return sha256_bytes(payload)


def assert_s7_v2_fake_label_agreement(
    full_cohort_labels: Mapping[str, int],
    planted_labels: Mapping[str, int],
) -> None:
    """Refuse when planted donor labels disagree with the full-cohort fake map."""
    full = {str(k): int(v) for k, v in full_cohort_labels.items()}
    planted = {str(k): int(v) for k, v in planted_labels.items()}
    if set(full) != set(planted):
        missing = sorted(set(full) ^ set(planted))
        raise S7V2PreflightError(
            f"planted/full-cohort donor sets differ; sample={missing[:5]}"
        )
    mismatches = sorted(
        donor for donor, label in full.items() if int(planted[donor]) != int(label)
    )
    if mismatches:
        raise S7V2PreflightError(
            f"planted/full-cohort fake labels disagree for donors {mismatches[:5]}"
        )


def validate_s7_v2_allocation(alloc: Mapping[str, Any]) -> dict[str, Any]:
    """Re-check one seed allocation for 16/8/6, both classes, once-only coverage.

    Raises ``S7V2PreflightError`` on any class/support/overlap failure. Returns a
    compact recount suitable for the split manifest.
    """
    donor_labels = {
        str(k): int(v) for k, v in dict(alloc["donor_labels"]).items()
    }
    _assert_s7_v2_class_balance(donor_labels)
    folds = dict(alloc["folds"])
    if len(folds) != S7_N_FOLDS:
        raise S7V2PreflightError(
            f"expected {S7_N_FOLDS} folds; found {len(folds)}"
        )
    seen_test: list[str] = []
    fold_records: dict[str, Any] = {}
    for fold_idx in range(S7_N_FOLDS):
        key = str(fold_idx)
        if key not in folds:
            raise S7V2PreflightError(f"missing fold {fold_idx}")
        fold = folds[key]
        train = [str(d) for d in fold["train_donors"]]
        val = [str(d) for d in fold["val_donors"]]
        test = [str(d) for d in fold["test_donors"]]
        if len(train) != 16 or len(val) != 8 or len(test) != 6:
            raise S7V2PreflightError(
                f"fold {fold_idx} donor counts train/val/test="
                f"{len(train)}/{len(val)}/{len(test)}; expected 16/8/6"
            )
        if len(set(train)) != 16 or len(set(val)) != 8 or len(set(test)) != 6:
            raise S7V2PreflightError(f"fold {fold_idx} duplicate donors inside a partition")
        parts = (set(train), set(val), set(test))
        if parts[0] & parts[1] or parts[0] & parts[2] or parts[1] & parts[2]:
            raise S7V2PreflightError(f"fold {fold_idx} overlapping train/val/test")
        if parts[0] | parts[1] | parts[2] != set(donor_labels):
            raise S7V2PreflightError(f"fold {fold_idx} partitions miss donors")
        overlap = set(test) & set(seen_test)
        if overlap:
            raise S7V2PreflightError(
                f"outer test donor overlap refused: {sorted(overlap)}"
            )
        seen_test.extend(test)
        counts = {
            "train": _class_counts(train, donor_labels),
            "val": _class_counts(val, donor_labels),
            "test": _class_counts(test, donor_labels),
        }
        for part_name, part_counts in counts.items():
            if part_counts["0"] < 1 or part_counts["1"] < 1:
                raise S7V2PreflightError(
                    f"fold {fold_idx} {part_name} single-class refused: {part_counts}"
                )
        fold_records[key] = {
            "train_donors": sorted(train),
            "val_donors": sorted(val),
            "test_donors": sorted(test),
            "train_class_counts": counts["train"],
            "val_class_counts": counts["val"],
            "test_class_counts": counts["test"],
            "n_train_donors": 16,
            "n_val_donors": 8,
            "n_test_donors": 6,
        }
    if len(seen_test) != S7_V2_EXPECTED_N_DONORS or len(set(seen_test)) != S7_V2_EXPECTED_N_DONORS:
        raise S7V2PreflightError(
            "outer tests must cover each donor exactly once; "
            f"covered {len(set(seen_test))} unique / {len(seen_test)} listed"
        )
    return {
        "generator_seed": int(alloc["generator_seed"]),
        "split_seed": int(alloc["split_seed"]),
        "class_balance": {
            "0": int(alloc["class_balance"]["0"]),
            "1": int(alloc["class_balance"]["1"]),
        },
        "donor_labels": dict(sorted(donor_labels.items())),
        "folds": fold_records,
        "test_donors_once": sorted(seen_test),
        "n_test_donors_unique": len(set(seen_test)),
    }


def recount_s7_v2_split_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Independent recount of a saved all-seed split manifest (no allocation)."""
    seeds = dict(manifest.get("seeds") or {})
    n_seeds = len(seeds)
    n_triplets = 0
    per_seed: dict[str, Any] = {}
    problems: list[str] = []
    for seed_key, entry in sorted(seeds.items(), key=lambda kv: int(kv[0])):
        try:
            validated = validate_s7_v2_allocation(
                {
                    "generator_seed": entry["generator_seed"],
                    "split_seed": entry["split_seed"],
                    "donor_labels": entry["donor_labels"],
                    "class_balance": entry["class_balance"],
                    "folds": entry["folds"],
                }
            )
        except S7V2PreflightError as exc:
            problems.append(str(exc))
            continue
        n_triplets += S7_N_FOLDS
        per_seed[seed_key] = {
            "n_folds": S7_N_FOLDS,
            "n_test_donors_unique": validated["n_test_donors_unique"],
            "class_balance": validated["class_balance"],
            "fold_donor_counts": {
                fold_key: {
                    "train": fold["n_train_donors"],
                    "val": fold["n_val_donors"],
                    "test": fold["n_test_donors"],
                    "train_class_counts": fold["train_class_counts"],
                    "val_class_counts": fold["val_class_counts"],
                    "test_class_counts": fold["test_class_counts"],
                }
                for fold_key, fold in validated["folds"].items()
            },
        }
    return {
        "n_seeds": n_seeds,
        "n_triplets": n_triplets,
        "expected_n_seeds": S7_V2_N_DECLARED_SEEDS,
        "expected_n_triplets": S7_V2_N_TRIPLETS,
        "ok": (
            n_seeds == S7_V2_N_DECLARED_SEEDS
            and n_triplets == S7_V2_N_TRIPLETS
            and not problems
            and bool(manifest.get("ok"))
        ),
        "problems": problems,
        "per_seed": per_seed,
    }


def build_s7_v2_all_seed_split_manifest(
    *,
    label_rows_by_seed: Mapping[int, tuple[Sequence[Any], Sequence[Any]]],
    split_seed: int = 0,
    seeds: Sequence[int] = S7_V2_DECLARED_SEEDS,
    planted_labels_by_seed: Mapping[int, Mapping[str, int]] | None = None,
    cell_id_hashes_by_seed: Mapping[int, Mapping[str, Mapping[str, str]]] | None = None,
) -> dict[str, Any]:
    """Build and validate the 11×5 no-fit split manifest before any fit.

    ``label_rows_by_seed`` maps generator seed → (donor_ids, fake_labels) cell
    or donor rows. One failing confirmation seed fails the entire batch.
    """
    declared = tuple(int(s) for s in seeds)
    if tuple(declared) != tuple(S7_V2_DECLARED_SEEDS):
        # Allow exact frozen set only; refuse silent seed substitution.
        if set(declared) != set(S7_V2_DECLARED_SEEDS) or len(declared) != S7_V2_N_DECLARED_SEEDS:
            raise S7V2PreflightError(
                f"declared seeds must be exactly {list(S7_V2_DECLARED_SEEDS)}; got {list(declared)}"
            )
    seed_entries: dict[str, Any] = {}
    for seed in S7_V2_DECLARED_SEEDS:
        if int(seed) not in label_rows_by_seed:
            raise S7V2PreflightError(f"missing label rows for generator_seed={seed}")
        donor_ids, labels = label_rows_by_seed[int(seed)]
        try:
            alloc = allocate_s7_v2_donor_folds(
                donor_ids,
                labels,
                split_seed=int(split_seed),
                generator_seed=int(seed),
            )
            validated = validate_s7_v2_allocation(alloc)
        except ValueError as exc:
            # allocate_s7_v2 raises ValueError; normalize to preflight label.
            raise S7V2PreflightError(
                f"generator_seed={seed} split invalid: {exc}"
            ) from exc
        if planted_labels_by_seed is not None:
            if int(seed) not in planted_labels_by_seed:
                raise S7V2PreflightError(
                    f"missing planted labels for generator_seed={seed}"
                )
            assert_s7_v2_fake_label_agreement(
                validated["donor_labels"],
                planted_labels_by_seed[int(seed)],
            )
        entry = dict(validated)
        entry["fake_label_tag"] = s7_label_tag(int(seed))
        if cell_id_hashes_by_seed is not None:
            if int(seed) not in cell_id_hashes_by_seed:
                raise S7V2PreflightError(
                    f"missing cell-id hashes for generator_seed={seed}"
                )
            entry["cell_id_hashes"] = {
                str(k): dict(v)
                for k, v in cell_id_hashes_by_seed[int(seed)].items()
            }
        seed_entries[str(int(seed))] = entry

    payload = {
        "ok": True,
        "label": "PREFLIGHT_PASS",
        "protocol": "S7_v2_split_manifest",
        "split_seed": int(split_seed),
        "declared_seeds": list(S7_V2_DECLARED_SEEDS),
        "n_seeds": S7_V2_N_DECLARED_SEEDS,
        "n_triplets": S7_V2_N_TRIPLETS,
        "seeds": seed_entries,
    }
    payload["split_manifest_sha256"] = sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    recount = recount_s7_v2_split_manifest(payload)
    if not recount["ok"]:
        raise S7V2PreflightError(
            f"independent recount failed: {recount.get('problems')}"
        )
    payload["recount"] = {
        "n_seeds": recount["n_seeds"],
        "n_triplets": recount["n_triplets"],
        "ok": True,
    }
    return payload


def require_s7_v2_preflight_pass(manifest: Mapping[str, Any] | None) -> None:
    """Hard gate: refuse fits/checkpoints/ledger rows without a PASS manifest."""
    if manifest is None or not bool(manifest.get("ok")):
        raise S7V2PreflightError(
            "fits refused until all-seed no-fit preflight PASS (55/55)"
        )
    if int(manifest.get("n_triplets", 0)) != S7_V2_N_TRIPLETS:
        raise S7V2PreflightError(
            f"manifest n_triplets={manifest.get('n_triplets')} != {S7_V2_N_TRIPLETS}"
        )


def guarded_s7_v2_call(
    manifest: Mapping[str, Any] | None,
    fn: Callable[..., Any],
    /,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Run ``fn`` only after all-seed preflight PASS; otherwise zero side effects."""
    require_s7_v2_preflight_pass(manifest)
    return fn(*args, **kwargs)


def resolve_repo_root(start: Path | str | None = None) -> Path:
    """Locate repository root containing the frozen S7 spec."""
    here = Path(start) if start is not None else Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / S7_SPEC_REL).is_file() and (candidate / S7_CONFIG_REL).is_file():
            return candidate
    raise FileNotFoundError("could not locate S7 repo root (missing spec/config)")


def resolve_s7_paths(repo_root: Path | str | None = None) -> dict[str, Path]:
    """Frozen worktree result + durable ledger/checkpoint locations."""
    root = resolve_repo_root(repo_root)
    durable = S7_DURABLE_ROOT
    worktree_reports = root / S7_WORKTREE_REPORTS_REL
    return {
        "repo_root": root,
        "spec": root / S7_SPEC_REL,
        "config": root / S7_CONFIG_REL,
        "result_dir": root / S7_RESULT_REL,
        "worktree_reports": worktree_reports,
        "durable_root": durable,
        "ledger_root": durable / "ledger",
        "checkpoint_dir": durable / "checkpoints",
        "stage_output_root": durable,
    }


def fold_positions(
    train_rows: np.ndarray, val_rows: np.ndarray, test_rows: np.ndarray
) -> dict[str, np.ndarray]:
    """Map split rows into ``prepare_nn_fold`` row order ``[train, val, test]``."""
    holdout = np.concatenate([val_rows, test_rows])
    train = np.arange(train_rows.size)
    val = train_rows.size + np.arange(val_rows.size)
    test = train_rows.size + val_rows.size + np.arange(test_rows.size)
    return {
        "train": train,
        "val": val,
        "test": test,
        "holdout_rows": holdout,
        "source_train": np.asarray(train_rows, dtype=np.int64),
        "source_val": np.asarray(val_rows, dtype=np.int64),
        "source_test": np.asarray(test_rows, dtype=np.int64),
    }


def _outer_fold_map(metadata: pd.DataFrame, protocol: MultiomeProtocol) -> dict[tuple[int, int], Any]:
    folds = list(
        iter_repeated_stratified_group_folds(
            metadata["donor_id"],
            metadata["label"],
            protocol.n_repeats,
            protocol.n_folds,
            protocol.split_seed,
        )
    )
    problems = validate_group_folds(folds)
    if problems:
        raise ValueError("; ".join(problems))
    return {(fold.repeat, fold.fold): fold for fold in folds}


def _split_indices(metadata: pd.DataFrame, outer: Any) -> dict[str, np.ndarray]:
    training = metadata.iloc[outer.train_index]
    inner = next(
        iter_repeated_stratified_group_folds(
            training["donor_id"],
            training["label"],
            n_repeats=1,
            n_folds=3,
            base_seed=outer.split_seed,
        )
    )
    return {
        "train": outer.train_index[inner.train_index],
        "val": outer.train_index[inner.test_index],
        "test": outer.test_index,
    }


def donor_inventory(metadata: pd.DataFrame) -> dict[str, Any]:
    """Record the 30 expected donor IDs and disease strata counts."""
    donors = metadata["donor_id"].astype(str)
    disease = metadata["disease"].astype(str) if "disease" in metadata.columns else None
    unique = sorted(set(donors.tolist()))
    inventory: dict[str, Any] = {
        "n_donors": len(unique),
        "donor_ids": unique,
        "n_donors_expected": 30,
        "donors_match_expected": len(unique) == 30,
    }
    if disease is not None:
        donor_disease = (
            pd.Series(disease.to_numpy(), index=donors.to_numpy())
            .groupby(level=0)
            .first()
        )
        inventory["n_disease"] = int((donor_disease == LABEL_DISEASE).sum())
        inventory["n_control"] = int(len(unique) - inventory["n_disease"])
    return inventory


def build_provenance(
    repo_root: Path | str | None = None,
    *,
    input_paths: Mapping[str, Path | str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Provenance:
    """Hash frozen spec, fitting sources and declared inputs for ledger freeze."""
    root = resolve_repo_root(repo_root)
    paths = resolve_s7_paths(root)
    source_sha256 = {
        path.name: sha256_file(root / path) for path in S7_FITTING_SOURCE_RELS
    }
    if input_paths is None:
        config = json.loads(paths["config"].read_text(encoding="utf-8"))["inputs"]
        input_paths = {
            "h5ad": config["h5ad"]["path"],
            "atac_tiebreak_counts": config["atac_tiebreak_counts"]["path"],
            "tracked_union_bed": config["tracked_union_bed"]["path"],
            "region_sets_sha256_json": config["region_sets_sha256_json"]["path"],
            "nn_inputs_config": paths["config"],
        }
    input_sha256 = {key: sha256_file(path) for key, path in sorted(input_paths.items())}
    return Provenance(
        protocol_id=S7_PROTOCOL_ID,
        spec_sha256=sha256_file(paths["spec"]),
        source_sha256=source_sha256,
        input_sha256=input_sha256,
        extra=None if extra is None else dict(extra),
    )


def preflight_param_match(
    protocol: MultiomeProtocol = S7_PROTOCOL,
    *,
    n_rna: int = S7_N_RNA_VIEW,
    n_atac: int = S7_N_ATAC_VIEW,
) -> dict[str, Any]:
    """CA/TC ≤10% relative param-match gate before any result fits."""
    widths = [int(n_rna), int(n_atac)]
    ca = paired_model("cross_attention", widths, protocol)
    tc = paired_model("token_concat", widths, protocol)
    return check_param_match(count_parameters(ca), count_parameters(tc))


def load_region_panels(config_path: Path | str) -> dict[int, list[str]]:
    """Load repeat-0 ATAC region panels keyed by outer fold index."""
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))["inputs"]
    region_sets = json.loads(
        Path(config["region_sets_sha256_json"]["path"]).read_text(encoding="utf-8")
    )
    panels = {
        int(entry["fold"]): list(entry["regions"])
        for entry in region_sets["per_fold"]
        if int(entry["repeat"]) == 0
    }
    if len(panels) < S7_N_FOLDS:
        raise ValueError(
            f"expected ≥{S7_N_FOLDS} repeat-0 region panels; found {len(panels)}"
        )
    return panels


def load_s7_inputs(
    *,
    repo_root: Path | str | None = None,
    cap: int = S7_CAP,
    protocol: MultiomeProtocol = S7_PROTOCOL,
) -> NNInputs:
    """Load NN inputs under frozen config paths and S7 cell cap."""
    paths = resolve_s7_paths(repo_root)
    config = json.loads(paths["config"].read_text(encoding="utf-8"))["inputs"]
    return load_nn_inputs(
        config["h5ad"]["path"],
        config["atac_tiebreak_counts"]["path"],
        cap=int(cap),
        seed=protocol.sampling_seed,
        union_bed=config["tracked_union_bed"]["path"],
    )


def s7_v2_fake_label_rows(
    inputs: NNInputs,
    generator_seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Return cell-aligned donors/fake labels plus pure donor→label map."""
    donor = inputs.metadata["donor_id"].astype(str).to_numpy()
    truth = (inputs.metadata["disease"].astype(str) == LABEL_DISEASE).to_numpy(
        dtype=np.int64
    )
    fake = fake_donor_labels(donor, truth, tag=s7_label_tag(int(generator_seed)))
    donor_labels = collect_s7_v2_donor_labels(donor.tolist(), fake.tolist())
    return donor, fake.astype(np.int64), donor_labels


def build_s7_v2_label_rows_by_seed(
    inputs: NNInputs,
    *,
    seeds: Sequence[int] = S7_V2_DECLARED_SEEDS,
) -> dict[int, tuple[Sequence[Any], Sequence[Any]]]:
    """Materialize fake-label rows for every declared S7-v2 generator seed."""
    out: dict[int, tuple[Sequence[Any], Sequence[Any]]] = {}
    for seed in seeds:
        donor, fake, _ = s7_v2_fake_label_rows(inputs, int(seed))
        out[int(seed)] = (donor.tolist(), fake.tolist())
    return out


def prepare_s7_folds(
    inputs: NNInputs,
    panels: Mapping[int, Sequence[str]],
    *,
    generator_seed: int = S7_SCREEN_SEED,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    n_folds: int = S7_N_FOLDS,
    split_method: str = "v1",
) -> dict[str, Any]:
    """Prepare five outer folds with S7 fake labels and cell-id mapping.

    Stratification uses ``prospective-s7:<generator_seed>`` fake labels (never
    real disease labels). ``split_method='v1'`` keeps StratifiedGroupKFold;
    ``split_method='v2'`` uses the S7-v2 SHA256 donor quota splitter.
    ``FoldArrays`` has no cell_id field, so mapped IDs are returned separately
    for ``plant_covariance``.
    """
    if split_method not in {"v1", "v2"}:
        raise ValueError(f"split_method must be 'v1' or 'v2'; got {split_method!r}")
    donor = inputs.metadata["donor_id"].astype(str).to_numpy()
    truth = (inputs.metadata["disease"].astype(str) == LABEL_DISEASE).to_numpy(
        dtype=np.int64
    )
    tag = s7_label_tag(int(generator_seed))
    fake = fake_donor_labels(donor, truth, tag=tag)
    table = pd.DataFrame(
        {
            "donor_id": donor,
            "label": fake,
            "disease": inputs.metadata["disease"].astype(str).to_numpy(),
        }
    )
    inventory = donor_inventory(table)
    if not inventory["donors_match_expected"]:
        raise ValueError(
            f"expected 30 donors; found {inventory['n_donors']}: "
            f"{inventory['donor_ids'][:5]}..."
        )

    v2_alloc: dict[str, Any] | None = None
    fold_map = None
    if split_method == "v2":
        v2_alloc = allocate_s7_v2_donor_folds(
            donor.tolist(),
            fake.tolist(),
            split_seed=int(protocol.split_seed),
            generator_seed=int(generator_seed),
            n_folds=int(n_folds),
        )
        validate_s7_v2_allocation(v2_alloc)
    else:
        fold_map = _outer_fold_map(table, protocol)

    folds_by_index: dict[int, FoldArrays] = {}
    positions_by_fold: dict[int, dict[str, np.ndarray]] = {}
    cell_ids_by_fold: dict[int, np.ndarray] = {}
    split_log: dict[str, Any] = {}

    for fold_idx in range(int(n_folds)):
        if fold_idx not in panels:
            raise KeyError(f"missing region panel for fold {fold_idx}")
        if split_method == "v2":
            assert v2_alloc is not None
            fold_alloc = v2_alloc["folds"][str(fold_idx)]
            split = {
                "train": _rows_for_donors(table, fold_alloc["train_donors"]),
                "val": _rows_for_donors(table, fold_alloc["val_donors"]),
                "test": _rows_for_donors(table, fold_alloc["test_donors"]),
            }
        else:
            assert fold_map is not None
            outer = fold_map[(0, fold_idx)]
            split = _split_indices(table, outer)
        positions = fold_positions(split["train"], split["val"], split["test"])
        region_rows = region_indices(inputs, panels[fold_idx])
        base = prepare_nn_fold(
            inputs, split["train"], positions["holdout_rows"], region_rows
        )
        if base.rna.shape[1] != S7_N_RNA_VIEW or base.atac.shape[1] != S7_N_ATAC_VIEW:
            raise ValueError(
                f"unexpected view widths fold={fold_idx}: "
                f"{base.rna.shape[1]}, {base.atac.shape[1]}"
            )
        cell_ids = fold_cell_ids(
            inputs.metadata.index,
            split["train"],
            split["val"],
            split["test"],
        )
        if cell_ids.shape[0] != base.donor.size:
            raise ValueError(
                f"cell_id length {cell_ids.shape[0]} != fold cells {base.donor.size}"
            )
        folds_by_index[fold_idx] = base
        positions_by_fold[fold_idx] = {
            "train": positions["train"],
            "val": positions["val"],
            "test": positions["test"],
        }
        cell_ids_by_fold[fold_idx] = cell_ids
        train_donors = sorted(set(donor[split["train"]].tolist()))
        val_donors = sorted(set(donor[split["val"]].tolist()))
        test_donors = sorted(set(donor[split["test"]].tolist()))
        fold_entry: dict[str, Any] = {
            "train_donors": train_donors,
            "val_donors": val_donors,
            "test_donors": test_donors,
            "n_train_cells": int(split["train"].size),
            "n_val_cells": int(split["val"].size),
            "n_test_cells": int(split["test"].size),
            "fake_label_tag": tag,
            "cell_id_hash": s7_v2_cell_id_hash(cell_ids.tolist()),
            "split_method": split_method,
        }
        if split_method == "v2":
            assert v2_alloc is not None
            fold_entry["train_class_counts"] = v2_alloc["folds"][str(fold_idx)][
                "train_class_counts"
            ]
            fold_entry["val_class_counts"] = v2_alloc["folds"][str(fold_idx)][
                "val_class_counts"
            ]
            fold_entry["test_class_counts"] = v2_alloc["folds"][str(fold_idx)][
                "test_class_counts"
            ]
        split_log[str(fold_idx)] = fold_entry

    result: dict[str, Any] = {
        "folds_by_index": folds_by_index,
        "positions_by_fold": positions_by_fold,
        "cell_ids_by_fold": cell_ids_by_fold,
        "generator_seed": int(generator_seed),
        "fake_label_tag": tag,
        "donor_inventory": inventory,
        "split_log": split_log,
        "split_method": split_method,
    }
    if split_method == "v2":
        assert v2_alloc is not None
        result["v2_allocation"] = v2_alloc
        result["donor_labels"] = v2_alloc["donor_labels"]
    return result


def write_preflight_record(path: Path | str, payload: Mapping[str, Any]) -> Path:
    """Persist preflight evidence (hashes, donors, param match, paths)."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_split_log(path: Path | str, pack: Mapping[str, Any]) -> Path:
    """Persist one generator-seed split log (donor sets + fake-label tag)."""
    payload = {
        "generator_seed": int(pack["generator_seed"]),
        "fake_label_tag": pack["fake_label_tag"],
        "donor_inventory": pack["donor_inventory"],
        "split_log": pack["split_log"],
    }
    return write_preflight_record(path, payload)


def run_s7_v2_all_seed_nofit_preflight(
    *,
    label_rows_by_seed: Mapping[int, tuple[Sequence[Any], Sequence[Any]]],
    split_seed: int = 0,
    planted_labels_by_seed: Mapping[int, Mapping[str, int]] | None = None,
    cell_id_hashes_by_seed: Mapping[int, Mapping[str, Mapping[str, str]]] | None = None,
    manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    """Validate all 11 declared seeds (55 triplets) with zero model fits.

    Writes the split manifest when ``manifest_path`` is set. Any invalid seed
    raises ``S7V2PreflightError`` and must block the entire batch.
    """
    manifest = build_s7_v2_all_seed_split_manifest(
        label_rows_by_seed=label_rows_by_seed,
        split_seed=int(split_seed),
        planted_labels_by_seed=planted_labels_by_seed,
        cell_id_hashes_by_seed=cell_id_hashes_by_seed,
    )
    require_s7_v2_preflight_pass(manifest)
    if manifest_path is not None:
        write_preflight_record(manifest_path, manifest)
    return manifest


class FoldPackCache:
    """Lazy per-seed fold packs for screen vs confirmation generator tags.

    Confirmation trials need a fresh ``prospective-s7:<seed>`` stratification
    (fixed ``split_seed``). Screen/smoke/PC reuse seed 1001. Caches packs so
    each seed is prepared at most once; never retunes splits from outcomes.
    """

    def __init__(
        self,
        inputs: NNInputs,
        panels: Mapping[int, Sequence[str]],
        *,
        protocol: MultiomeProtocol = S7_PROTOCOL,
        n_folds: int = S7_N_FOLDS,
        split_method: str = "v1",
        split_log_dir: Path | str | None = None,
        initial: Mapping[int, Mapping[str, Any]] | None = None,
    ) -> None:
        self._inputs = inputs
        self._panels = panels
        self._protocol = protocol
        self._n_folds = int(n_folds)
        self._split_method = str(split_method)
        self._split_log_dir = None if split_log_dir is None else Path(split_log_dir)
        self._packs: dict[int, dict[str, Any]] = {
            int(seed): dict(pack) for seed, pack in (initial or {}).items()
        }

    def get(self, generator_seed: int) -> dict[str, Any]:
        seed = int(generator_seed)
        if seed not in self._packs:
            pack = prepare_s7_folds(
                self._inputs,
                self._panels,
                generator_seed=seed,
                protocol=self._protocol,
                n_folds=self._n_folds,
                split_method=self._split_method,
            )
            self._packs[seed] = pack
            if self._split_log_dir is not None:
                self._split_log_dir.mkdir(parents=True, exist_ok=True)
                write_split_log(
                    self._split_log_dir / f"split_log_seed_{seed}.json",
                    pack,
                )
        return self._packs[seed]

    def resolver(self) -> Callable[[int], dict[str, Any]]:
        """Return a ``Callable[[int], dict]`` for the pipeline fit runner."""
        return self.get

    @property
    def prepared_seeds(self) -> tuple[int, ...]:
        return tuple(sorted(self._packs))

    @property
    def split_method(self) -> str:
        return self._split_method
