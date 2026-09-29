"""P1/N14: nuisance_v3 wrapper resolves canonical ladder and publishes docs."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_nuisance_probe import (
    assert_ladder_has_models,
    publish,
    render_markdown,
    resolve_canonical_ladder,
    update_ladder_md,
)

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_ladder_v3():
    ladder = resolve_canonical_ladder()
    assert ladder.name == "ladder_v3"
    assert (ladder / "folds").is_dir()
    assert (ladder / "models").is_dir()


def test_assert_ladder_has_n14_models_on_canonical():
    info = assert_ladder_has_models(resolve_canonical_ladder())
    assert info["n_models_per_arm"] == 25
    assert set(info["arms"]) >= {"R1_ca", "R2_ca", "R3_tc"}


def test_render_markdown_binds_ladder_name():
    payload = {
        "decision": {
            "r2_rejection_decision": "R2_REJECTED",
            "labels": ["R2_REJECTED", "PROBE_DROP_INSUFFICIENT"],
            "by_fusion": {
                "ca": {"probe_drop_points": -0.7, "ba_drop": -0.01},
                "tc": {"probe_drop_points": -0.5, "ba_drop": 0.02},
            },
        },
        "n_fold_rows": 150,
        "folds": [{"library_accuracy": None}] * 150,
        "arm_summaries": [
            {
                "arm": "R1_ca",
                "batch_accuracy": 0.05,
                "library_accuracy": None,
                "qc_r2": -0.1,
                "donor_ba": 0.5,
                "parameter_count": 1,
            }
        ],
    }
    md = render_markdown(payload, Path("/tmp/ladder_v3"))
    assert "ladder_v3" in md
    assert "R2_REJECTED" in md
    assert "PROBE_DROP_INSUFFICIENT" in md
    assert "No `ADVERSARY_ERASES_SIGNAL`" in md
    assert md.count("`R2_REJECTED`") == 1
    assert "| R1_ca |" in md


def test_publish_and_ladder_md(tmp_path: Path, monkeypatch):
    run_out = tmp_path / "nuisance_v3"
    run_out.mkdir()
    ladder = tmp_path / "ladder_v3"
    ladder.mkdir()
    payload = {
        "task": "N14",
        "status": "DONE",
        "source_run": "/old/ladder_v2",
        "smoke": False,
        "n_fold_rows": 150,
        "folds": [{"library_accuracy": None}] * 150,
        "arm_summaries": [
            {
                "arm": "R1_ca",
                "batch_accuracy": 0.05,
                "library_accuracy": None,
                "qc_r2": -0.1,
                "donor_ba": 0.5,
                "parameter_count": 10,
            }
        ],
        "decision": {
            "r2_rejection_decision": "R2_REJECTED",
            "labels": ["R2_REJECTED", "PROBE_DROP_INSUFFICIENT"],
            "by_fusion": {
                "ca": {"probe_drop_points": -0.5, "ba_drop": 0.0},
                "tc": {"probe_drop_points": -0.4, "ba_drop": 0.01},
            },
        },
    }
    (run_out / "nuisance_probe.json").write_text(json.dumps(payload))
    docs = tmp_path / "docs" / "nn_v2"
    docs.mkdir(parents=True)
    import nn_v5_nuisance_probe as mod

    monkeypatch.setattr(mod, "DOCS_JSON", docs / "nuisance_probe.json")
    monkeypatch.setattr(mod, "DOCS_MD", docs / "NUISANCE_PROBE.md")
    monkeypatch.setattr(mod, "LADDER_MD", docs / "LADDER.md")
    (docs / "LADDER.md").write_text(
        "## Nuisance-probe diagnostics (N14)\n\nold ladder_v2 text\n\n"
        "## Out-of-fold cell scores (N15)\n\nx\n"
    )
    result = publish(run_out, ladder)
    assert result["decision"] == "R2_REJECTED"
    assert "ladder_v3" in result["source_run"]
    written = json.loads((docs / "nuisance_probe.json").read_text())
    assert written["source_run"].endswith("ladder_v3")
    assert "ladder_v3" in (docs / "NUISANCE_PROBE.md").read_text()
    update_ladder_md(written)
    ladder_md = (docs / "LADDER.md").read_text()
    assert "ladder_v3" in ladder_md
    assert "## Out-of-fold cell scores (N15)" in ladder_md


def test_publish_rejects_unevaluated(tmp_path: Path, monkeypatch):
    run_out = tmp_path / "nuisance_v3"
    run_out.mkdir()
    ladder = tmp_path / "ladder_v3"
    ladder.mkdir()
    (run_out / "nuisance_probe.json").write_text(
        json.dumps(
            {
                "n_fold_rows": 150,
                "smoke": False,
                "folds": [],
                "arm_summaries": [],
                "decision": {"r2_rejection_decision": "R2_UNEVALUATED", "labels": []},
            }
        )
    )
    import nn_v5_nuisance_probe as mod

    monkeypatch.setattr(mod, "DOCS_JSON", tmp_path / "docs" / "nuisance_probe.json")
    monkeypatch.setattr(mod, "DOCS_MD", tmp_path / "docs" / "NUISANCE_PROBE.md")
    try:
        publish(run_out, ladder)
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "R2_UNEVALUATED" in str(exc)
