"""Frozen ladder arm factory (N9).

Every NN-v2 rung is built here from one place so the frozen protocol can name a
single constructor per arm. ``build_arm`` returns ``(model, aux_losses, trainer)``:

* ``model`` is the torch module (or, for the sklearn controls, a
  :class:`ControlPlan`) that the runner fits for one fold.
* ``aux_losses`` is the tuple of MIL auxiliary-loss callables. It is returned for
  inspection; the MIL trainer already closes over it.
* ``trainer`` is a callable ``trainer(model, train, val) -> TrainedModel | FittedControl``
  with ``train``/``val`` each an :class:`ArmData`.

The factory only builds architecture. It never reads real DS labels; that happens
in N10 under the frozen protocol. The parameter-matched control
(``R3_tc_parammatched``) widens the token-concat hidden width until the full R3
token-concat arm is within 5% (10% fallback, decision-tree N9) of ``R3_ca``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch
from torch import nn

from p22.models.baselines import BaselineMLP
from p22.models.contrastive import PairingHead, pairing_aux_loss
from p22.models.cross_attention import CrossAttentionModel, TokenConcatFusionModel
from p22.models.fusion import VIEW_A, VIEW_B, GatedFusionModel
from p22.models.mil import MILWrapper
from p22.models.nuisance import ConditionalNuisanceAdversary, adversary_aux_loss
from p22.models.program_tokens import ProgramTokenConcat, ProgramTokenCrossAttention
from p22.training.loop import TrainedModel, train_model
from p22.training.mil_loop import train_mil

__all__ = [
    "ARM_NAMES",
    "ArmData",
    "ControlPlan",
    "FittedControl",
    "build_arm",
    "parameter_counts",
    "write_parameter_counts",
]

DEFAULT_ARCH: dict[str, Any] = {
    "n_tokens": 4,
    "embed_dim": 16,
    "hidden_dim": 32,
    "dropout": 0.1,
    "n_heads": 2,
    "attn_dim": 64,
    "gate_hidden_dim": 32,
    "prog_dim": 32,
    "prog_heads": 4,
    "n_qc": 5,
    "adv_hidden": 64,
    "pairing_proj": 32,
    "latent_width": 64,
    "lambda_adv": 1.0,
    "lambda_nce": 1.0,
}

DEFAULT_TRAIN: dict[str, Any] = {
    "bag_size": 64,
    "batch_size": 64,
    "learning_rate": 1e-3,
    "max_epochs": 30,
    "patience": 6,
    "seed": 0,
    "device": "cpu",
}

#: Cell-level arms cannot select on a continuous loss through ``train_model`` (its
#: donor-mode selection maximises donor balanced accuracy); MIL arms use donor
#: log-loss. Recorded here so the freeze note can state the difference honestly.
CELL_SELECTION_METRIC = "balanced_accuracy"

_NN_ARM_NAMES = (
    "R0_ca",
    "R0_tc",
    "R1_ca",
    "R1_tc",
    "R2_ca",
    "R2_tc",
    "R3_ca",
    "R3_tc",
    "R4_ca",
    "R4_tc",
    "R3_tc_parammatched",
    "R3_gated",
    "latent_pca_lsi_head",
)
_CONTROL_ARM_NAMES = (
    "logreg_rna",
    "logreg_concat",
    "pseudobulk_rna_logistic",
    "chr21_dosage",
    "majority",
)
ARM_NAMES = _NN_ARM_NAMES + _CONTROL_ARM_NAMES

_ADV_ARMS = {"R2_ca", "R2_tc", "R3_ca", "R3_tc", "R4_ca", "R4_tc", "R3_gated"}
_NCE_ARMS = {"R3_ca", "R3_tc", "R3_gated"}


@dataclass(frozen=True)
class ArmData:
    """Per-fold arrays handed to a trainer.

    Args:
        views: mapping of view name to ``(n_cells, n_features)`` array.
        labels: ``(n_cells,)`` binary labels.
        donors: ``(n_cells,)`` donor IDs.
        cell_meta: optional per-cell nuisance arrays (``labels``, ``library``,
            ``batch``, ``qc``) for arms with an adversary.
    """

    views: Mapping[str, np.ndarray]
    labels: np.ndarray
    donors: np.ndarray
    cell_meta: Mapping[str, np.ndarray] | None = None


@dataclass(frozen=True)
class ControlPlan:
    """Buildable placeholder for a non-NN control arm."""

    name: str
    kind: str
    n_features: int
    detail: str = ""


@dataclass
class FittedControl:
    """A fitted sklearn control with a ``predict_proba`` path."""

    kind: str
    estimator: Any
    n_features: int
    donor_fit: bool = False
    majority: int | None = None

    def predict_proba(self, views: Mapping[str, np.ndarray]) -> np.ndarray:
        """Return ``(n_cells, 2)`` class probabilities for a held-out split."""
        if self.majority is not None:
            prob = np.full((_n_rows(views), 2), 0.0)
            prob[:, self.majority] = 1.0
            return prob
        matrix = _control_matrix(self.kind, views)
        proba = self.estimator.predict_proba(matrix)
        if proba.shape[1] == 1:
            full = np.zeros((proba.shape[0], 2))
            classes = list(self.estimator.classes_)
            full[:, int(classes[0])] = proba[:, 0]
            full[:, 1 - int(classes[0])] = 1.0 - proba[:, 0]
            return full
        return proba


def _n_rows(views: Mapping[str, np.ndarray]) -> int:
    return len(next(iter(views.values())))


def _control_matrix(kind: str, views: Mapping[str, np.ndarray]) -> np.ndarray:
    if kind == "logreg_rna":
        return np.asarray(views[VIEW_A], dtype=np.float64)
    if kind == "logreg_concat":
        return np.hstack(
            [np.asarray(views[VIEW_A], dtype=np.float64),
             np.asarray(views[VIEW_B], dtype=np.float64)]
        )
    if kind in {"pseudobulk_rna_logistic", "chr21_dosage"}:
        key = "chr21_dosage" if kind == "chr21_dosage" else VIEW_A
        matrix = np.asarray(views[key], dtype=np.float64)
        return matrix.reshape(-1, 1) if matrix.ndim == 1 else matrix
    raise ValueError(f"control {kind!r} has no feature matrix")


def _validate_int(value: Any, name: str, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


def _require(widths: Mapping[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in widths]
    if missing:
        raise ValueError(f"widths is missing {missing}")


def _options(cfg: Mapping[str, Any] | None) -> dict[str, Any]:
    options = {**DEFAULT_ARCH, **DEFAULT_TRAIN, **dict(cfg or {})}
    for name in ("n_tokens", "embed_dim", "hidden_dim", "n_heads", "attn_dim"):
        _validate_int(options[name], name)
    return options


def _fusion(kind: str, widths: Mapping[str, Any], options: Mapping[str, Any]) -> nn.Module:
    n_a = _validate_int(widths["n_features_a"], "n_features_a")
    n_b = _validate_int(widths["n_features_b"], "n_features_b")
    n_classes = _validate_int(widths.get("n_classes", 2), "n_classes", 2)
    common = {
        "n_classes": n_classes,
        "embed_dim": options["embed_dim"],
        "hidden_dim": options["hidden_dim"],
        "dropout": options["dropout"],
    }
    if kind == "ca":
        return CrossAttentionModel(n_a, n_b, **common, n_tokens=options["n_tokens"],
                                   n_heads=options["n_heads"])
    if kind == "tc":
        return TokenConcatFusionModel(n_a, n_b, **common, n_tokens=options["n_tokens"])
    if kind == "gated":
        return GatedFusionModel(n_a, n_b, **common,
                                gate_hidden_dim=options["gate_hidden_dim"])
    raise ValueError(f"unknown fusion kind {kind!r}")


def _program_encoder(
    kind: str, widths: Mapping[str, Any], options: Mapping[str, Any]
) -> nn.Module:
    _require(widths, "k_rna", "k_atac")
    dim = _validate_int(options["prog_dim"], "prog_dim")
    if kind == "ca":
        return ProgramTokenCrossAttention(
            widths["k_rna"], widths["k_atac"], dim=dim, heads=options["prog_heads"],
            n_classes=_validate_int(widths.get("n_classes", 2), "n_classes", 2),
            dropout=options["dropout"],
        )
    if kind == "tc":
        return ProgramTokenConcat(
            widths["k_rna"], widths["k_atac"], dim=dim,
            n_classes=_validate_int(widths.get("n_classes", 2), "n_classes", 2),
            dropout=options["dropout"],
        )
    raise ValueError(f"unknown program kind {kind!r}")


class _ProgramFusionAdapter(nn.Module):
    """Give a program-token model the two-view ``has_gate`` contract MIL needs."""

    has_gate = True

    def __init__(self, inner: nn.Module) -> None:
        super().__init__()
        self.inner = inner
        self.embed_dim = 2 * int(inner.dim)

    def forward(self, view_a: torch.Tensor, view_b: torch.Tensor, **kwargs: Any):
        return self.inner(view_a, view_b, **kwargs)


def _adversary(
    model: nn.Module, dim: int, widths: Mapping[str, Any], options: Mapping[str, Any]
):
    n_library = _validate_int(widths["n_library"], "n_library")
    n_batch = _validate_int(widths["n_batch"], "n_batch")
    adversary = ConditionalNuisanceAdversary(
        dim, n_library, n_batch, n_qc=options["n_qc"], hidden=options["adv_hidden"]
    )
    # Attach so train_mil's optimiser sees it (A-NEW-1).
    model.adversary = adversary
    cell_meta = dict(options.get("cell_meta") or {})
    return adversary, adversary_aux_loss(adversary, cell_meta, options["lambda_adv"])


def _add_pairing(model: nn.Module, dim: int, options: Mapping[str, Any]):
    head = PairingHead(dim, proj=options["pairing_proj"])
    return pairing_aux_loss(head, options["lambda_nce"])


def _mil_trainer(aux_losses: Sequence[Any], options: Mapping[str, Any]):
    def run(model: nn.Module, train: ArmData, val: ArmData) -> TrainedModel:
        cfg = {key: options[key] for key in DEFAULT_TRAIN if key in options}
        return train_mil(
            model,
            dict(train.views),
            train.donors,
            train.labels,
            dict(val.views),
            val.donors,
            val.labels,
            cfg,
            tuple(aux_losses),
        )

    return run


def _cell_trainer(options: Mapping[str, Any]):
    def run(model: nn.Module, train: ArmData, val: ArmData) -> TrainedModel:
        return train_model(
            model,
            dict(train.views),
            train.labels,
            dict(val.views),
            val.labels,
            max_epochs=int(options["max_epochs"]),
            batch_size=int(options["batch_size"]),
            learning_rate=float(options["learning_rate"]),
            patience=int(options["patience"]),
            seed=int(options["seed"]),
            selection_metric=CELL_SELECTION_METRIC,
            device=str(options["device"]),
            train_donor_ids=train.donors,
            val_donor_ids=val.donors,
        )

    return run


def _control_trainer(kind: str):
    def run(_model: nn.Module, train: ArmData, val: ArmData) -> FittedControl:
        del val
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        if kind == "majority":
            values, counts = np.unique(np.asarray(train.labels), return_counts=True)
            return FittedControl(
                kind=kind, estimator=None, n_features=0,
                majority=int(values[int(np.argmax(counts))]),
            )
        n_features = int(_control_matrix(kind, train.views).shape[1])
        if kind == "pseudobulk_rna_logistic":
            donors = np.asarray(train.donors).astype(str)
            bulk, donor_labels = _pool_by_donor(train.views[VIEW_A], donors, train.labels)
            scaler = StandardScaler().fit(bulk)
            estimator = LogisticRegression(max_iter=1000, class_weight="balanced")
            estimator.fit(scaler.transform(bulk), donor_labels)
            return FittedControl(
                kind=kind, estimator=_Scaled(scaler, estimator), n_features=n_features,
                donor_fit=True,
            )
        matrix = _control_matrix(kind, train.views)
        weights = _donor_weights(train.donors)
        scaler = StandardScaler().fit(matrix)
        estimator = LogisticRegression(max_iter=1000, fit_intercept=True)
        estimator.fit(scaler.transform(matrix), np.asarray(train.labels), sample_weight=weights)
        return FittedControl(
            kind=kind, estimator=_Scaled(scaler, estimator), n_features=n_features
        )

    return run


class _Scaled:
    """Tiny scaler+estimator pair exposing ``predict_proba``/``classes_``."""

    def __init__(self, scaler: Any, estimator: Any) -> None:
        self.scaler = scaler
        self.estimator = estimator
        self.classes_ = estimator.classes_

    def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
        return self.estimator.predict_proba(self.scaler.transform(matrix))


def _pool_by_donor(
    matrix: np.ndarray, donors: np.ndarray, labels: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    donor_ids = np.unique(donors)
    bulk = np.vstack([np.asarray(matrix)[donors == d].mean(axis=0) for d in donor_ids])
    donor_labels = np.array([int(np.asarray(labels)[donors == d][0]) for d in donor_ids])
    return bulk, donor_labels


def _donor_weights(donors: np.ndarray) -> np.ndarray:
    donors = np.asarray(donors).astype(str)
    _, inverse, counts = np.unique(donors, return_inverse=True, return_counts=True)
    return (len(donors) / (len(counts) * counts[inverse])).astype(np.float64)


def _param_count(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


def _needs_adv(arm_name: str) -> bool:
    return arm_name in _ADV_ARMS


def _needs_nce(arm_name: str) -> bool:
    return arm_name in _NCE_ARMS


def _build_nn(
    arm_name: str, widths: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[nn.Module, tuple[Any, ...], Callable[..., Any]]:
    if arm_name.startswith("R0_"):
        kind = arm_name.split("_", 1)[1]
        model = _fusion(kind, widths, options)
        return model, (), _cell_trainer(options)

    if arm_name == "latent_pca_lsi_head":
        width = _validate_int(options["latent_width"], "latent_width")
        base = BaselineMLP(
            width, _validate_int(widths.get("n_classes", 2), "n_classes", 2),
            embed_dim=options["embed_dim"], hidden_dim=options["hidden_dim"],
            dropout=options["dropout"],
        )
        model = MILWrapper(base, dim=options["embed_dim"], attn_dim=options["attn_dim"])
        return model, (), _mil_trainer((), options)

    if arm_name.startswith("R4_"):
        kind = arm_name.split("_", 1)[1]
        inner = _program_encoder(kind, widths, options)
        fusion = _ProgramFusionAdapter(inner)
        model = MILWrapper(fusion, dim=fusion.embed_dim, attn_dim=options["attn_dim"])
        aux: list[Any] = []
        if _needs_adv(arm_name):
            _adv, loss = _adversary(model, fusion.embed_dim, widths, options)
            aux.append(loss)
        return model, tuple(aux), _mil_trainer(tuple(aux), options)

    kind = arm_name[1:].rsplit("_", 1)[1]
    if kind == "parammatched":
        kind = "tc"
    base = _fusion(kind, widths, options)
    branch_dim = _validate_int(options["embed_dim"], "embed_dim")
    # The bag head (and adversary) read the *fused* embedding width: gated fusion
    # returns a weighted sum (embed_dim), concat/cross-attention concatenate the
    # two branches (2 * embed_dim). Pairing reads per-branch embeddings (embed_dim).
    fused_dim = branch_dim if kind == "gated" else 2 * branch_dim
    model = MILWrapper(base, dim=fused_dim, attn_dim=options["attn_dim"])
    aux = []
    if _needs_adv(arm_name):
        _adv, loss = _adversary(model, fused_dim, widths, options)
        aux.append(loss)
    if _needs_nce(arm_name):
        aux.append(_add_pairing(model, branch_dim, options))
    return model, tuple(aux), _mil_trainer(tuple(aux), options)


def _build_parammatched(
    widths: Mapping[str, Any], options: Mapping[str, Any]
) -> tuple[nn.Module, tuple[Any, ...], Callable[..., Any], dict[str, Any]]:
    target_model, _, _ = _build_nn("R3_ca", widths, options)
    target = _param_count(target_model)
    best: tuple[float, nn.Module, tuple[Any, ...], Callable[..., Any], int, int] | None = None
    for hidden in (32, 48, 64, 96, 128, 160, 192, 256, 320, 384, 512):
        for n_tokens in (4, 6, 8, 12, 16):
            trial_options = {**options, "hidden_dim": hidden, "n_tokens": n_tokens}
            try:
                model, aux, trainer = _build_nn("R3_tc", widths, trial_options)
            except ValueError:
                continue
            count = _param_count(model)
            error = abs(count - target) / target
            if best is None or error < best[0]:
                best = (error, model, aux, trainer, hidden, n_tokens)
    if best is None:
        raise ValueError("could not build any R3_tc_parammatched candidate")
    error, model, aux, trainer, hidden, n_tokens = best
    if error > 0.10:
        raise ValueError(
            f"R3_tc_parammatched cannot reach within 10% of R3_ca "
            f"(best relative error {error:.3f})"
        )
    model.match_info = {  # type: ignore[attr-defined]
        "hidden_dim": hidden,
        "n_tokens": n_tokens,
        "n_params": _param_count(model),
        "target_params": target,
        "relative_error": round(error, 6),
        "within_5pct": error <= 0.05,
    }
    return model, aux, trainer, model.match_info  # type: ignore[attr-defined]


def build_arm(
    arm_name: str, widths: Mapping[str, Any], cfg: Mapping[str, Any] | None = None
) -> tuple[nn.Module, tuple[Any, ...], Callable[..., Any]]:
    """Build one ladder arm.

    Args:
        arm_name: one of :data:`ARM_NAMES`.
        widths: feature/program widths. Requires ``n_features_a``, ``n_features_b``;
            adversary arms also require ``n_library``, ``n_batch``; R4 arms also
            require ``k_rna``, ``k_atac``.
        cfg: architecture and training overrides merged over the defaults. Include
            ``cell_meta`` (training-cell ``labels``/``library``/``batch``/``qc``)
            for adversary arms.

    Returns:
        ``(model, aux_losses, trainer)``.

    Raises:
        ValueError: on an unknown arm, missing widths or invalid options.
    """
    if arm_name not in ARM_NAMES:
        raise ValueError(f"unknown arm {arm_name!r}; expected one of {sorted(ARM_NAMES)}")
    widths = dict(widths)
    options = {**DEFAULT_ARCH, **DEFAULT_TRAIN, **dict(cfg or {})}
    options["n_classes"] = widths.get("n_classes", 2)

    if arm_name in _CONTROL_ARM_NAMES:
        plan = ControlPlan(
            name=arm_name,
            kind=arm_name,
            n_features=_validate_int(
                widths.get("n_features_a", 1) if arm_name != "majority" else 1,
                "n_features_a",
            ),
        )
        return plan, (), _control_trainer(arm_name)  # type: ignore[arg-type]

    if _needs_adv(arm_name):
        _require(widths, "n_library", "n_batch")
    if arm_name.startswith("R4_"):
        _require(widths, "k_rna", "k_atac")

    if arm_name == "R3_tc_parammatched":
        model, aux, trainer, _info = _build_parammatched(widths, options)
        return model, aux, trainer
    return _build_nn(arm_name, widths, options)


def parameter_counts(
    widths: Mapping[str, Any], cfg: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Return trainable parameter counts for every buildable arm.

    Control arms report ``None`` (they are sklearn models, not torch modules).
    """
    out: dict[str, Any] = {}
    for arm_name in ARM_NAMES:
        if arm_name in _CONTROL_ARM_NAMES:
            out[arm_name] = None
            continue
        model, _aux, _trainer = build_arm(arm_name, widths, cfg)
        entry: dict[str, Any] = {"n_params": _param_count(model)}
        match = getattr(model, "match_info", None)
        if match is not None:
            entry["match"] = match
        out[arm_name] = entry
    return out


def write_parameter_counts(
    path: str, widths: Mapping[str, Any], cfg: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Compute :func:`parameter_counts` and write it as JSON, returning the dict."""
    import json
    from pathlib import Path

    counts = parameter_counts(widths, cfg)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return counts
