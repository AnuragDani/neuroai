"""M4 metric and leakage helpers for the masked ATAC computational pilot.

No model fitting. Provides:

- binary presence labels (count > 0)
- clipped cell log-loss and equal-donor-average of within-donor mean cell loss
- refusal of donor-average-probability / fake disease-class substitution
- visible-ATAC-only TF-IDF fit statistics that stay invariant under target
  column perturbation (target-inclusive panel depth is the leak path refused)
- forbidden-feature inventory and overwrite / feature-order hash guards

Existing disease trainers (``mil_loop._donor_label_map``) refuse mixed cell
labels per donor; this module records that an adapter is required rather than
reusing that assumption for accessibility targets.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

# Match s7_pairing.binary_log_loss clip for evaluator consistency.
PROB_CLIP = 1e-15

FORBIDDEN_FEATURE_FIELDS: tuple[str, ...] = (
    "disease",
    "donor_id",
    "group",
    "nCount_ATAC",
    "nFeature_ATAC",
    "nucleosome_signal",
    "TSS.enrichment",
    "target_count",
    "target_region_index",
    "target_chrom",
    "gene_activity_all_regions",
)

ADAPTER_REQUIREMENTS: dict[str, Any] = {
    "existing_mil_loop_assumption": (
        "p22.training.mil_loop._donor_label_map refuses any donor with mixed "
        "cell labels; disease bags assume one label per donor"
    ),
    "required_adapter": (
        "donor-average of within-donor mean cell-target binary log-loss "
        "(equal donor weighting); do not substitute donor-average probability "
        "or invent a fake donor disease class"
    ),
    "preserve_classification_api": True,
    "fake_disease_class_forbidden": True,
    "donor_average_probability_forbidden_as_primary": True,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_array(values: np.ndarray) -> str:
    arr = np.ascontiguousarray(values, dtype=np.float64)
    return sha256_bytes(arr.tobytes())


def sha256_lines(items: Sequence[str]) -> str:
    return sha256_bytes("\n".join(str(x) for x in items).encode())


def binary_presence_labels(counts: np.ndarray | Sequence[float]) -> np.ndarray:
    """Map exact-region fragment counts to binary presence (count > 0)."""
    arr = np.asarray(counts, dtype=np.float64).reshape(-1)
    if np.any(arr < 0):
        raise ValueError("counts must be non-negative")
    return (arr > 0).astype(np.int64)


def cell_log_loss(
    y: np.ndarray | Sequence[float],
    p: np.ndarray | Sequence[float],
    *,
    clip: float = PROB_CLIP,
) -> np.ndarray:
    """Per-cell binary cross-entropy with clipped probabilities."""
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    p_arr = np.clip(np.asarray(p, dtype=np.float64).reshape(-1), clip, 1.0 - clip)
    if y_arr.shape != p_arr.shape:
        raise ValueError(f"y shape {y_arr.shape} != p shape {p_arr.shape}")
    if y_arr.size == 0:
        raise ValueError("empty log-loss input")
    if not np.isin(y_arr, [0.0, 1.0]).all():
        raise ValueError("labels must be binary 0/1")
    return -(y_arr * np.log(p_arr) + (1.0 - y_arr) * np.log(1.0 - p_arr))


def mean_cell_log_loss(
    y: np.ndarray | Sequence[float],
    p: np.ndarray | Sequence[float],
    *,
    clip: float = PROB_CLIP,
) -> float:
    return float(np.mean(cell_log_loss(y, p, clip=clip)))


def donor_average_cell_log_loss(
    donors: Sequence[str],
    y: np.ndarray | Sequence[float],
    p: np.ndarray | Sequence[float],
    *,
    clip: float = PROB_CLIP,
) -> dict[str, Any]:
    """Equal mean across donors of within-donor mean cell log-loss.

    Mixed cell labels within a donor are allowed. Cell counts may differ across
    donors; each donor contributes equally (not cell-weighted pooling).
    """
    donor_arr = np.asarray(donors).astype(str).reshape(-1)
    losses = cell_log_loss(y, p, clip=clip)
    if donor_arr.shape != losses.shape:
        raise ValueError("donors length must match y/p")
    if donor_arr.size == 0:
        raise ValueError("empty donor-average input")
    unique = sorted(set(donor_arr.tolist()))
    per_donor: dict[str, float] = {}
    n_cells: dict[str, int] = {}
    for donor in unique:
        mask = donor_arr == donor
        per_donor[donor] = float(np.mean(losses[mask]))
        n_cells[donor] = int(mask.sum())
    value = float(np.mean(list(per_donor.values())))
    return {
        "value": value,
        "n_donors": len(unique),
        "per_donor_mean_cell_log_loss": per_donor,
        "per_donor_n_cells": n_cells,
        "aggregation": "equal_mean_of_within_donor_mean_cell_log_loss",
        "mixed_labels_allowed": True,
    }


def refuse_donor_average_probability_as_primary(
    donors: Sequence[str],
    y: np.ndarray | Sequence[float],
    p: np.ndarray | Sequence[float],
) -> dict[str, Any]:
    """Document why donor-mean probability + donor-mode label is not the estimand.

    Returns the numerically different wrong statistic so tests can assert
    inequality against the correct donor-average cell log-loss.
    """
    donor_arr = np.asarray(donors).astype(str).reshape(-1)
    y_arr = np.asarray(y, dtype=np.float64).reshape(-1)
    p_arr = np.asarray(p, dtype=np.float64).reshape(-1)
    unique = sorted(set(donor_arr.tolist()))
    donor_p: list[float] = []
    donor_y: list[float] = []
    for donor in unique:
        mask = donor_arr == donor
        donor_p.append(float(np.mean(p_arr[mask])))
        # Mode / majority label — the disease-style collapse that is forbidden.
        vals, counts = np.unique(y_arr[mask], return_counts=True)
        donor_y.append(float(vals[int(np.argmax(counts))]))
    wrong_loss = mean_cell_log_loss(donor_y, donor_p)
    correct = donor_average_cell_log_loss(donors, y, p)
    return {
        "forbidden_as_primary": True,
        "wrong_statistic_name": "log_loss(donor_mode_label, donor_mean_probability)",
        "wrong_value": wrong_loss,
        "correct_value": correct["value"],
        "values_differ": not np.isclose(wrong_loss, correct["value"], rtol=0.0, atol=1e-12),
        "reason": (
            "Donor-average probability / majority-label collapse invents a fake "
            "donor class and ignores within-donor mixed accessibility targets"
        ),
    }


def hand_calculated_metric_example() -> dict[str, Any]:
    """Tiny unequal-cell / mixed-label fixture with closed-form checks."""
    donors = ["A", "A", "A", "B"]
    y = np.asarray([1, 0, 1, 0], dtype=np.float64)
    p = np.asarray([0.9, 0.2, 0.8, 0.3], dtype=np.float64)
    # Cell losses (clip unused; probs interior):
    # A0: -log(0.9); A1: -log(0.8); A2: -log(0.8); B0: -log(0.7)
    expected_cells = np.asarray(
        [
            -np.log(0.9),
            -np.log(0.8),
            -np.log(0.8),
            -np.log(0.7),
        ],
        dtype=np.float64,
    )
    expected_a = float(np.mean(expected_cells[:3]))
    expected_b = float(expected_cells[3])
    expected_donor_avg = float(np.mean([expected_a, expected_b]))
    got = donor_average_cell_log_loss(donors, y, p)
    cells = cell_log_loss(y, p)
    wrong = refuse_donor_average_probability_as_primary(donors, y, p)
    return {
        "donors": donors,
        "y": y.tolist(),
        "p": p.tolist(),
        "expected_cell_log_loss": expected_cells.tolist(),
        "got_cell_log_loss": cells.tolist(),
        "expected_donor_A_mean": expected_a,
        "expected_donor_B_mean": expected_b,
        "expected_donor_average": expected_donor_avg,
        "got_donor_average": got["value"],
        "cell_match": bool(np.allclose(cells, expected_cells, rtol=0.0, atol=1e-12)),
        "donor_average_match": bool(
            np.isclose(got["value"], expected_donor_avg, rtol=0.0, atol=1e-12)
        ),
        "wrong_donor_avg_prob": wrong,
        "n_cells_unequal": got["per_donor_n_cells"] == {"A": 3, "B": 1},
        "mixed_labels_in_donor_A": True,
    }


def oracle_and_constant_direction_check() -> dict[str, Any]:
    """Oracle near-zero loss; constant mid prediction worse — no fits."""
    donors = ["D0", "D0", "D1", "D1"]
    y = np.asarray([1, 0, 1, 0], dtype=np.float64)
    oracle_p = np.clip(y, PROB_CLIP, 1.0 - PROB_CLIP)
    # Keep oracle slightly interior so clip does not dominate.
    oracle_p = np.where(y == 1.0, 1.0 - 1e-6, 1e-6)
    constant_p = np.full_like(y, 0.5)
    oracle = donor_average_cell_log_loss(donors, y, oracle_p)
    constant = donor_average_cell_log_loss(donors, y, constant_p)
    return {
        "oracle_value": oracle["value"],
        "constant_0_5_value": constant["value"],
        "oracle_better_than_constant": oracle["value"] < constant["value"],
        "oracle_near_zero": oracle["value"] < 1e-4,
        "constant_equals_ln2": bool(
            np.isclose(constant["value"], np.log(2.0), rtol=0.0, atol=1e-12)
        ),
    }


def visible_atac_tfidf_fit(
    atac_counts: np.ndarray,
    visible_indices: Sequence[int],
    train_rows: np.ndarray | Sequence[bool],
) -> dict[str, Any]:
    """Fit TF-IDF on visible ATAC columns only (train-row IDF).

    Panel depth / TF denominators use visible columns only — never the target.
    """
    mat = np.asarray(atac_counts, dtype=np.float64)
    if mat.ndim != 2:
        raise ValueError("atac_counts must be 2-d (cells × regions)")
    vis = np.asarray(list(visible_indices), dtype=np.int64)
    if vis.size == 0:
        raise ValueError("visible_indices empty")
    if np.any(vis < 0) or np.any(vis >= mat.shape[1]):
        raise ValueError("visible_indices out of range")
    train = np.asarray(train_rows)
    if train.dtype != bool:
        mask = np.zeros(mat.shape[0], dtype=bool)
        mask[np.asarray(train_rows, dtype=np.int64)] = True
        train = mask
    if train.shape != (mat.shape[0],):
        raise ValueError("train_rows shape mismatch")
    if int(train.sum()) < 1:
        raise ValueError("need at least one training row")

    visible = mat[:, vis]
    panel_total = visible.sum(axis=1)
    safe_total = np.where(panel_total > 0, panel_total, 1.0)
    tf = visible / safe_total[:, None]
    df = (visible[train] > 0).sum(axis=0).astype(np.float64)
    n_train = int(train.sum())
    idf = np.log((1.0 + n_train) / (1.0 + df)) + 1.0
    encoded = np.log1p(tf * idf).astype(np.float64)
    return {
        "n_visible": int(vis.size),
        "n_train": n_train,
        "idf": idf,
        "encoded": encoded,
        "panel_total": panel_total.astype(np.float64),
        "idf_sha256": sha256_array(idf),
        "encoded_sha256": sha256_array(encoded),
        "panel_total_sha256": sha256_array(panel_total.astype(np.float64)),
        "visible_indices_sha256": sha256_lines([str(int(i)) for i in vis.tolist()]),
    }


def target_inclusive_panel_depth_leaks(
    atac_counts: np.ndarray,
    visible_indices: Sequence[int],
    target_index: int,
    train_rows: np.ndarray | Sequence[bool],
) -> dict[str, Any]:
    """Demonstrate that including the target in panel depth changes visible TF."""
    mat = np.asarray(atac_counts, dtype=np.float64)
    vis = list(visible_indices)
    if target_index in vis:
        raise ValueError("target_index must not already be in visible_indices")
    leak_cols = vis + [int(target_index)]
    base = visible_atac_tfidf_fit(mat, vis, train_rows)
    # Fit stats when panel wrongly includes target column for depth only:
    train = np.asarray(train_rows)
    if train.dtype != bool:
        mask = np.zeros(mat.shape[0], dtype=bool)
        mask[np.asarray(train_rows, dtype=np.int64)] = True
        train = mask
    panel = mat[:, leak_cols]
    panel_total = panel.sum(axis=1)
    safe = np.where(panel_total > 0, panel_total, 1.0)
    tf_vis = mat[:, vis] / safe[:, None]
    # Mutate target and recompute.
    mutated = mat.copy()
    mutated[:, target_index] = mutated[:, target_index] + 5.0
    panel_m = mutated[:, leak_cols]
    total_m = panel_m.sum(axis=1)
    safe_m = np.where(total_m > 0, total_m, 1.0)
    tf_vis_m = mutated[:, vis] / safe_m[:, None]
    changed = not np.allclose(tf_vis, tf_vis_m, rtol=0.0, atol=0.0)
    # Correct visible-only path remains invariant under same mutation.
    correct_base = visible_atac_tfidf_fit(mat, vis, train_rows)
    correct_mut = visible_atac_tfidf_fit(mutated, vis, train_rows)
    return {
        "target_inclusive_depth_changes_visible_tf": changed,
        "correct_visible_only_invariant": (
            correct_base["encoded_sha256"] == correct_mut["encoded_sha256"]
            and correct_base["idf_sha256"] == correct_mut["idf_sha256"]
            and correct_base["panel_total_sha256"] == correct_mut["panel_total_sha256"]
        ),
        "base_visible_encoded_sha256": base["encoded_sha256"],
        "refused_path": "target_inclusive_nCount_or_panel_depth",
    }


def assert_target_perturbation_leaves_inputs_unchanged(
    *,
    rna: np.ndarray,
    atac_counts: np.ndarray,
    visible_indices: Sequence[int],
    target_index: int,
    train_rows: np.ndarray | Sequence[bool],
) -> dict[str, Any]:
    """Mutate target counts; RNA and visible-ATAC fit stats must be identical."""
    rna = np.asarray(rna, dtype=np.float64)
    atac = np.asarray(atac_counts, dtype=np.float64)
    if target_index in set(int(i) for i in visible_indices):
        raise ValueError("target_index must be excluded from visible_indices")
    rna_sha = sha256_array(rna)
    base = visible_atac_tfidf_fit(atac, visible_indices, train_rows)
    mutated = atac.copy()
    # Strong artificial change including zeros ↔ positives.
    mutated[:, target_index] = (mutated[:, target_index] + 7.0) * 3.0 + 1.0
    mut_fit = visible_atac_tfidf_fit(mutated, visible_indices, train_rows)
    rna_unchanged = sha256_array(rna) == rna_sha
    fit_unchanged = (
        base["idf_sha256"] == mut_fit["idf_sha256"]
        and base["encoded_sha256"] == mut_fit["encoded_sha256"]
        and base["panel_total_sha256"] == mut_fit["panel_total_sha256"]
    )
    labels_changed = not np.array_equal(
        binary_presence_labels(atac[:, target_index]),
        binary_presence_labels(mutated[:, target_index]),
    )
    return {
        "rna_unchanged": bool(rna_unchanged),
        "visible_atac_fit_stats_unchanged": bool(fit_unchanged),
        "target_labels_did_change": bool(labels_changed),
        "base_idf_sha256": base["idf_sha256"],
        "mut_idf_sha256": mut_fit["idf_sha256"],
        "base_encoded_sha256": base["encoded_sha256"],
        "mut_encoded_sha256": mut_fit["encoded_sha256"],
        "passed": bool(rna_unchanged and fit_unchanged and labels_changed),
    }


def assert_chromosome_mask_exclusivity(
    region_chroms: Sequence[str],
    visible_indices: Sequence[int],
    target_chrom: str,
) -> None:
    """Refuse if any visible region shares the target chromosome."""
    for idx in visible_indices:
        chrom = str(region_chroms[int(idx)])
        if chrom == str(target_chrom):
            raise ValueError(
                f"chromosome-mask leak: visible region {idx} has chrom "
                f"{chrom!r} matching target {target_chrom!r}"
            )


def assert_no_forbidden_features(feature_names: Sequence[str]) -> list[str]:
    """Return forbidden names found in a proposed feature list."""
    names = {str(n) for n in feature_names}
    return sorted(names & set(FORBIDDEN_FEATURE_FIELDS))


def feature_order_hash(feature_names: Sequence[str]) -> str:
    return sha256_lines([str(n) for n in feature_names])


def refuse_output_overwrite(path: Path) -> None:
    """Refuse writing when the destination already exists."""
    if Path(path).exists():
        raise FileExistsError(f"refusing to overwrite existing path: {path}")


def assert_prediction_reload_identity(
    probs_a: Sequence[float] | np.ndarray,
    probs_b: Sequence[float] | np.ndarray,
    *,
    atol: float = 1e-6,
) -> dict[str, Any]:
    """Reload/repeat predictions must match within atol (no fits)."""
    a = np.asarray(probs_a, dtype=np.float64).reshape(-1)
    b = np.asarray(probs_b, dtype=np.float64).reshape(-1)
    if a.shape != b.shape:
        return {
            "passed": False,
            "max_abs_diff": None,
            "reason": f"shape mismatch {a.shape} vs {b.shape}",
        }
    max_diff = float(np.max(np.abs(a - b))) if a.size else None
    passed = a.size > 0 and max_diff is not None and max_diff <= float(atol)
    return {
        "passed": bool(passed),
        "atol": float(atol),
        "max_abs_diff": max_diff,
        "reason": None if passed else "predictions differ beyond atol",
    }


def assert_existing_mil_refuses_mixed_labels() -> dict[str, Any]:
    """Live check that disease MIL donor map rejects mixed cell labels."""
    from p22.training.mil_loop import _donor_label_map

    donors = np.asarray(["D0", "D0", "D1"], dtype=str)
    mixed = np.asarray([1, 0, 1], dtype=np.int64)
    refused = False
    message = ""
    try:
        _donor_label_map(donors, mixed)
    except ValueError as exc:
        refused = True
        message = str(exc)
    # Control: uniform labels still accepted.
    ok_map = _donor_label_map(donors, np.asarray([1, 1, 0], dtype=np.int64))
    return {
        "mixed_refused": refused,
        "message": message,
        "uniform_accepted": ok_map == {"D0": 1, "D1": 0},
        "adapter_required": True,
        "adapter_requirements": ADAPTER_REQUIREMENTS,
    }


def build_toy_leakage_arrays() -> dict[str, Any]:
    """Deterministic tiny RNA/ATAC arrays for leakage falsification."""
    # 4 cells × 4 ATAC regions; region 1 is the target (chrT); visible = {0,2,3}.
    rng = np.random.default_rng(22)
    rna = rng.normal(size=(4, 3)).astype(np.float64)
    atac = np.asarray(
        [
            [2, 0, 1, 0],
            [0, 3, 0, 2],
            [1, 0, 4, 1],
            [0, 5, 0, 0],
        ],
        dtype=np.float64,
    )
    return {
        "rna": rna,
        "atac": atac,
        "visible_indices": [0, 2, 3],
        "target_index": 1,
        "train_rows": np.asarray([True, True, False, False]),
        "region_chroms": ["chrA", "chrT", "chrA", "chrB"],
        "target_chrom": "chrT",
    }


def run_falsification_suite() -> dict[str, Any]:
    """Execute all M4 no-fit falsification checks; return machine report body."""
    metric_ex = hand_calculated_metric_example()
    direction = oracle_and_constant_direction_check()
    mil = assert_existing_mil_refuses_mixed_labels()
    toy = build_toy_leakage_arrays()
    assert_chromosome_mask_exclusivity(
        toy["region_chroms"], toy["visible_indices"], toy["target_chrom"]
    )
    chrom_refused = False
    try:
        assert_chromosome_mask_exclusivity(
            toy["region_chroms"], [0, 1, 2], toy["target_chrom"]
        )
    except ValueError:
        chrom_refused = True
    inv = assert_target_perturbation_leaves_inputs_unchanged(
        rna=toy["rna"],
        atac_counts=toy["atac"],
        visible_indices=toy["visible_indices"],
        target_index=toy["target_index"],
        train_rows=toy["train_rows"],
    )
    leak_path = target_inclusive_panel_depth_leaks(
        toy["atac"],
        toy["visible_indices"],
        toy["target_index"],
        toy["train_rows"],
    )
    forbidden_hit = assert_no_forbidden_features(
        ["rna_gene_0", "visible_atac_0", "disease", "nCount_ATAC", "donor_id"]
    )
    allowed_features = ["rna_gene_0", "rna_gene_1", "visible_atac_0", "visible_atac_1"]
    forbidden_clean = assert_no_forbidden_features(allowed_features)
    order_a = feature_order_hash(allowed_features)
    order_b = feature_order_hash(list(reversed(allowed_features)))
    reload = assert_prediction_reload_identity([0.1, 0.2, 0.3], [0.1, 0.2, 0.3])
    reload_fail = assert_prediction_reload_identity([0.1, 0.2], [0.1, 0.9])
    overwrite_refused = False
    # Use a path that exists in-repo; refuse_output_overwrite must raise.
    try:
        refuse_output_overwrite(Path(__file__))
    except FileExistsError:
        overwrite_refused = True

    checks = {
        "hand_calculated_metric_match": bool(
            metric_ex["cell_match"] and metric_ex["donor_average_match"]
        ),
        "wrong_donor_avg_prob_differs": bool(
            metric_ex["wrong_donor_avg_prob"]["values_differ"]
        ),
        "oracle_better_than_constant": bool(direction["oracle_better_than_constant"]),
        "oracle_near_zero": bool(direction["oracle_near_zero"]),
        "constant_equals_ln2": bool(direction["constant_equals_ln2"]),
        "mil_mixed_label_refused": bool(mil["mixed_refused"] and mil["uniform_accepted"]),
        "target_perturbation_invariant": bool(inv["passed"]),
        "target_inclusive_depth_leaks": bool(
            leak_path["target_inclusive_depth_changes_visible_tf"]
            and leak_path["correct_visible_only_invariant"]
        ),
        "chromosome_mask_exclusivity_ok": True,
        "chromosome_mask_leak_refused": bool(chrom_refused),
        "forbidden_features_detected": forbidden_hit
        == ["disease", "donor_id", "nCount_ATAC"],
        "allowed_features_clean": forbidden_clean == [],
        "feature_order_hash_sensitive": order_a != order_b,
        "prediction_reload_identity": bool(reload["passed"]),
        "prediction_reload_detects_drift": not bool(reload_fail["passed"]),
        "output_overwrite_refused": bool(overwrite_refused),
    }
    all_pass = all(bool(v) for v in checks.values())
    return {
        "disposition": "FALSIFICATION_PASS" if all_pass else "FALSIFICATION_FAIL",
        "checks": checks,
        "metric_example": {
            "expected_donor_average": metric_ex["expected_donor_average"],
            "got_donor_average": metric_ex["got_donor_average"],
            "n_cells_unequal": metric_ex["n_cells_unequal"],
            "mixed_labels_in_donor_A": metric_ex["mixed_labels_in_donor_A"],
            "wrong_donor_avg_prob_value": metric_ex["wrong_donor_avg_prob"][
                "wrong_value"
            ],
            "correct_donor_avg_cell_loss": metric_ex["wrong_donor_avg_prob"][
                "correct_value"
            ],
        },
        "direction": direction,
        "leakage": {
            "target_perturbation": inv,
            "target_inclusive_depth": leak_path,
            "forbidden_feature_fields": list(FORBIDDEN_FEATURE_FIELDS),
            "forbidden_hit_example": forbidden_hit,
        },
        "adapter": mil,
        "feature_order": {
            "hash_forward": order_a,
            "hash_reversed": order_b,
            "allowed_features": allowed_features,
        },
        "reload": {"match": reload, "drift": reload_fail},
        "overwrite_refusal_verified": overwrite_refused,
    }
