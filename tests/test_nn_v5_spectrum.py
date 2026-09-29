"""P1/N16: spectrum_v3 wrapper resolves canonical ladder and publishes docs."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_spectrum import (
    assert_export_binds_ladder,
    publish,
    resolve_canonical_ladder,
    resolve_cell_scores,
    resolve_chr21_scores,
    update_ladder_md,
)

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_ladder_v3():
    ladder = resolve_canonical_ladder()
    assert ladder.name == "ladder_v3"
    assert (ladder / "folds").is_dir()


def test_resolve_cell_scores_points_at_spectrum_v3():
    path = resolve_cell_scores()
    assert path.name == "cell_scores.csv.gz"
    assert "spectrum_v3" in str(path)
    assert path.is_file()


def test_resolve_chr21_scores_present():
    path = resolve_chr21_scores()
    assert path is not None
    assert path.name == "cell_scores_chr21_excluded.csv.gz"
    assert path.is_file()


def test_assert_export_binds_ladder_v3():
    ladder = resolve_canonical_ladder()
    payload = assert_export_binds_ladder(ladder)
    main = payload["ladder_export"]
    assert Path(main["source_run"]).resolve() == ladder.resolve()
    assert int(main["n_cell_arm_rows"]) == 120_000


def test_publish_and_ladder_md(tmp_path: Path, monkeypatch):
    payload = {
        "status": "estimated",
        "spectrum_call": "SPECTRUM_NULL",
        "eligible_types": ["IPC", "RG"],
        "excluded_types": [],
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
                "confound_sensitive": False,
            }
        ],
        "source": {
            "cell_scores_path": "reports/generated/nn_20260923/spectrum_v3/cell_scores.csv.gz",
            "cell_scores_sha256": "abc123def456789",
            "arm": "R3_ca",
            "ladder_source": "/tmp/ladder_v3",
        },
        "chr21_excluded_compare": {
            "status": "COMPARED",
            "spectrum_call": "SPECTRUM_NULL",
            "calls_agree": True,
        },
    }
    docs_json = tmp_path / "spectrum.json"
    docs_md = tmp_path / "SPECTRUM.md"
    ladder_md = tmp_path / "LADDER.md"
    ladder_md.write_text(
        "## Cell-state spectrum (N16)\n\nold\n\n## Routing / attention (N17)\n\nx\n"
    )
    monkeypatch.setattr("nn_v5_spectrum.DOCS_JSON", docs_json)
    monkeypatch.setattr("nn_v5_spectrum.DOCS_MD", docs_md)
    monkeypatch.setattr("nn_v5_spectrum.LADDER_MD", ladder_md)

    result = publish(payload, out_json=docs_json, out_md=docs_md)
    assert result["spectrum_call"] == "SPECTRUM_NULL"
    assert docs_json.is_file()
    md = docs_md.read_text()
    assert "ladder_v3 OOF export" in md
    assert "SPECTRUM_NULL" in md

    update_ladder_md(payload)
    text = ladder_md.read_text()
    assert "SPECTRUM_NULL" in text
    assert "COMPARED" in text
    assert "## Routing / attention (N17)" in text
