"""P1/N17: routing_v3 wrapper resolves canonical ladder and publishes docs."""

from __future__ import annotations

import json
from pathlib import Path

from nn_v5_routing import (
    assert_faithfulness_binds_ladder,
    assert_ladder_has_models,
    publish,
    resolve_canonical_ladder,
    rewrite_markdown,
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
    assert set(info["arms"]) == {"R3_gated", "R3_ca", "R4_ca"}


def test_assert_faithfulness_binds_ladder_v3():
    ladder = resolve_canonical_ladder()
    payload = assert_faithfulness_binds_ladder(ladder)
    assert payload["status"] == "DONE"
    assert Path(payload["source_run"]).resolve() == ladder.resolve()


def test_publish_and_ladder_md(tmp_path: Path, monkeypatch):
    run_out = tmp_path / "routing_v3"
    run_out.mkdir()
    ladder = tmp_path / "ladder_v3"
    ladder.mkdir()
    payload = {
        "task": "N17",
        "status": "DONE",
        "source_run": str(ladder),
        "smoke": False,
        "folds_used": 75,
        "readout_tags": {
            "R3_gated_routing_weight": "NOT_SHOWN_USED",
            "R3_ca_attention_entropy": "NOT_SHOWN_USED",
            "R4_ca_program_module_attention": "NOT_SHOWN_USED",
        },
        "cell_types": [],
    }
    (run_out / "routing_attention.json").write_text(json.dumps(payload))
    (run_out / "ROUTING_ATTENTION.md").write_text(
        "# Routing and attention (N17)\n\n"
        "Source models: `/old/ladder_v2` (accepted ladder_v2; not copied into finish-base).\n\n"
        "Descriptive only.\n"
    )
    docs = tmp_path / "docs" / "nn_v2"
    docs.mkdir(parents=True)
    import nn_v5_routing as mod

    monkeypatch.setattr(mod, "DOCS_JSON", docs / "routing_attention.json")
    monkeypatch.setattr(mod, "DOCS_MD", docs / "ROUTING_ATTENTION.md")
    monkeypatch.setattr(mod, "LADDER_MD", docs / "LADDER.md")
    (docs / "LADDER.md").write_text(
        "## Routing / attention (N17)\n\nold ladder_v2 text\n\n"
        "## Gene-activity secondary ladder (N21)\n\nx\n"
    )
    result = publish(run_out, ladder)
    assert result["folds_used"] == 75
    assert "ladder_v3" in result["source_run"]
    md = (docs / "ROUTING_ATTENTION.md").read_text()
    assert "ladder_v3" in md
    assert "canonical ladder_v3" in md
    update_ladder_md(json.loads((docs / "routing_attention.json").read_text()))
    ladder_md = (docs / "LADDER.md").read_text()
    assert "ladder_v3" in ladder_md
    assert "NOT_SHOWN_USED" in ladder_md
    assert "## Gene-activity secondary ladder (N21)" in ladder_md


def test_rewrite_markdown_uses_ladder_name():
    md = (
        "# Routing and attention (N17)\n\n"
        "Source models: `/old/ladder_v2` (accepted ladder_v2; not copied into finish-base).\n\n"
        "x\n"
    )
    out = rewrite_markdown(md, Path("/tmp/ladder_v3"))
    assert "canonical ladder_v3" in out
    assert "ladder_v2" not in out.split("Source models:")[1].split("\n")[0]
