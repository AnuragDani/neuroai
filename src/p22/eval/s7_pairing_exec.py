"""S7 pairing-PC diagnostic executor (no new fits).

Reloads retained rho=1 screen CA checkpoints, verifies identity, runs the
frozen 32 within-donor ATAC shuffles, aggregates to donors across folds, and
feeds :func:`evaluate_pairing_pc`. Does not search seeds or retune. TC
checkpoints may be retained for provenance but Gate 0b scores CA only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from p22.data.group_splits import aggregate_donor_probabilities
from p22.data.nn_inputs import FoldArrays
from p22.eval.multiome_protocol import MultiomeProtocol
from p22.eval.planted_signal import plant_covariance, shuffle_atac_within_donor
from p22.eval.s7_ledger import (
    S7_N_FOLDS,
    S7_SCREEN_SEED,
    make_fit_id,
)
from p22.eval.s7_pairing import (
    PC_INCOMPLETE,
    S7_PAIRING_SEEDS,
    evaluate_pairing_pc,
)
from p22.eval.s7_runner import S7_PROTOCOL, reload_checkpoint_predictions
from p22.models.fusion import VIEW_A, VIEW_B

S7_PC_MODEL = "cross_attention"
S7_PC_RHO = 1.0
S7_PC_STAGE = "screen"

ScoreFn = Callable[
    [Path | str, Mapping[str, np.ndarray], np.ndarray, MultiomeProtocol],
    np.ndarray,
]


def expected_ca_rho1_screen_jobs(
    *,
    n_folds: int = S7_N_FOLDS,
    generator_seed: int = S7_SCREEN_SEED,
) -> list[dict[str, Any]]:
    """Predeclared CA rho=1 screen jobs that must retain checkpoints for PC."""
    jobs: list[dict[str, Any]] = []
    for fold in range(int(n_folds)):
        fit_id = make_fit_id(
            S7_PC_STAGE, S7_PC_RHO, generator_seed, fold, S7_PC_MODEL
        )
        jobs.append(
            {
                "fit_id": fit_id,
                "stage": S7_PC_STAGE,
                "rho": float(S7_PC_RHO),
                "generator_seed": int(generator_seed),
                "fold": int(fold),
                "model": S7_PC_MODEL,
            }
        )
    return jobs


def select_pc_checkpoint_records(
    records: Sequence[Mapping[str, Any]],
    *,
    n_folds: int = S7_N_FOLDS,
    generator_seed: int = S7_SCREEN_SEED,
) -> dict[str, Any]:
    """Pick CA rho=1 screen rows that have a checkpoint_path; report gaps."""
    expected = {
        job["fit_id"]: job
        for job in expected_ca_rho1_screen_jobs(
            n_folds=n_folds, generator_seed=generator_seed
        )
    }
    by_id = {str(row.get("fit_id")): dict(row) for row in records}
    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    for fit_id in expected:
        row = by_id.get(fit_id)
        if row is None:
            missing.append(fit_id)
            continue
        path = row.get("checkpoint_path")
        if not path:
            missing.append(fit_id)
            continue
        selected.append(row)
    return {
        "records": selected,
        "expected": len(expected),
        "present": len(selected),
        "missing": missing,
        "complete": not missing,
    }


def cell_probs_to_donor(
    cell_probabilities: Sequence[float] | np.ndarray,
    donors: Sequence[Any] | np.ndarray,
    labels: Sequence[float] | np.ndarray,
) -> dict[str, Any]:
    """Mean cell probability per donor with the (constant) donor fake label."""
    probs = np.asarray(cell_probabilities, dtype=np.float64).reshape(-1)
    donor_arr = np.asarray([str(d) for d in np.asarray(donors)], dtype=object)
    label_arr = np.asarray(labels, dtype=np.float64).reshape(-1)
    if not (probs.size == donor_arr.size == label_arr.size):
        raise ValueError(
            f"length mismatch probs={probs.size} donors={donor_arr.size} "
            f"labels={label_arr.size}"
        )
    if probs.size == 0:
        return {
            "donor_ids": [],
            "y_true": [],
            "p": [],
        }
    frame = aggregate_donor_probabilities(probs, donor_arr)
    truth = pd.Series(label_arr, index=donor_arr).groupby(level=0).first()
    frame["label"] = frame.donor_id.map(truth).astype(float)
    return {
        "donor_ids": [str(d) for d in frame["donor_id"].tolist()],
        "y_true": frame["label"].to_numpy(dtype=np.float64).tolist(),
        "p": frame["probability"].to_numpy(dtype=np.float64).tolist(),
    }


def score_fold_pairing_pc(
    *,
    fold: FoldArrays,
    positions: Mapping[str, np.ndarray],
    checkpoint_path: Path | str,
    generator_seed: int,
    cell_ids: np.ndarray | None = None,
    feature_seed: int | None = None,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    pairing_seeds: tuple[int, ...] = S7_PAIRING_SEEDS,
    score_fn: ScoreFn | None = None,
) -> dict[str, Any]:
    """Plant rho=1, reload CA, score identity + within-donor ATAC shuffles.

    Returns donor-aligned original/reload/shuffled probabilities for one fold's
    held-out donors. Does not fit.
    """
    scorer = score_fn or reload_checkpoint_predictions
    planted, fake = plant_covariance(
        fold,
        rho=S7_PC_RHO,
        generator_seed=int(generator_seed),
        cell_ids=cell_ids,
        feature_seed=feature_seed,
    )
    test = np.asarray(positions["test"], dtype=np.int64)
    views = {VIEW_A: planted.rna, VIEW_B: planted.atac}
    p_cell_orig = np.asarray(
        scorer(checkpoint_path, views, test, protocol), dtype=np.float64
    ).reshape(-1)
    p_cell_reload = np.asarray(
        scorer(checkpoint_path, views, test, protocol), dtype=np.float64
    ).reshape(-1)
    if p_cell_orig.shape != test.shape or p_cell_reload.shape != test.shape:
        raise ValueError(
            f"scorer returned shape orig={p_cell_orig.shape} "
            f"reload={p_cell_reload.shape}; expected {test.shape}"
        )

    donors_test = planted.donor[test]
    labels_test = fake[test]
    orig = cell_probs_to_donor(p_cell_orig, donors_test, labels_test)
    reload = cell_probs_to_donor(p_cell_reload, donors_test, labels_test)

    shuffled_by_seed: dict[int, list[float]] = {}
    for seed in pairing_seeds:
        shuffled = shuffle_atac_within_donor(planted, int(seed))
        views_s = {VIEW_A: planted.rna, VIEW_B: shuffled.atac}
        p_cell_s = np.asarray(
            scorer(checkpoint_path, views_s, test, protocol), dtype=np.float64
        ).reshape(-1)
        if p_cell_s.shape != test.shape:
            raise ValueError(
                f"shuffle seed {seed} scorer shape {p_cell_s.shape} != {test.shape}"
            )
        donor_s = cell_probs_to_donor(p_cell_s, donors_test, labels_test)
        # Align shuffle probs to original donor order.
        by_donor = {
            d: float(p)
            for d, p in zip(donor_s["donor_ids"], donor_s["p"], strict=True)
        }
        shuffled_by_seed[int(seed)] = [by_donor[d] for d in orig["donor_ids"]]

    return {
        "n_test_cells": int(test.size),
        "n_test_donors": len(orig["donor_ids"]),
        "donor_ids": orig["donor_ids"],
        "y_true": orig["y_true"],
        "p_original": orig["p"],
        "p_reload": reload["p"],
        "p_shuffled_by_seed": shuffled_by_seed,
        "generator_seed": int(generator_seed),
    }


def run_pairing_pc_diagnostic(
    *,
    folds_by_index: Mapping[int, FoldArrays],
    positions_by_fold: Mapping[int, Mapping[str, np.ndarray]],
    ledger_records: Sequence[Mapping[str, Any]],
    cell_ids_by_fold: Mapping[int, np.ndarray] | None = None,
    feature_seed: int | None = None,
    protocol: MultiomeProtocol = S7_PROTOCOL,
    pairing_seeds: tuple[int, ...] = S7_PAIRING_SEEDS,
    n_folds: int = S7_N_FOLDS,
    generator_seed: int = S7_SCREEN_SEED,
    score_fn: ScoreFn | None = None,
) -> dict[str, Any]:
    """Run Gate 0b on all retained CA rho=1 screen checkpoints.

    Missing checkpoints or folds map to ``PC_INCOMPLETE`` without inventing
    predictions. No confirmation fits are started here.
    """
    selection = select_pc_checkpoint_records(
        ledger_records, n_folds=n_folds, generator_seed=generator_seed
    )
    if not selection["complete"]:
        return {
            "pc_label": PC_INCOMPLETE,
            "eligible_for_confirmation": False,
            "selection": selection,
            "fold_results": [],
            "evaluate": evaluate_pairing_pc(
                donor_ids=[],
                y_true=[],
                p_original=[],
                p_shuffled_by_seed={},
                p_reload=[],
                required_seeds=pairing_seeds,
            ),
            "reason": f"missing CA rho=1 screen checkpoints: {selection['missing']}",
        }

    donor_ids: list[str] = []
    y_true: list[float] = []
    p_original: list[float] = []
    p_reload: list[float] = []
    p_shuffled_by_seed: dict[int, list[float]] = {
        int(seed): [] for seed in pairing_seeds
    }
    fold_results: list[dict[str, Any]] = []

    for row in selection["records"]:
        fold_idx = int(row["fold"])
        if fold_idx not in folds_by_index:
            raise KeyError(f"missing fold arrays for fold {fold_idx}")
        if fold_idx not in positions_by_fold:
            raise KeyError(f"missing positions for fold {fold_idx}")
        cell_ids = None
        if cell_ids_by_fold is not None:
            cell_ids = cell_ids_by_fold.get(fold_idx)
        scored = score_fold_pairing_pc(
            fold=folds_by_index[fold_idx],
            positions=positions_by_fold[fold_idx],
            checkpoint_path=str(row["checkpoint_path"]),
            generator_seed=int(row.get("generator_seed", generator_seed)),
            cell_ids=cell_ids,
            feature_seed=feature_seed,
            protocol=protocol,
            pairing_seeds=pairing_seeds,
            score_fn=score_fn,
        )
        fold_results.append(
            {
                "fit_id": row["fit_id"],
                "fold": fold_idx,
                "checkpoint_path": str(row["checkpoint_path"]),
                "n_test_donors": scored["n_test_donors"],
                "n_test_cells": scored["n_test_cells"],
            }
        )
        donor_ids.extend(scored["donor_ids"])
        y_true.extend(scored["y_true"])
        p_original.extend(scored["p_original"])
        p_reload.extend(scored["p_reload"])
        for seed in pairing_seeds:
            p_shuffled_by_seed[int(seed)].extend(scored["p_shuffled_by_seed"][int(seed)])

    evaluated = evaluate_pairing_pc(
        donor_ids=donor_ids,
        y_true=y_true,
        p_original=p_original,
        p_shuffled_by_seed=p_shuffled_by_seed,
        p_reload=p_reload,
        required_seeds=pairing_seeds,
    )
    return {
        "pc_label": evaluated["pc_label"],
        "eligible_for_confirmation": evaluated["eligible_for_confirmation"],
        "selection": selection,
        "fold_results": fold_results,
        "n_donors": len(donor_ids),
        "evaluate": evaluated,
        "reason": None,
    }
