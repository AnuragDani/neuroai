"""M9 real-data pilot fit path for the masked ATAC computational pilot.

New module deliberately outside M8 ``REQUIRED_LOCK_KEYS`` so live protocol /
executor digests stay authorized. Builds chromosome-masked fold features from
frozen M3 manifests, implements ``fit_fn`` via the M7 adapter, and dispatches
serial jobs through the M8-gated reserve/skip path without mutating locked
source files.

Resume after a progressed attempt counter cannot re-enter
``run_authorized_pilot`` (counter digest is locked at zero); use
``authorize_immutable_lock`` + ``execute_jobs_serial`` instead.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import torch
from scipy import sparse

from p22.data.transforms import fit_train_only
from p22.eval.execution_repair_provenance import (
    DEFAULT_ATAC_REL,
    DEFAULT_H5AD_REL,
    EXPECTED_MATRIX_SHA256,
    EXPECTED_ORDERED_CELLS_SHA256,
    EXPECTED_UNION_BED_SHA256,
    default_atac_path,
    default_h5ad_path,
    resolve_portable_path,
)
from p22.eval.execution_repair_runtime_mask import (
    enforce_runtime_feature_mask,
    load_union_bed_chroms,
)
from p22.eval.masked_atac_adapter import (
    ARM_TO_PAIRED_NAME,
    LOGREG_ARMS,
    NEURAL_ARMS,
    fit_constant_prevalence,
    fit_logreg_cell_target,
    fit_neural_cell_target,
)
from p22.eval.masked_atac_execute import (
    ALLOWED_RAW_ROOT,
    COUNTER_NAME,
    REQUIRED_LOCK_KEYS,
    MaskedAtacExecuteRefusal,
    execute_jobs_serial,
    job_fit_id,
    load_attempt_counter,
    prepare_raw_root,
    refuse_if_not_allowed_raw_root,
    resolve_lock_artifact_path,
    review_lock_path,
    verify_reviewed_hashes,
)
from p22.eval.masked_atac_metrics import (
    assert_no_forbidden_features,
    binary_presence_labels,
    donor_average_cell_log_loss,
    sha256_array,
    sha256_lines,
    visible_atac_tfidf_fit,
)
from p22.eval.masked_atac_protocol import (
    CLAIM_LEVEL,
    CONSTANT_ARM,
    LEARNED_ARMS,
    NEURAL,
    PRESERVED_LABELS,
    PROTOCOL_ID,
    TORCH_THREADS,
    WORKERS,
    enumerate_planned_jobs,
)
from p22.eval.multiome_runner import model_inputs
from p22.eval.s7_ledger import sha256_file
from p22.models.fusion import VIEW_A, VIEW_B
from p22.training.loop import predict as predict_fn

STAGE_DIR_REL = (
    "tasks/nn/professor_direction_investigation_20260929/"
    "masked_atac_pilot_20261001"
)
# Backward-compatible aliases; prefer workspace-relative defaults via
# default_h5ad_path / default_atac_path (E0 portable provenance).
DEFAULT_H5AD = Path(DEFAULT_H5AD_REL)
DEFAULT_ATAC = Path(DEFAULT_ATAC_REL)
IMMUTABLE_LOCK_KEYS = tuple(
    k for k in REQUIRED_LOCK_KEYS if not k.endswith(COUNTER_NAME)
)


class MaskedAtacPilotError(ValueError):
    """Refuse unsafe M9 real-data construction or dispatch."""


@dataclass
class FoldFeatureBundle:
    """Per-fold encoded inputs shared across all arms."""

    fold: int
    cell_ids: list[str]
    donors: np.ndarray
    labels: np.ndarray
    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray
    rna: np.ndarray
    atac: np.ndarray
    target_index: int
    target_label: str
    visible_indices: list[int]
    rna_selected_features: list[int]
    rna_encoded_sha256: str
    atac_encoded_sha256: str
    labels_sha256: str
    cell_ids_sha256: str

    @property
    def n_visible(self) -> int:
        return int(self.atac.shape[1])

    def views(self) -> dict[str, np.ndarray]:
        return {VIEW_A: self.rna.astype(np.float64), VIEW_B: self.atac.astype(np.float64)}


@dataclass
class PilotArrays:
    """Matched sampled-cell RNA/ATAC tensors pinned to M3 cell order."""

    cell_ids: list[str]
    donors: np.ndarray
    rna_counts: Any  # sparse or ndarray cells × genes
    atac_counts: np.ndarray  # cells × regions dense float64
    h5ad_path: str
    atac_path: str
    matrix_sha256: str
    ordered_full_cells_sha256: str
    sampling_cell_ids_sha256: str
    region_chroms: list[str]
    union_bed_path: str
    union_bed_sha256: str


def _stage_dir(workspace: Path) -> Path:
    return Path(workspace) / STAGE_DIR_REL


def load_splits_manifest(workspace: Path) -> dict[str, Any]:
    path = _stage_dir(workspace) / "SPLITS_AND_SAMPLING.json"
    if not path.is_file():
        raise MaskedAtacPilotError(f"missing frozen splits: {path}")
    blob = json.loads(path.read_text(encoding="utf-8"))
    if blob.get("disposition") != "SPLITS_AND_SAMPLING_FROZEN":
        raise MaskedAtacPilotError(
            f"unexpected splits disposition {blob.get('disposition')!r}"
        )
    return blob


def authorize_immutable_lock(
    *,
    workspace: Path,
    m8_lock_path: Path | None = None,
    allow_progressed_counter: bool = False,
) -> dict[str, Any]:
    """Authorize fits without requiring the zeroed counter digest after progress.

    First entry (counters still zero) uses full ``verify_reviewed_hashes``.
    Resume after reserved attempts verifies only immutable ``REQUIRED_LOCK_KEYS``
    (excludes attempt_counter) and refuses counter reset.
    """
    workspace = Path(workspace)
    lock = Path(m8_lock_path) if m8_lock_path is not None else review_lock_path(workspace)
    review = workspace / (
        "tasks/nn/professor_direction_investigation_20260929/"
        "masked_atac_pilot_20261001/NO_FIT_REVIEW_M8.json"
    )
    if not review.is_file():
        raise MaskedAtacExecuteRefusal(f"missing M8 review record: {review}")
    review_blob = json.loads(review.read_text(encoding="utf-8"))
    if review_blob.get("verdict") != "PASS" or not review_blob.get("fits_authorized"):
        raise MaskedAtacExecuteRefusal("M8 PASS with fits_authorized required")

    raw_root = prepare_raw_root(workspace / ALLOWED_RAW_ROOT)
    counter_path = raw_root / COUNTER_NAME
    counter = load_attempt_counter(counter_path)
    used = int(counter["total_attempts"]["used"])

    if used == 0:
        live = verify_reviewed_hashes(workspace=workspace, lock_path=lock)
        return {
            "mode": "full_lock_including_zero_counter",
            "reviewed_hashes": live,
            "counter": counter,
            "raw_root": str(raw_root),
        }

    if not allow_progressed_counter:
        raise MaskedAtacExecuteRefusal(
            "attempt counter already progressed; re-call with "
            "allow_progressed_counter=True for durable resume "
            "(counter digest is locked at zero and cannot rematch)"
        )

    blob = json.loads(lock.read_text(encoding="utf-8"))
    expected = blob.get("reviewed_hashes") or {}
    live: dict[str, str] = {}
    for key in IMMUTABLE_LOCK_KEYS:
        path = resolve_lock_artifact_path(workspace, key)
        if not path.is_file():
            raise MaskedAtacExecuteRefusal(f"missing reviewed artifact {key}: {path}")
        actual = sha256_file(path)
        live[key] = actual
        want = str(expected.get(key, "") or "")
        if actual != want:
            raise MaskedAtacExecuteRefusal(
                f"M8 immutable hash mismatch for {key}: expected {want} got {actual}"
            )
    if int(counter["total_attempts"]["used"]) < 1:
        raise MaskedAtacExecuteRefusal("progressed-counter mode requires used>=1")
    return {
        "mode": "immutable_lock_progressed_counter",
        "reviewed_hashes": live,
        "counter": counter,
        "raw_root": str(raw_root),
        "note": (
            "attempt_counter excluded from live rematch after first reservation; "
            "never reset; skip completed fit_ids"
        ),
    }


def load_pilot_arrays(
    *,
    workspace: Path,
    h5ad: Path | None = None,
    atac_npz: Path | None = None,
) -> PilotArrays:
    """Load matched sampled-cell RNA/ATAC tensors under frozen M3 cell order."""
    splits = load_splits_manifest(workspace)
    sample_ids = [str(x) for x in splits["sampling_cell_ids_sorted"]]
    if len(sample_ids) != 7680:
        raise MaskedAtacPilotError(f"expected 7680 sampled cells; got {len(sample_ids)}")
    sample_sha = sha256_lines(sample_ids)
    if sample_sha != splits["sampling"]["cell_ids_sha256"]:
        raise MaskedAtacPilotError("sampling_cell_ids_sorted hash mismatch vs M3")

    h5ad_path = Path(h5ad) if h5ad is not None else default_h5ad_path(workspace)
    atac_path = (
        Path(atac_npz) if atac_npz is not None else default_atac_path(workspace)
    )
    if not h5ad_path.is_file() and not h5ad_path.is_absolute():
        h5ad_path = (Path(workspace) / h5ad_path).resolve()
    if not atac_path.is_file() and not atac_path.is_absolute():
        atac_path = (Path(workspace) / atac_path).resolve()
    for path in (h5ad_path, atac_path):
        if not path.is_file():
            raise MaskedAtacPilotError(f"missing required input: {path}")

    matrix_sha = sha256_file(atac_path)
    if matrix_sha != EXPECTED_MATRIX_SHA256:
        raise MaskedAtacPilotError(
            f"ATAC matrix hash mismatch: {matrix_sha} != {EXPECTED_MATRIX_SHA256}"
        )

    bed_path = resolve_portable_path(workspace, "union_bed")
    if not bed_path.is_file():
        raise MaskedAtacPilotError(f"missing required input: {bed_path}")
    bed_sha = sha256_file(bed_path)
    if bed_sha != EXPECTED_UNION_BED_SHA256:
        raise MaskedAtacPilotError(
            f"union BED hash mismatch: {bed_sha} != {EXPECTED_UNION_BED_SHA256}"
        )
    region_chroms = load_union_bed_chroms(bed_path)
    if len(region_chroms) != 465:
        raise MaskedAtacPilotError(
            f"unexpected union BED region count {len(region_chroms)}"
        )

    # Full in-memory load: backed CSR fancy-index is broken under this
    # anndata/scipy pair (``_validate_indices`` AttributeError). File is
    # ~1.5 GiB on disk; 128 GiB host RAM makes a one-shot load safer than a
    # custom h5py row gather for this bounded pilot.
    adata = ad.read_h5ad(h5ad_path)
    full_cell_ids = adata.obs_names.astype(str).to_numpy()
    ordered_sha = sha256_lines(full_cell_ids.tolist())
    if ordered_sha != EXPECTED_ORDERED_CELLS_SHA256:
        raise MaskedAtacPilotError("ordered full-cell hash mismatch vs M1 contract")
    cell_to_row = {cid: i for i, cid in enumerate(full_cell_ids.tolist())}
    try:
        sample_rows = np.asarray([cell_to_row[c] for c in sample_ids], dtype=np.int64)
    except KeyError as exc:
        raise MaskedAtacPilotError(f"sampled cell missing from H5AD: {exc}") from exc

    donors_full = adata.obs["donor_id"].astype(str).to_numpy()
    donors = donors_full[sample_rows]
    rna = adata.X[sample_rows]
    if sparse.issparse(rna):
        rna_counts = rna.tocsr()
    else:
        rna_counts = sparse.csr_matrix(np.asarray(rna, dtype=np.float64))
    del adata

    mat = sparse.load_npz(atac_path)
    if mat.shape != (465, 248998):
        raise MaskedAtacPilotError(f"unexpected ATAC shape {mat.shape}")
    atac_sample = mat[:, sample_rows].T.tocsr()
    atac_dense = np.asarray(atac_sample.toarray(), dtype=np.float64)

    return PilotArrays(
        cell_ids=sample_ids,
        donors=np.asarray(donors, dtype=str),
        rna_counts=rna_counts,
        atac_counts=atac_dense,
        h5ad_path=str(h5ad_path),
        atac_path=str(atac_path),
        matrix_sha256=matrix_sha,
        ordered_full_cells_sha256=ordered_sha,
        sampling_cell_ids_sha256=sample_sha,
        region_chroms=list(region_chroms),
        union_bed_path=str(bed_path),
        union_bed_sha256=bed_sha,
    )


def _index_map(cell_ids: Sequence[str]) -> dict[str, int]:
    return {str(c): i for i, c in enumerate(cell_ids)}


def _rows_for(wanted: Sequence[str], index: Mapping[str, int]) -> np.ndarray:
    try:
        return np.asarray([index[str(c)] for c in wanted], dtype=np.int64)
    except KeyError as exc:
        raise MaskedAtacPilotError(f"fold cell not in sampled set: {exc}") from exc


def build_fold_features(
    arrays: PilotArrays,
    fold_blob: Mapping[str, Any],
    *,
    feature_budget: int = NEURAL.feature_budget,
    region_chroms: Sequence[str] | None = None,
) -> FoldFeatureBundle:
    """Train-only RNA variance+scale and visible-only ATAC TF-IDF(+scale).

    Runtime E1 mask: every visible ATAC column must exclude the target index and
    the whole target chromosome; panel depth uses visible columns only.
    """
    fold_i = int(fold_blob["fold"])
    target = fold_blob["target"]
    target_index = int(target["region_index"])
    target_chrom = str(target["chrom"])
    visible = [int(i) for i in fold_blob["visible_atac"]["visible_region_indices"]]
    chroms = (
        [str(c) for c in region_chroms]
        if region_chroms is not None
        else [str(c) for c in getattr(arrays, "region_chroms", [])]
    )
    if not chroms:
        raise MaskedAtacPilotError(
            f"fold {fold_i}: region_chroms required for runtime chromosome mask"
        )
    try:
        enforce_runtime_feature_mask(
            region_chroms=chroms,
            visible_indices=visible,
            target_index=target_index,
            target_chrom=target_chrom,
        )
    except ValueError as exc:
        raise MaskedAtacPilotError(f"fold {fold_i}: {exc}") from exc
    got_vis_sha = sha256_lines([str(i) for i in visible])
    want_vis_sha = fold_blob["visible_atac"]["visible_region_indices_sha256"]
    if got_vis_sha != want_vis_sha:
        raise MaskedAtacPilotError(f"fold {fold_i}: visible index hash mismatch")

    index = _index_map(arrays.cell_ids)
    cells = fold_blob["cells"]
    train_idx = _rows_for(cells["inner_train_cell_ids"], index)
    val_idx = _rows_for(cells["inner_val_cell_ids"], index)
    test_idx = _rows_for(cells["outer_test_cell_ids"], index)
    if len(train_idx) + len(val_idx) + len(test_idx) != len(arrays.cell_ids):
        raise MaskedAtacPilotError(f"fold {fold_i}: split sizes do not cover sample")
    if len(set(train_idx.tolist()) | set(val_idx.tolist()) | set(test_idx.tolist())) != len(
        arrays.cell_ids
    ):
        raise MaskedAtacPilotError(f"fold {fold_i}: split rows not a partition")

    labels = binary_presence_labels(arrays.atac_counts[:, target_index])
    train_mask = np.zeros(len(arrays.cell_ids), dtype=bool)
    train_mask[train_idx] = True

    # RNA: train-only top-variance then StandardScaler (fit_train_only).
    rna = arrays.rna_counts
    train_rna = rna[train_idx]
    if sparse.issparse(train_rna):
        mean = np.asarray(train_rna.mean(axis=0)).ravel()
        second = np.asarray(train_rna.power(2).mean(axis=0)).ravel()
        variance = second - np.square(mean)
    else:
        variance = np.asarray(train_rna, dtype=np.float64).var(axis=0)
    selected = np.sort(np.argsort(-variance, kind="stable")[: int(feature_budget)])
    rna_chosen = rna[:, selected]
    rna_dense = (
        rna_chosen.toarray().astype(np.float64)
        if sparse.issparse(rna_chosen)
        else np.asarray(rna_chosen, dtype=np.float64)
    )
    cell_ids = np.asarray(arrays.cell_ids, dtype=object)
    holdout_ids = cell_ids[np.concatenate([val_idx, test_idx])]
    rna_fit = fit_train_only(
        rna_dense,
        cell_ids,
        cell_ids[train_idx],
        holdout_ids,
    )
    rna_encoded = np.asarray(rna_fit.transform(rna_dense), dtype=np.float64)

    # ATAC: visible-only TF-IDF (train IDF / visible depth), then train-only scale.
    # Target-inclusive panel depth is refused by the runtime mask above.
    tfidf = visible_atac_tfidf_fit(arrays.atac_counts, visible, train_mask)
    if int(tfidf["n_visible"]) != len(visible):
        raise MaskedAtacPilotError(f"fold {fold_i}: visible TF-IDF width mismatch")
    atac_raw = np.asarray(tfidf["encoded"], dtype=np.float64)
    atac_fit = fit_train_only(
        atac_raw,
        cell_ids,
        cell_ids[train_idx],
        holdout_ids,
    )
    atac_encoded = np.asarray(atac_fit.transform(atac_raw), dtype=np.float64)

    feature_names = (
        [f"rna_var_{int(i)}" for i in selected.tolist()]
        + [f"visible_atac_{int(i)}" for i in visible]
    )
    forbidden = assert_no_forbidden_features(feature_names)
    if forbidden:
        raise MaskedAtacPilotError(f"forbidden feature names: {forbidden}")

    return FoldFeatureBundle(
        fold=fold_i,
        cell_ids=list(arrays.cell_ids),
        donors=np.asarray(arrays.donors, dtype=str),
        labels=labels.astype(np.int64),
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
        rna=rna_encoded,
        atac=atac_encoded,
        target_index=target_index,
        target_label=str(target["region_label"]),
        visible_indices=visible,
        rna_selected_features=[int(i) for i in selected.tolist()],
        rna_encoded_sha256=sha256_array(rna_encoded),
        atac_encoded_sha256=sha256_array(atac_encoded),
        labels_sha256=sha256_array(labels.astype(np.float64)),
        cell_ids_sha256=sha256_lines(list(arrays.cell_ids)),
    )


def build_all_fold_features(
    arrays: PilotArrays,
    splits: Mapping[str, Any],
    *,
    region_chroms: Sequence[str] | None = None,
) -> dict[int, FoldFeatureBundle]:
    chroms = (
        [str(c) for c in region_chroms]
        if region_chroms is not None
        else [str(c) for c in getattr(arrays, "region_chroms", [])]
    )
    if not chroms:
        raise MaskedAtacPilotError(
            "region_chroms required for runtime chromosome mask"
        )
    out: dict[int, FoldFeatureBundle] = {}
    for fold_blob in splits["folds"]:
        bundle = build_fold_features(arrays, fold_blob, region_chroms=chroms)
        out[int(bundle.fold)] = bundle
    if sorted(out) != [0, 1, 2, 3, 4]:
        raise MaskedAtacPilotError(f"expected folds 0..4; got {sorted(out)}")
    # Matched cells across folds/arms: same global sample order.
    cell_hashes = {b.cell_ids_sha256 for b in out.values()}
    if len(cell_hashes) != 1:
        raise MaskedAtacPilotError("cell ID order diverged across folds")
    return out


def _jsonable_probs(values: np.ndarray) -> list[float]:
    return [float(x) for x in np.asarray(values, dtype=np.float64).tolist()]


def fit_one_job(
    job: Mapping[str, Any],
    folds: Mapping[int, FoldFeatureBundle],
) -> dict[str, Any]:
    """Fit one smoke/main learned arm on a frozen fold feature bundle."""
    stage = str(job["stage"])
    arm = str(job["arm"])
    fold_i = int(job["fold"])
    if arm == CONSTANT_ARM:
        raise MaskedAtacPilotError(
            "constant arm has zero fits; evaluate at summary time only"
        )
    if arm not in LEARNED_ARMS:
        raise MaskedAtacPilotError(f"unknown learned arm {arm!r}")
    bundle = folds[fold_i]
    train = bundle.train_idx
    val = bundle.val_idx
    test = bundle.test_idx
    donors = bundle.donors
    labels = bundle.labels

    if arm in LOGREG_ARMS:
        features = bundle.rna if arm == "logreg_rna" else bundle.atac
        # Predict on all sampled cells so train/val/test metrics can be replayed.
        predict_idx = np.arange(len(bundle.cell_ids), dtype=np.int64)
        fitted = fit_logreg_cell_target(
            features,
            labels,
            donors,
            train,
            predict_idx,
        )
        probs = np.asarray(fitted["probabilities"], dtype=np.float64)
        train_loss = donor_average_cell_log_loss(
            donors[train], labels[train], probs[train]
        )["value"]
        val_loss = donor_average_cell_log_loss(
            donors[val], labels[val], probs[val]
        )["value"]
        test_loss = donor_average_cell_log_loss(
            donors[test], labels[test], probs[test]
        )["value"]
        return {
            "fit_id": job_fit_id(job),
            "stage": stage,
            "arm": arm,
            "fold": fold_i,
            "kind": "logreg",
            "target_label": bundle.target_label,
            "target_index": bundle.target_index,
            "n_visible_atac": bundle.n_visible,
            "rna_width": int(bundle.rna.shape[1]),
            "atac_width": int(bundle.atac.shape[1]),
            "cell_ids_sha256": bundle.cell_ids_sha256,
            "labels_sha256": bundle.labels_sha256,
            "rna_encoded_sha256": bundle.rna_encoded_sha256,
            "atac_encoded_sha256": bundle.atac_encoded_sha256,
            "train_donor_average_cell_log_loss": float(train_loss),
            "val_donor_average_cell_log_loss": float(val_loss),
            "test_donor_average_cell_log_loss": float(test_loss),
            "test_cell_ids": [bundle.cell_ids[i] for i in test.tolist()],
            "test_donors": donors[test].tolist(),
            "test_labels": labels[test].astype(int).tolist(),
            "test_probabilities": _jsonable_probs(probs[test]),
            "all_probabilities": _jsonable_probs(probs),
            "coef": fitted.get("coef"),
            "intercept": fitted.get("intercept"),
            "settings": fitted.get("settings"),
            "claim_level": CLAIM_LEVEL,
            "protocol_id": PROTOCOL_ID,
            "preserved_labels": dict(PRESERVED_LABELS),
        }

    if arm not in NEURAL_ARMS:
        raise MaskedAtacPilotError(f"arm {arm!r} not wired")

    torch.set_num_threads(int(TORCH_THREADS))
    views = bundle.views()
    fitted = fit_neural_cell_target(
        arm,
        views,
        labels,
        donors,
        train,
        val,
        test,
        protocol=NEURAL,
    )
    model = fitted.pop("model")
    result_dict = fitted["result"]
    selected = model_inputs(ARM_TO_PAIRED_NAME[arm], dict(views))
    _, p_train = predict_fn(model, {k: v[train] for k, v in selected.items()})
    test_probs = np.asarray(fitted["probabilities"], dtype=np.float64)
    train_probs = p_train[:, 1].astype(np.float64)
    return {
        "fit_id": job_fit_id(job),
        "stage": stage,
        "arm": arm,
        "fold": fold_i,
        "kind": "neural",
        "paired_name": fitted["paired_name"],
        "widths": fitted["widths"],
        "target_label": bundle.target_label,
        "target_index": bundle.target_index,
        "n_visible_atac": bundle.n_visible,
        "rna_width": int(bundle.rna.shape[1]),
        "atac_width": int(bundle.atac.shape[1]),
        "cell_ids_sha256": bundle.cell_ids_sha256,
        "labels_sha256": bundle.labels_sha256,
        "rna_encoded_sha256": bundle.rna_encoded_sha256,
        "atac_encoded_sha256": bundle.atac_encoded_sha256,
        "train_donor_average_cell_log_loss": float(
            donor_average_cell_log_loss(donors[train], labels[train], train_probs)[
                "value"
            ]
        ),
        "val_donor_average_cell_log_loss": float(
            result_dict["val_donor_average_cell_log_loss"]
        ),
        "test_donor_average_cell_log_loss": float(
            donor_average_cell_log_loss(donors[test], labels[test], test_probs)["value"]
        ),
        "initial_state_sha256": result_dict["initial_state_sha256"],
        "checkpoint_sha256": result_dict["checkpoint_sha256"],
        "selection_metric": result_dict["selection_metric"],
        "training": result_dict["training"],
        "test_cell_ids": [bundle.cell_ids[i] for i in test.tolist()],
        "test_donors": donors[test].tolist(),
        "test_labels": labels[test].astype(int).tolist(),
        "test_probabilities": _jsonable_probs(test_probs),
        "claim_level": CLAIM_LEVEL,
        "protocol_id": PROTOCOL_ID,
        "preserved_labels": dict(PRESERVED_LABELS),
    }


def filter_jobs(
    *,
    stages: Sequence[str] | None = None,
    folds: Sequence[int] | None = None,
    arms: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    jobs = enumerate_planned_jobs()
    if stages is not None:
        allowed = set(stages)
        jobs = [j for j in jobs if j["stage"] in allowed]
    if folds is not None:
        allowed_f = {int(x) for x in folds}
        jobs = [j for j in jobs if int(j["fold"]) in allowed_f]
    if arms is not None:
        allowed_a = set(arms)
        jobs = [j for j in jobs if j["arm"] in allowed_a]
    return jobs


def evaluate_constant_arm(bundle: FoldFeatureBundle) -> dict[str, Any]:
    """Zero-fit training-prevalence constant on one fold (not an attempt)."""
    train = bundle.train_idx
    test = bundle.test_idx
    const = fit_constant_prevalence(bundle.labels[train], n_predict=len(test))
    probs = np.asarray(const["probabilities"], dtype=np.float64)
    return {
        "arm": CONSTANT_ARM,
        "fold": bundle.fold,
        "fits_count": 0,
        "prevalence": const["prevalence"],
        "test_donor_average_cell_log_loss": float(
            donor_average_cell_log_loss(
                bundle.donors[test], bundle.labels[test], probs
            )["value"]
        ),
        "test_probabilities": _jsonable_probs(probs),
        "test_cell_ids": [bundle.cell_ids[i] for i in test.tolist()],
        "test_donors": bundle.donors[test].tolist(),
        "test_labels": bundle.labels[test].astype(int).tolist(),
        "cell_ids_sha256": bundle.cell_ids_sha256,
        "labels_sha256": bundle.labels_sha256,
    }


def run_m9_jobs(
    *,
    workspace: Path,
    stages: Sequence[str] = ("smoke",),
    h5ad: Path | None = None,
    atac_npz: Path | None = None,
    allow_progressed_counter: bool = False,
) -> dict[str, Any]:
    """Authorize, build fold features once, and serially dispatch filtered jobs."""
    workspace = Path(workspace)
    if WORKERS != 1:
        raise MaskedAtacPilotError("WORKERS must be 1")
    auth = authorize_immutable_lock(
        workspace=workspace,
        allow_progressed_counter=allow_progressed_counter,
    )
    raw_root = Path(auth["raw_root"])
    refuse_if_not_allowed_raw_root(raw_root)
    counter_path = raw_root / COUNTER_NAME

    splits = load_splits_manifest(workspace)
    started_load = time.perf_counter()
    arrays = load_pilot_arrays(workspace=workspace, h5ad=h5ad, atac_npz=atac_npz)
    folds = build_all_fold_features(arrays, splits)
    load_seconds = float(time.perf_counter() - started_load)

    # Equality pins across folds (same cells / donors order).
    donor_sha = sha256_lines(arrays.donors.tolist())
    for bundle in folds.values():
        if bundle.cell_ids_sha256 != arrays.sampling_cell_ids_sha256:
            raise MaskedAtacPilotError("fold cell hash != sampling hash")
        if sha256_lines(bundle.donors.tolist()) != donor_sha:
            raise MaskedAtacPilotError("donor order diverged")

    jobs = filter_jobs(stages=stages)
    if not jobs:
        raise MaskedAtacPilotError(f"no jobs for stages={list(stages)!r}")

    def _fit_fn(job: Mapping[str, Any]) -> dict[str, Any]:
        return fit_one_job(job, folds)

    torch.set_num_threads(int(TORCH_THREADS))
    exec_summary = execute_jobs_serial(
        jobs,
        raw_root=raw_root,
        counter_path=counter_path,
        fit_fn=_fit_fn,
    )

    # Constant arm descriptive (0 fits) for folds touched by this call.
    touched_folds = sorted({int(j["fold"]) for j in jobs})
    constants = {
        str(f): evaluate_constant_arm(folds[f]) for f in touched_folds
    }
    const_path = raw_root / "constant_arm_descriptive.json"
    if const_path.exists():
        prior = json.loads(const_path.read_text(encoding="utf-8"))
        merged = dict(prior)
        for key, value in constants.items():
            if key in merged:
                # Same fold already recorded — keep prior; do not overwrite.
                continue
            merged[key] = value
        if merged != prior:
            # Only extend with new folds; never rewrite existing fold payloads.
            tmp = const_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
            tmp.replace(const_path)
    else:
        const_path.write_text(json.dumps(constants, indent=2) + "\n", encoding="utf-8")

    return {
        "protocol_id": PROTOCOL_ID,
        "claim_level": CLAIM_LEVEL,
        "preserved_labels": dict(PRESERVED_LABELS),
        "authorization": {
            "mode": auth["mode"],
            "raw_root": auth["raw_root"],
        },
        "inputs": {
            "h5ad": arrays.h5ad_path,
            "atac_counts": arrays.atac_path,
            "matrix_sha256": arrays.matrix_sha256,
            "ordered_full_cells_sha256": arrays.ordered_full_cells_sha256,
            "sampling_cell_ids_sha256": arrays.sampling_cell_ids_sha256,
            "n_sampled_cells": len(arrays.cell_ids),
        },
        "fold_pins": {
            str(f): {
                "target_label": b.target_label,
                "target_index": b.target_index,
                "n_visible_atac": b.n_visible,
                "rna_width": int(b.rna.shape[1]),
                "atac_width": int(b.atac.shape[1]),
                "rna_encoded_sha256": b.rna_encoded_sha256,
                "atac_encoded_sha256": b.atac_encoded_sha256,
                "labels_sha256": b.labels_sha256,
                "cell_ids_sha256": b.cell_ids_sha256,
                "n_train": int(len(b.train_idx)),
                "n_val": int(len(b.val_idx)),
                "n_test": int(len(b.test_idx)),
            }
            for f, b in folds.items()
        },
        "stages": list(stages),
        "n_jobs_planned_this_call": len(jobs),
        "load_feature_seconds": load_seconds,
        "workers": WORKERS,
        "torch_threads": TORCH_THREADS,
        "constant_arm_descriptive_folds": touched_folds,
        "execution": exec_summary,
        "counter": dict(load_attempt_counter(counter_path)),
    }
