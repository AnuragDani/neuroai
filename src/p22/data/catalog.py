"""Live CELLxGENE catalog metadata preflight (G1).

Fetches public catalog JSON only. Does not download H5AD or fragment matrices.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

DEFAULT_COLLECTION_ID = "0e9fd1d3-ef4c-47c6-a2e4-ef4bfadf7c79"
DEFAULT_DATASET_ID = "f16c25da-15bd-46a4-9a3f-17093f27a2f1"
DEFAULT_API_BASE = "https://api.cellxgene.cziscience.com/dp/v1"
EXPECTED_CELLS = 248_998
EXPECTED_DONORS = 30
EXPECTED_CONDITIONS = frozenset({"complete trisomy 21", "normal"})
EXPECTED_ASSAY = "10x multiome"
EXPECTED_DONORS_PER_CONDITION = 15
EXPECTED_H5AD_BYTES = 1_569_658_860


@dataclass(frozen=True)
class CatalogContract:
    """Frozen catalog identity expectations."""

    collection_id: str = DEFAULT_COLLECTION_ID
    dataset_id: str = DEFAULT_DATASET_ID
    expected_cells: int = EXPECTED_CELLS
    expected_donors: int = EXPECTED_DONORS
    expected_assay: str = EXPECTED_ASSAY
    expected_conditions: frozenset[str] = EXPECTED_CONDITIONS
    expected_donors_per_condition: int = EXPECTED_DONORS_PER_CONDITION
    expected_h5ad_bytes: int = EXPECTED_H5AD_BYTES
    api_base: str = DEFAULT_API_BASE


@dataclass(frozen=True)
class CatalogPreflight:
    """Live catalog comparison against the frozen contract."""

    status: str
    retrieved_at: str
    catalog_url: str
    summary: dict[str, Any] = field(default_factory=dict)
    blocking_problems: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    evidence_labels: tuple[str, ...] = ("verified",)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "retrieved_at": self.retrieved_at,
            "catalog_url": self.catalog_url,
            "summary": dict(self.summary),
            "blocking_problems": list(self.blocking_problems),
            "open_questions": list(self.open_questions),
            "evidence_labels": list(self.evidence_labels),
        }


def fetch_json(url: str, timeout: float = 60.0) -> dict[str, Any]:
    """Fetch a JSON object from a public URL."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object from {url}")
    return payload


def _labels(items: list[dict[str, Any]] | None) -> list[str]:
    if not items:
        return []
    return [str(item.get("label", item)) for item in items]


def _condition_counts_from_donor_ids(donor_ids: list[str]) -> dict[str, int]:
    return {
        "normal": sum("_CON_" in donor for donor in donor_ids),
        "complete trisomy 21": sum("_DS_" in donor for donor in donor_ids),
    }


def build_catalog_summary(
    collection: dict[str, Any],
    dataset: dict[str, Any],
    contract: CatalogContract,
) -> dict[str, Any]:
    """Normalize live catalog fields into a stable summary dict."""
    assets = list(dataset.get("dataset_assets") or [])
    h5ad_asset = next((item for item in assets if item.get("filetype") == "H5AD"), None)
    fragment_asset = next(
        (item for item in assets if item.get("filetype") == "ATAC_FRAGMENT"),
        None,
    )
    donor_ids = [str(value) for value in dataset.get("donor_id") or []]
    return {
        "collection_id": collection.get("id") or contract.collection_id,
        "collection_name": collection.get("name"),
        "dataset_id": dataset.get("id"),
        "dataset_name": dataset.get("name"),
        "assay": _labels(dataset.get("assay")),
        "cell_count": dataset.get("cell_count"),
        "donor_count": len(donor_ids),
        "donor_ids": donor_ids,
        "conditions": _labels(dataset.get("disease")),
        "condition_counts_from_donor_suffix": _condition_counts_from_donor_ids(donor_ids),
        "stage_count": len(dataset.get("development_stage") or []),
        "stages": _labels(dataset.get("development_stage")),
        "h5ad_asset": {
            "present": h5ad_asset is not None,
            "filetype": None if h5ad_asset is None else h5ad_asset.get("filetype"),
            "file_size": None if h5ad_asset is None else h5ad_asset.get("file_size"),
            "s3_uri": None if h5ad_asset is None else h5ad_asset.get("s3_uri"),
            "url": f"https://datasets.cellxgene.cziscience.com/{contract.dataset_id}.h5ad",
        },
        "atac_fragment_asset": {
            "present": fragment_asset is not None,
            "filetype": None if fragment_asset is None else fragment_asset.get("filetype"),
            "file_size": None if fragment_asset is None else fragment_asset.get("file_size"),
        },
        "same_nucleus_evidence": "unknown_until_h5ad_inspection",
        "metadata_missingness": "catalog_only",
    }


