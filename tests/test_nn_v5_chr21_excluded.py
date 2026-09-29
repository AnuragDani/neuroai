"""P1/N11: chr21-excluded_v3 summarizer resolves canonical ladder and labels."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from nn_v5_chr21_excluded import decide_label, load_repeats, resolve_canonical_ladder, summarize

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_existing_folds():
    ladder = resolve_canonical_ladder()
    assert (ladder / "folds").is_dir()
    assert ladder.name == "ladder_v3"


def test_decide_label_dosage_dominated():
    results = {
        "R3_ca": {"ba_without_chr21": 0.4},
        "R3_tc": {"ba_without_chr21": 0.5},
        "logreg_rna": {"ba_without_chr21": 0.55},
        "logreg_concat": {"ba_without_chr21": 0.45},
    }
    assert decide_label(results) == "DOSAGE_DOMINATED"


def test_decide_label_beyond_dosage():
    results = {"R3_ca": {"ba_without_chr21": 0.61}, "R3_tc": {"ba_without_chr21": 0.4}}
    assert decide_label(results) == "BEYOND_DOSAGE (R3_ca)"


def test_load_repeats_and_summarize_on_tiny_synthetic(tmp_path: Path):
    def _write_fold(root: Path, arm: str, rep: int, fold: int, probs, labels):
        out = root / "folds"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"r{rep}_f{fold}_{arm}.json").write_text(
            json.dumps(
                {
                    "repeat": rep,
                    "fold": fold,
                    "arm": arm,
                    "donor_ids": [f"d{i}" for i in range(len(labels))],
                    "donor_labels": labels,
                    "donor_probabilities": probs,
                }
            )
        )

    ladder = tmp_path / "ladder"
    excl = tmp_path / "excl"
    # Perfect with-chr21; chance without.
    _write_fold(ladder, "R3_ca", 0, 0, [0.9, 0.1, 0.9, 0.1], [1, 0, 1, 0])
    _write_fold(ladder, "R3_tc", 0, 0, [0.8, 0.2, 0.8, 0.2], [1, 0, 1, 0])
    _write_fold(ladder, "logreg_rna", 0, 0, [0.7, 0.3, 0.7, 0.3], [1, 0, 1, 0])
    _write_fold(ladder, "logreg_concat", 0, 0, [0.75, 0.25, 0.75, 0.25], [1, 0, 1, 0])
    _write_fold(excl, "R3_ca", 0, 0, [0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0])
    _write_fold(excl, "R3_tc", 0, 0, [0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0])
    _write_fold(excl, "logreg_rna", 0, 0, [0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0])
    _write_fold(excl, "logreg_concat", 0, 0, [0.5, 0.5, 0.5, 0.5], [1, 0, 1, 0])

    repeats, arms = load_repeats(ladder / "folds")
    assert arms == {"R3_ca", "R3_tc", "logreg_rna", "logreg_concat"}
    assert len(repeats) == 1
    assert isinstance(repeats[0]["R3_ca"], pd.DataFrame)

    payload = summarize(ladder, excl)
    assert payload["label"] == "DOSAGE_DOMINATED"
    assert payload["n_excluded_folds"] == 4
    assert set(payload.keys()) >= {
        "record_type",
        "ladder_source",
        "excluded_source",
        "label",
        "R3_ca",
    }
