"""P1/N15: cell_scores_v3 wrapper resolves canonical ladder and publishes docs."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_cell_scores import (
    assert_ladder_has_models,
    publish,
    render_markdown,
    resolve_canonical_ladder,
    resolve_chr21_excluded,
    update_ladder_md,
)

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_ladder_v3():
    ladder = resolve_canonical_ladder()
    assert ladder.name == "ladder_v3"
    assert (ladder / "folds").is_dir()
    assert (ladder / "models").is_dir()


def test_assert_ladder_has_n15_models_on_canonical():
    info = assert_ladder_has_models(resolve_canonical_ladder())
    assert info["n_models_per_arm"] == 25
    assert set(info["arms"]) == {"R1_ca", "R3_ca", "R3_tc", "R4_ca"}


def test_resolve_chr21_excluded_prefers_v3():
    ladder = resolve_canonical_ladder()
    path = resolve_chr21_excluded(ladder)
    assert path.name == "chr21_excluded_v3"
    assert (path / "models" / "R3_ca").is_dir()


def test_render_markdown_binds_ladder_name():
    payload = {
        "ladder_export": {
            "arms": ["R1_ca", "R3_ca", "R3_tc", "R4_ca"],
            "folds_used": 100,
            "n_cell_arm_rows": 120000,
            "n_donor_celltype_rows": 1800,
            "five_appearances_asserted": True,
            "parameter_counts": {"R3_ca": 384250},
            "n_library": 37,
            "n_batch": 12,
            "cell_scores_path": "reports/generated/nn_20260923/spectrum_v3/cell_scores.csv.gz",
            "donor_celltype_scores_path": "docs/nn_v2/donor_celltype_scores.csv.gz",
            "source_run": "/tmp/ladder_v3",
        },
        "chr21_excluded_export": {
            "status": "DEFERRED",
            "reason": "test",
        },
    }
    md = render_markdown(payload, Path("/tmp/ladder_v3"))
    assert "ladder_v3" in md
    assert "120000" in md
    assert "DEFERRED" in md


def test_publish_and_ladder_md(tmp_path: Path, monkeypatch):
    spectrum = tmp_path / "spectrum_v3"
    spectrum.mkdir()
    ladder = tmp_path / "ladder_v3"
    ladder.mkdir()
    cells = spectrum / "cell_scores.csv.gz"
    compact = tmp_path / "donor_celltype_scores.csv.gz"
    cells.write_bytes(b"cell")
    compact.write_bytes(b"donor")
    payload = {
        "ladder_export": {
            "source_run": str(ladder.resolve()),
            "arms": ["R1_ca", "R3_ca", "R3_tc", "R4_ca"],
            "folds_used": 100,
            "n_cell_arm_rows": 120000,
            "n_donor_celltype_rows": 1800,
            "five_appearances_asserted": True,
            "parameter_counts": {"R3_ca": 384250},
            "n_library": 37,
            "n_batch": 12,
            "cell_scores_path": str(cells),
            "donor_celltype_scores_path": str(compact),
        },
        "chr21_excluded_export": {"status": "DEFERRED", "reason": "test"},
    }
    (spectrum / "cell_scores_export.json").write_text(json.dumps(payload) + "\n")

    docs_json = tmp_path / "cell_scores_export.json"
    docs_md = tmp_path / "CELL_SCORES.md"
    ladder_md = tmp_path / "LADDER.md"
    ladder_md.write_text(
        "## Out-of-fold cell scores (N15)\n\nold\n\n## Cell-state spectrum (N16)\n\nx\n"
    )
    monkeypatch.setattr("nn_v5_cell_scores.DOCS_JSON", docs_json)
    monkeypatch.setattr("nn_v5_cell_scores.DOCS_MD", docs_md)
    monkeypatch.setattr("nn_v5_cell_scores.LADDER_MD", ladder_md)

    result = publish(spectrum, ladder)
    assert result["n_cell_arm_rows"] == 120000
    assert docs_json.is_file()
    written = json.loads(docs_json.read_text())
    assert "cell_scores_sha256" in written["ladder_export"]
    assert written["ladder_export"]["source_run"] == str(ladder.resolve())
    assert "ladder_v3" in docs_md.read_text()

    update_ladder_md(written)
    ladder_text = ladder_md.read_text()
    assert "ladder_v3" in ladder_text
    assert "## Cell-state spectrum (N16)" in ladder_text
