"""Held-out within-disease nuisance probes for N14 (R2 rejection rule).

Pure scoring helpers: no model loading. Fit probes on outer-train cell
embeddings and score outer-test cells whose nuisance class was seen in train
for the same disease label.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression


def held_out_within_label_probe_accuracy(
    train_embeddings: np.ndarray,
    train_labels: np.ndarray,
    train_nuisance: np.ndarray,
    test_embeddings: np.ndarray,
    test_labels: np.ndarray,
    test_nuisance: np.ndarray,
    *,
    max_iter: int = 1000,
    seed: int = 0,
) -> float | None:
    """Mean within-label held-out accuracy for a categorical nuisance.

    For each disease label present in both splits, fit ``LogisticRegression`` on
    train cells and score test cells whose nuisance code appeared in that
    label's train set. Returns the unweighted mean over labels, or ``None`` if
    no label yields a scorable test subset.
    """
    train_embeddings = np.asarray(train_embeddings)
    test_embeddings = np.asarray(test_embeddings)
    train_labels = np.asarray(train_labels)
    test_labels = np.asarray(test_labels)
    train_nuisance = np.asarray(train_nuisance)
    test_nuisance = np.asarray(test_nuisance)

    scores: list[float] = []
    for label in sorted(set(train_labels.tolist()) & set(test_labels.tolist())):
        tr = train_labels == label
        te = test_labels == label
        if tr.sum() < 2 or te.sum() < 1:
            continue
        train_y = train_nuisance[tr]
        if np.unique(train_y).size < 2:
            continue
        seen = set(train_y.tolist())
        keep = np.array([v in seen for v in test_nuisance[te]], dtype=bool)
        if not keep.any():
            continue
        probe = LogisticRegression(max_iter=max_iter, random_state=seed)
        probe.fit(train_embeddings[tr], train_y)
        scores.append(
            float(probe.score(test_embeddings[te][keep], test_nuisance[te][keep]))
        )
    if not scores:
        return None
    return float(np.mean(scores))


def held_out_within_label_qc_r2(
    train_embeddings: np.ndarray,
    train_labels: np.ndarray,
    train_qc: np.ndarray,
    test_embeddings: np.ndarray,
    test_labels: np.ndarray,
    test_qc: np.ndarray,
) -> float | None:
    """Mean per-column linear R² of QC from embeddings, within disease labels."""
    train_embeddings = np.asarray(train_embeddings)
    test_embeddings = np.asarray(test_embeddings)
    train_labels = np.asarray(train_labels)
    test_labels = np.asarray(test_labels)
    train_qc = np.asarray(train_qc)
    test_qc = np.asarray(test_qc)
    if train_qc.ndim != 2 or test_qc.ndim != 2:
        raise ValueError("qc must be 2-d")

    col_scores: list[float] = []
    for col in range(train_qc.shape[1]):
        label_scores: list[float] = []
        for label in sorted(set(train_labels.tolist()) & set(test_labels.tolist())):
            tr = train_labels == label
            te = test_labels == label
            if tr.sum() < 2 or te.sum() < 1:
                continue
            model = LinearRegression()
            model.fit(train_embeddings[tr], train_qc[tr, col])
            label_scores.append(float(model.score(test_embeddings[te], test_qc[te, col])))
        if label_scores:
            col_scores.append(float(np.mean(label_scores)))
    if not col_scores:
        return None
    return float(np.mean(col_scores))


def decide_r2_rejection(
    *,
    r1_probe_accuracy: float,
    r2_probe_accuracy: float,
    r1_donor_ba: float,
    r2_donor_ba: float,
    min_probe_drop_points: float = 5.0,
    max_ba_drop: float = 0.05,
) -> dict[str, Any]:
    """Apply plan §4.2 / decision_tree N14 R2 rejection rule.

    R2 is rejected if the held-out nuisance-probe accuracy does not drop by at
    least ``min_probe_drop_points`` versus R1, or if donor BA drops by more than
    ``max_ba_drop``. A large BA drop also tags ``ADVERSARY_ERASES_SIGNAL``.
    """
    probe_drop_points = (float(r1_probe_accuracy) - float(r2_probe_accuracy)) * 100.0
    ba_drop = float(r1_donor_ba) - float(r2_donor_ba)
    probe_ok = probe_drop_points >= min_probe_drop_points
    ba_ok = ba_drop <= max_ba_drop
    rejected = (not probe_ok) or (not ba_ok)
    labels: list[str] = []
    if rejected:
        labels.append("R2_REJECTED")
    else:
        labels.append("R2_ACCEPTED")
    if ba_drop > max_ba_drop:
        labels.append("ADVERSARY_ERASES_SIGNAL")
    if not probe_ok:
        labels.append("PROBE_DROP_INSUFFICIENT")
    return {
        "probe_drop_points": probe_drop_points,
        "ba_drop": ba_drop,
        "probe_ok": probe_ok,
        "ba_ok": ba_ok,
        "rejected": rejected,
        "labels": labels,
        "decision": "R2_REJECTED" if rejected else "R2_ACCEPTED",
    }
