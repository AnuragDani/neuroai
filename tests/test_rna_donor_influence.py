"""Post-hoc donor diagnostics: fixtures are not biological evidence."""

import json
from pathlib import Path

import pytest

from p22.eval.rna_donor_influence import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_config_refuses_model_or_gene_filter_changes(tmp_path):
    source = ROOT / "configs/rna_donor_influence.json"
    config = load_config(source)
    assert config["gene_rules"]["exclude_chr21"] is True
    assert config["gene_rules"]["expression_min_fraction_per_class"] == 0.5
    for section, field, value in [
        ("gene_rules", "exclude_chr21", False),
        ("model", "formula", "raw_counts ~ DS + PCW + female"),
        ("same_support_contract", "rho_atol", 0.1),
    ]:
        changed = json.loads(source.read_text())
        changed[section][field] = value
        path = tmp_path / "changed.json"
        path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="frozen config"):
            load_config(path)
