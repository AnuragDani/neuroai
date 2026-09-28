"""P1/N12: seed-sensitivity summarizer resolves canonical ladder and labels."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_seed_sensitivity import (
    assert_seed_fold_protocol,
    decide_labels,
    resolve_canonical_ladder,
    reuse_ladder_as_m0_s22,
    summarize,
)

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_ladder_v3():
    ladder = resolve_canonical_ladder()
    assert (ladder / "folds").is_dir()
    assert ladder.name == "ladder_v3"


def test_decide_labels_spread_only_for_b_null():
    assert decide_labels("B_NULL", [0.01, 0.02, 0.0], 0.04) == ["SPREAD_ONLY"]


def test_decide_labels_sampling_sensitive():
    labels = decide_labels("B_NULL", [0.0, 0.01], 0.08)
    assert labels == ["SPREAD_ONLY", "SAMPLING_SENSITIVE"]


def test_decide_labels_a_robust_init():
    labels = decide_labels("A_WIN", [0.08, 0.09, 0.1, 0.11, 0.07], 0.01)
    assert labels == ["A_ROBUST_INIT"]


def test_reuse_and_summarize_tiny(tmp_path: Path):
    ladder = tmp_path / "ladder_v3"
    lf = ladder / "folds"
    # 25 folds each arm with fixed widths; unique donors per fold within a repeat.
    for rep in range(5):
        for fold in range(5):
            base = fold * 4
            ids = [f"d{base + i}" for i in range(4)]
            labels = [1, 0, 1, 0]
            for arm, probs, params in (
                ("R3_ca", [0.9, 0.1, 0.8, 0.2], 384250),
                ("R3_tc", [0.7, 0.3, 0.6, 0.4], 380026),
            ):
                lf.mkdir(parents=True, exist_ok=True)
                (lf / f"r{rep}_f{fold}_{arm}.json").write_text(
                    json.dumps(
                        {
                            "repeat": rep,
                            "fold": fold,
                            "arm": arm,
                            "parameter_count": params,
                            "donor_ids": ids,
                            "donor_labels": labels,
                            "donor_probabilities": probs,
                        }
                    )
                )
    seeds = tmp_path / "seeds_v3"
    reuse_ladder_as_m0_s22(ladder, seeds / "m_0_s_22")
    info = assert_seed_fold_protocol(seeds / "m_0_s_22" / "folds")
    assert info["n_folds"] == 50
    # Clone m_0_s_22 into the other run dirs so summarize can run end-to-end.
    for m, s in [(1, 22), (2, 22), (3, 22), (4, 22), (0, 23), (0, 24)]:
        dest = seeds / f"m_{m}_s_{s}" / "folds"
        dest.mkdir(parents=True, exist_ok=True)
        for src in (seeds / "m_0_s_22" / "folds").glob("*.json"):
            (dest / src.name).write_text(src.read_text())
    # Point summarizer at a fake ladder_summary outcome.
    docs = tmp_path / "docs" / "nn_v2"
    docs.mkdir(parents=True)
    (docs / "ladder_summary.json").write_text(json.dumps({"outcome": "B_NULL"}))
    import nn_v5_seed_sensitivity as mod

    old_summary = mod.LADDER_SUMMARY
    mod.LADDER_SUMMARY = docs / "ladder_summary.json"
    try:
        payload = summarize(ladder, seeds, ROOT / "configs/nn_protocol_v2_2026-09-23.json")
    finally:
        mod.LADDER_SUMMARY = old_summary
    assert payload["labels"] == ["SPREAD_ONLY"]
    assert payload["model_seed_spread"] == 0.0
    assert set(payload["runs"]) == {
        "m_0_s_22",
        "m_1_s_22",
        "m_2_s_22",
        "m_3_s_22",
        "m_4_s_22",
        "m_0_s_23",
        "m_0_s_24",
    }
