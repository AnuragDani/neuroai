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
from p22.eval.s7_ledger import (
    S7_N_FOLDS,
    S7_SCREEN_SEED,
    Provenance,
    check_param_match,
    count_parameters,
    sha256_file,
)
from p22.eval.s7_runner import S7_PROTOCOL
from p22.eval.s7_screen import fold_cell_ids

S7_PROTOCOL_ID = "S7_covariance_20260929"
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


def prepare_s7_folds(
    inputs: NNInputs,
    panels: Mapping[int, Sequence[str]],
    *,
    generator_seed: int = S7_SCREEN_SEED,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    n_folds: int = S7_N_FOLDS,
) -> dict[str, Any]:
    """Prepare five outer folds with S7 fake labels and cell-id mapping.

    Stratification uses ``prospective-s7:<generator_seed>`` fake labels (never
    real disease labels). ``FoldArrays`` has no cell_id field, so mapped IDs
    are returned separately for ``plant_covariance``.
    """
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

    fold_map = _outer_fold_map(table, protocol)
    folds_by_index: dict[int, FoldArrays] = {}
    positions_by_fold: dict[int, dict[str, np.ndarray]] = {}
    cell_ids_by_fold: dict[int, np.ndarray] = {}
    split_log: dict[str, Any] = {}

    for fold_idx in range(int(n_folds)):
        if fold_idx not in panels:
            raise KeyError(f"missing region panel for fold {fold_idx}")
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
        split_log[str(fold_idx)] = {
            "train_donors": sorted(set(donor[split["train"]].tolist())),
            "val_donors": sorted(set(donor[split["val"]].tolist())),
            "test_donors": sorted(set(donor[split["test"]].tolist())),
            "n_train_cells": int(split["train"].size),
            "n_val_cells": int(split["val"].size),
            "n_test_cells": int(split["test"].size),
            "fake_label_tag": tag,
        }

    return {
        "folds_by_index": folds_by_index,
        "positions_by_fold": positions_by_fold,
        "cell_ids_by_fold": cell_ids_by_fold,
        "generator_seed": int(generator_seed),
        "fake_label_tag": tag,
        "donor_inventory": inventory,
        "split_log": split_log,
    }


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
        split_log_dir: Path | str | None = None,
        initial: Mapping[int, Mapping[str, Any]] | None = None,
    ) -> None:
        self._inputs = inputs
        self._panels = panels
        self._protocol = protocol
        self._n_folds = int(n_folds)
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
