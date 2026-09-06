"""Immutable software-run settings and strict paired donor comparisons.

This is not scientific approval or an accepted real-data feature protocol.
Real release/QC, provenance, and measurement-space gates remain separate.
"""

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from p22.data.splits import _as_donor_array
from p22.eval.estimand import practical_margin
from p22.eval.metrics import MetricValue, balanced_accuracy
from p22.eval.statistics import donor_bootstrap


@dataclass(frozen=True)
class MultiomeProtocol:
    """Small CPU model budget; fingerprint settings before a synthetic run."""

    n_tokens: int = 4
    embed_dim: int = 16
    hidden_dim: int = 32
    n_heads: int = 2
    dropout: float = 0.1
    feature_budget: int = 128
    cell_cap: int = 256
    max_epochs: int = 20
    patience: int = 5
    batch_size: int = 64
    learning_rate: float = 0.001
    n_repeats: int = 5
    n_folds: int = 5
    split_seed: int = 0
    model_seed: int = 0
    sampling_seed: int = 22

    def __post_init__(self):
        for name, value in asdict(self).items():
            if name in {"dropout", "learning_rate"}:
                lower = value >= 0 if name == "dropout" else value > 0
                if isinstance(value, bool) or not lower or not value < 1:
                    raise ValueError(f"invalid {name}")
            else:
                minimum = 0 if name.endswith("seed") else 1
                if type(value) is not int or value < minimum:
                    raise ValueError(f"{name} must be an integer >= {minimum}")
        if self.n_tokens < 2 or self.n_folds < 2 or self.embed_dim % self.n_heads:
            raise ValueError("need >=2 tokens/folds and heads dividing embed_dim")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


def paired_comparison(model: pd.DataFrame, reference: pd.DataFrame) -> dict:
    """Cross-attention minus matched concat; identical unique donors required.

    Uses one shared donor-index draw per replicate through the existing donor
    bootstrap. Invalid single-class resamples are counted, never redrawn.
    A positive advantage requires delta >= count-derived margin AND lower > 0.
    """
    aligned = []
    for frame in (model, reference):
        if not {"donor_id", "label", "probability"}.issubset(frame.columns):
            raise ValueError("predictions require donor_id, label, probability")
        frame = frame.copy()
        frame["donor_id"] = _as_donor_array(frame["donor_id"]).astype(str)
        if frame["donor_id"].duplicated().any():
            raise ValueError("duplicate donor predictions")
        if not frame["label"].isin([0, 1]).all() or set(frame["label"]) != {0, 1}:
            raise ValueError("predictions require both binary classes")
        probability = frame["probability"].to_numpy(dtype=float)
        if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
            raise ValueError("probabilities must be finite and within [0, 1]")
        aligned.append(frame.sort_values("donor_id").reset_index(drop=True))
    left, right = aligned
    if not left["donor_id"].equals(right["donor_id"]):
        raise ValueError("models must have identical donor sets")
    if not np.array_equal(left["label"], right["label"]):
        raise ValueError("models have inconsistent donor labels")
    labels = left["label"].to_numpy(dtype=int)
    a, b = [(frame["probability"].to_numpy() >= 0.5).astype(int) for frame in aligned]

    def delta(truth, indices):
        first, second = balanced_accuracy(truth, a[indices]), balanced_accuracy(truth, b[indices])
        return MetricValue(
            "paired_donor_balanced_accuracy_delta",
            first.value - second.value if first.applicable else None,
            not_applicable=first.not_applicable,
        )

    interval = donor_bootstrap(
        delta, labels, np.arange(len(labels)), left["donor_id"], n_replicates=1000, seed=22
    ).to_dict()
    n_control, n_positive = int(sum(labels == 0)), int(sum(labels == 1))
    margin = practical_margin(n_control, n_positive)
    interval.update(
        n_control=n_control,
        n_positive=n_positive,
        practical_margin=margin,
        advantage_demonstrated=bool(
            interval["estimate"] >= margin
            and interval["interval"][0] is not None
            and interval["interval"][0] > 0
        ),
    )
    return interval
