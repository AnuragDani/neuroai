"""P3: spectrum on chr21-excluded scores (wrapper + reading + live bind)."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_spectrum_chr21_excluded import (
    assert_chr21_export_binds,
    assert_dosage_dominated,
    build_reading,
    publish,
    resolve_canonical_ladder,
    resolve_chr21_scores,
)

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_ladder_v3():
    ladder = resolve_canonical_ladder()
    assert ladder.name == "ladder_v3"
    assert (ladder / "folds").is_dir()


def test_resolve_chr21_scores_present():
    path = resolve_chr21_scores()
    assert path.name == "cell_scores_chr21_excluded.csv.gz"
    assert "spectrum_v3" in str(path)
    assert path.is_file()


def test_assert_chr21_export_binds_n11_v3():
    block = assert_chr21_export_binds()
    assert Path(block["source_run"]).name == "chr21_excluded_v3"
    assert int(block["n_cell_arm_rows"]) == 60_000


def test_assert_dosage_dominated():
    label = assert_dosage_dominated()
    assert "DOSAGE_DOMINATED" in label


def test_build_reading_null_and_localized(tmp_path: Path):
    base = {
        "status": "estimated",
        "eligible_types": ["IPC", "RG"],
        "results": [
            {
                "author_cell_type": "IPC",
                "n_donors_ds": 15,
                "n_donors_con": 15,
                "s": {
                    "diff": -0.1,
                    "ci_low": -0.2,
                    "ci_high": 0.0,
                    "p_holm": 0.2,
                    "significant": False,
                },
            },
            {
                "author_cell_type": "RG",
                "n_donors_ds": 15,
                "n_donors_con": 15,
                "s": {
                    "diff": -0.2,
                    "ci_low": -0.3,
                    "ci_high": -0.1,
                    "p_holm": 0.01,
                    "significant": True,
                },
            },
        ],
        "source": {
            "cell_scores_path": "reports/generated/nn_20260923/spectrum_v3/cell_scores_chr21_excluded.csv.gz",
            "cell_scores_sha256": "abc123def456789",
            "arm": "R3_ca",
            "chr21_excluded_run": "/tmp/chr21_excluded_v3",
            "n11_label": "DOSAGE_DOMINATED",
        },
    }
    null_payload = dict(base, spectrum_call="SPECTRUM_NULL", label="SPECTRUM_NULL")
    null_payload["results"] = [dict(base["results"][0])]
    text = build_reading(null_payload)
    assert text.count("\n") + 1 <= 40
    assert "`SPECTRUM_NULL`" in text
    assert "mechanism" not in text.lower()

    loc_payload = dict(base, spectrum_call="SPECTRUM_LOCALIZED:RG", label="SPECTRUM_LOCALIZED:RG")
    text2 = build_reading(loc_payload)
    assert text2.count("\n") + 1 <= 40
    assert "SPECTRUM_LOCALIZED:RG" in text2
    assert "Holm-significant" in text2


def test_publish_writes_json_and_reading(tmp_path: Path):
    payload = {
        "status": "estimated",
        "spectrum_call": "SPECTRUM_NULL",
        "label": "SPECTRUM_NULL",
        "eligible_types": ["IPC"],
        "results": [
            {
                "author_cell_type": "IPC",
                "n_donors_ds": 15,
                "n_donors_con": 15,
                "s": {
                    "diff": -0.05,
                    "ci_low": -0.1,
                    "ci_high": 0.05,
                    "p_holm": 0.5,
                    "significant": False,
                },
            }
        ],
        "source": {
            "cell_scores_path": "x.csv.gz",
            "cell_scores_sha256": "deadbeefcafe01",
            "arm": "R3_ca",
            "chr21_excluded_run": "/tmp/chr21_excluded_v3",
            "n11_label": "DOSAGE_DOMINATED",
        },
        "task": "P3",
    }
    out_json = tmp_path / "spectrum_chr21_excluded.json"
    out_md = tmp_path / "SPECTRUM_CHR21_EXCLUDED.md"
    result = publish(payload, out_json=out_json, out_md=out_md)
    assert result["spectrum_call"] == "SPECTRUM_NULL"
    assert result["n_lines_reading"] <= 40
    assert json.loads(out_json.read_text())["label"] == "SPECTRUM_NULL"
    assert "SPECTRUM_NULL" in out_md.read_text()
