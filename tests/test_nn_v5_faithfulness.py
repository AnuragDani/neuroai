"""P1/N13: faithfulness_v3 wrapper resolves canonical ladder and rewrites PC wording."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_faithfulness import (
    assert_ladder_has_models,
    publish,
    resolve_canonical_ladder,
    rewrite_markdown,
    rewrite_pc_reason,
    update_ladder_md,
)

ROOT = Path(__file__).parents[1]


def test_resolve_canonical_ladder_points_at_ladder_v3():
    ladder = resolve_canonical_ladder()
    assert ladder.name == "ladder_v3"
    assert (ladder / "folds").is_dir()
    assert (ladder / "models").is_dir()


def test_assert_ladder_has_models_on_canonical():
    info = assert_ladder_has_models(resolve_canonical_ladder())
    assert info["n_models_per_arm"] == 25
    assert "R3_ca" in info["arms"]


def test_rewrite_pc_reason_uses_ladder_name():
    payload = {
        "decision": {
            "tags": ["CA_PAIRING_UNUSED"],
            "nc_exact_zero": True,
            "pc_status": "N/A",
            "pc_reason": "No saved planted S4/S5 δ=1.0 fold models under ladder_v2; x",
        },
        "source_run": "/old/ladder_v2",
    }
    out = rewrite_pc_reason(payload, Path("/tmp/ladder_v3"))
    assert "ladder_v3" in out["decision"]["pc_reason"]
    assert "ladder_v2" not in out["decision"]["pc_reason"]
    assert out["source_run"].endswith("ladder_v3")


def test_publish_and_ladder_md(tmp_path: Path, monkeypatch):
    run_out = tmp_path / "faithfulness_v3"
    run_out.mkdir()
    ladder = tmp_path / "ladder_v3"
    ladder.mkdir()
    payload = {
        "task": "N13",
        "status": "DONE",
        "source_run": str(ladder),
        "decision": {
            "tags": ["CA_PAIRING_UNUSED", "ATAC_USED"],
            "nc_exact_zero": True,
            "pc_status": "N/A",
            "pc_reason": "No saved planted S4/S5 δ=1.0 fold models under ladder_v2; x",
        },
        "summary": [],
    }
    (run_out / "faithfulness.json").write_text(json.dumps(payload))
    (run_out / "FAITHFULNESS.md").write_text(
        "# Faithfulness interventions (N13)\n\n"
        "Source models: `/old/ladder_v2` (accepted ladder_v2; not copied into finish-base).\n\n"
        "**NC exact zero:** `True`.\n"
        "**Decision tags:** CA_PAIRING_UNUSED, ATAC_USED.\n"
        "**PC:** N/A — old\n"
    )
    docs = tmp_path / "docs" / "nn_v2"
    docs.mkdir(parents=True)
    import nn_v5_faithfulness as mod

    monkeypatch.setattr(mod, "DOCS_JSON", docs / "faithfulness.json")
    monkeypatch.setattr(mod, "DOCS_MD", docs / "FAITHFULNESS.md")
    monkeypatch.setattr(mod, "LADDER_MD", docs / "LADDER.md")
    (docs / "LADDER.md").write_text(
        "## Faithfulness interventions (N13)\n\nold text\n\n"
        "## Nuisance-probe diagnostics (N14)\n\nx\n"
    )
    result = publish(run_out, ladder)
    assert result["nc"] is True
    assert "ladder_v3" in result["source_run"]
    written = json.loads((docs / "faithfulness.json").read_text())
    assert "ladder_v3" in written["decision"]["pc_reason"]
    md = (docs / "FAITHFULNESS.md").read_text()
    assert "ladder_v3" in md
    assert "ladder_v2" not in md.split("Source models:")[1].split("\n")[0]
    update_ladder_md(written)
    ladder_md = (docs / "LADDER.md").read_text()
    assert "ladder_v3" in ladder_md
    assert "## Nuisance-probe diagnostics (N14)" in ladder_md


def test_rewrite_markdown_syncs_tags():
    payload = {
        "decision": {
            "tags": ["ATAC_USED"],
            "nc_exact_zero": True,
            "pc_status": "N/A",
            "pc_reason": "reason under ladder_v3",
        }
    }
    md = (
        "# Faithfulness interventions (N13)\n\n"
        "Source models: `/old` (accepted ladder_v2; not copied into finish-base).\n\n"
        "**NC exact zero:** `False`.\n"
        "**Decision tags:** OLD.\n"
        "**PC:** N/A — old\n"
    )
    out = rewrite_markdown(md, Path("/x/ladder_v3"), payload)
    assert "ATAC_USED" in out
    assert "`True`" in out
    assert "reason under ladder_v3" in out
