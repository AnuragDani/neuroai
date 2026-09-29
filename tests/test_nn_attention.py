"""Tests for N17 routing/attention tag mapping from N13 faithfulness."""

from __future__ import annotations

from scripts.describe_nn_v2_attention import tags_from_faithfulness


def test_tags_from_faithfulness_blocked_n13_all_not_shown():
    tags = tags_from_faithfulness({"status": "BLOCKED:N10_ladder_missing", "summary": []})
    assert tags == {
        "R3_gated_routing_weight": "NOT_SHOWN_USED",
        "R3_ca_attention_entropy": "NOT_SHOWN_USED",
        "R4_ca_program_module_attention": "NOT_SHOWN_USED",
    }


def test_tags_from_faithfulness_uses_mapped_interventions():
    faith = {
        "status": "DONE",
        "summary": [
            {"intervention": "I4", "arm": "R3_ca", "used_by_model": True},
            {"intervention": "I4", "arm": "R4_ca", "used_by_model": False},
            {"intervention": "I6_01", "arm": "R3_gated", "used_by_model": False},
            {"intervention": "I6_10", "arm": "R3_gated", "used_by_model": True},
            {"intervention": "I6_55", "arm": "R3_gated", "used_by_model": False},
        ],
    }
    tags = tags_from_faithfulness(faith)
    assert tags["R3_ca_attention_entropy"] == "USED_BY_MODEL"
    assert tags["R4_ca_program_module_attention"] == "NOT_SHOWN_USED"
    assert tags["R3_gated_routing_weight"] == "USED_BY_MODEL"


def test_tags_from_faithfulness_matches_accepted_n13_all_not_shown():
    """Accepted ladder_v2 N13: I4 and I6 CIs include 0 → all NOT_SHOWN_USED."""
    faith = {
        "status": "DONE",
        "summary": [
            {"intervention": "I4", "arm": "R3_ca", "used_by_model": False},
            {"intervention": "I4", "arm": "R4_ca", "used_by_model": False},
            {"intervention": "I6_01", "arm": "R3_gated", "used_by_model": False},
            {"intervention": "I6_10", "arm": "R3_gated", "used_by_model": False},
            {"intervention": "I6_55", "arm": "R3_gated", "used_by_model": False},
            {"intervention": "I1", "arm": "R3_gated", "used_by_model": True},
        ],
    }
    tags = tags_from_faithfulness(faith)
    assert set(tags.values()) == {"NOT_SHOWN_USED"}
