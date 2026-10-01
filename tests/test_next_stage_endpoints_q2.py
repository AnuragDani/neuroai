"""Q2 endpoint inventory: ENDPOINT_UNRESOLVED and identity/absence checks."""

from __future__ import annotations

import json
from pathlib import Path

import anndata as ad
import pytest

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = (
    ROOT
    / "tasks/nn/professor_direction_investigation_20260929/next_stage_20260930"
    / "endpoint_inventory.json"
)
ENDPOINTS_MD = INVENTORY.with_name("ENDPOINTS.md")
H5AD = Path("/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad")
EXPECTED_H5AD_SHA256 = "08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb"


@pytest.fixture(scope="module")
def inventory() -> dict:
    assert INVENTORY.is_file(), f"missing {INVENTORY}"
    return json.loads(INVENTORY.read_text())


def test_endpoints_md_exists() -> None:
    assert ENDPOINTS_MD.is_file()
    text = ENDPOINTS_MD.read_text()
    assert "ENDPOINT_UNRESOLVED" in text
    assert "ENDPOINT_UNRESOLVED" in text.replace("`", "")


def test_disposition_unresolved_no_pilot_endpoint(inventory: dict) -> None:
    assert inventory["disposition"] == "ENDPOINT_UNRESOLVED"
    assert inventory["selected_pilot_endpoint"] is None
    assert inventory["h5ad_sha256"] == EXPECTED_H5AD_SHA256
    for cand in inventory["candidates"]:
        assert cand.get("pilot_eligible_as_cell_state") is False
        assert cand.get("is_cell_state_endpoint") is False


def test_categories_separate_independent_covariate_proxy(inventory: dict) -> None:
    by_id = {c["candidate_id"]: c for c in inventory["candidates"]}
    assert by_id["disease_group"]["category"] == "independent_measured_outcome_specimen_level"
    assert by_id["developmental_age_PCW"]["category"] == "contextual_covariate"
    assert by_id["author_cell_type_clusters"]["category"] == "rna_derived_proxy"
    assert by_id["author_cell_type_clusters"]["overlaps_model_inputs"] is True
    assert by_id["nn_v2_oof_disease_model_scores"]["category"] == "model_derived_circular_proxy"
    assert by_id["continuous_maturation_or_pseudotime"]["category"] == "absent"


@pytest.mark.skipif(not H5AD.is_file(), reason="shared H5AD not available")
def test_live_h5ad_identity_and_no_pseudotime(inventory: dict) -> None:
    adata = ad.read_h5ad(H5AD, backed="r")
    obs = adata.obs
    assert obs.index.is_unique
    assert obs["observation_joinid"].is_unique
    assert int(obs.shape[0]) == inventory["n_obs"] == 248998
    assert inventory["identity_checks"]["obs_index_unique"] is True
    assert inventory["identity_checks"]["observation_joinid_unique"] is True

    suspect = [
        c
        for c in obs.columns
        if any(
            k in c.lower()
            for k in ("pseudo", "matur", "trajectory", "velocity", "state_score", "module")
        )
    ]
    assert suspect == []
    assert "X_umap" in adata.obsm
    # RNA modality used as NN input
    assert "assay" in adata.var.columns
    assert set(adata.var["assay"].astype(str).unique()) == {"Gene Expression"}

    # author vs cluster_name consistency
    prefix = obs["cluster_name"].astype(str).str.replace(r"_c\d+$", "", regex=True)
    assert int((prefix != obs["author_cell_type"].astype(str)).sum()) == 0