def evaluate_catalog_contract(
    summary: dict[str, Any],
    contract: CatalogContract | None = None,
) -> tuple[str, list[str], list[str]]:
    """Compare a catalog summary to the frozen contract."""
    contract = contract or CatalogContract()
    blocking: list[str] = []
    unknowns: list[str] = []

    if summary.get("dataset_id") != contract.dataset_id:
        blocking.append(
            f"dataset_id mismatch: live={summary.get('dataset_id')!r} "
            f"expected={contract.dataset_id!r}"
        )
    if summary.get("cell_count") != contract.expected_cells:
        blocking.append(
            f"cell_count mismatch: live={summary.get('cell_count')} "
            f"expected={contract.expected_cells}"
        )
    if summary.get("donor_count") != contract.expected_donors:
        blocking.append(
            f"donor_count mismatch: live={summary.get('donor_count')} "
            f"expected={contract.expected_donors}"
        )
    assays = set(summary.get("assay") or [])
    if contract.expected_assay not in assays:
        blocking.append(f"assay mismatch: live={sorted(assays)} expected={contract.expected_assay}")
    conditions = set(summary.get("conditions") or [])
    if conditions != set(contract.expected_conditions):
        blocking.append(
            f"condition mismatch: live={sorted(conditions)} "
            f"expected={sorted(contract.expected_conditions)}"
        )
    condition_counts = summary.get("condition_counts_from_donor_suffix") or {}
    for label in contract.expected_conditions:
        observed = int(condition_counts.get(label, -1))
        if observed != contract.expected_donors_per_condition:
            blocking.append(
                f"donor count for {label!r} is {observed}, "
                f"expected {contract.expected_donors_per_condition}"
            )
    if not (summary.get("h5ad_asset") or {}).get("present"):
        blocking.append("H5AD asset missing from catalog")
    if not (summary.get("atac_fragment_asset") or {}).get("present"):
        unknowns.append("ATAC fragment asset absent from catalog")
    if summary.get("same_nucleus_evidence") == "unknown_until_h5ad_inspection":
        unknowns.append("same-nucleus pairing requires H5AD inspection")

    if blocking:
        status = "BLOCKED"
    elif unknowns:
        status = "INCONCLUSIVE"
    else:
        status = "PASS"
    return status, blocking, unknowns


def run_catalog_preflight(
    contract: CatalogContract | None = None,
    fetcher: Any | None = None,
) -> CatalogPreflight:
    """Fetch live catalog metadata and evaluate the frozen identity contract."""
    contract = contract or CatalogContract()
    catalog_url = f"{contract.api_base}/collections/{contract.collection_id}"
    retrieved_at = datetime.now(UTC).isoformat(timespec="seconds")
    get_json = fetcher or fetch_json
    try:
        collection = get_json(catalog_url)
        dataset = next(item for item in collection["datasets"] if item["id"] == contract.dataset_id)
    except (
        StopIteration,
        KeyError,
        TypeError,
        urllib.error.URLError,
        TimeoutError,
        ValueError,
    ) as error:
        return CatalogPreflight(
            status="BLOCKED",
            retrieved_at=retrieved_at,
            catalog_url=catalog_url,
            summary={},
            blocking_problems=(f"catalog fetch failed: {error}",),
            open_questions=(),
            evidence_labels=("unknown",),
        )

    summary = build_catalog_summary(collection, dataset, contract)
    status, blocking, unknowns = evaluate_catalog_contract(summary, contract)
    return CatalogPreflight(
        status=status,
        retrieved_at=retrieved_at,
        catalog_url=catalog_url,
        summary=summary,
        blocking_problems=tuple(blocking),
        open_questions=tuple(unknowns),
        evidence_labels=("verified",) if status != "BLOCKED" else ("unknown",),
    )
