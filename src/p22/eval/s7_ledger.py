"""Immutable fit ledger and provenance freeze for the S7 synthetic control.

Tracks completed fit IDs, cumulative budget (≤480 including smoke), and frozen
source/config/input hashes. Completed fits cannot be rewritten. Resuming with
changed fitting hashes labels the run invalid and refuses further writes.
No model fitting happens here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

# Mirrors tasks/nn/finish_20260928/BENCHMARK_SPEC.json resources/models/screen.
S7_MODELS: tuple[str, ...] = (
    "cross_attention",
    "token_concat",
    "rna_atac_concat",
    "gated_fusion",
    "logreg_concat",
    "logreg_rna",
    "logreg_atac",
)
S7_RHO_GRID: tuple[float, ...] = (0.0, 0.5, 1.0)
S7_SCREEN_SEED = 1001
S7_N_FOLDS = 5
S7_MAX_TOTAL_FITS = 480
S7_SMOKE_FIT_LIMIT = 14
S7_PARAM_MATCH_TOLERANCE = 0.10
PROVENANCE_NAME = "provenance.json"
LEDGER_NAME = "fit_ledger.jsonl"
INVALID_MARKER = "RUN_INVALID.txt"


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def make_fit_id(
    stage: str,
    rho: float,
    generator_seed: int,
    fold: int,
    model: str,
) -> str:
    """Stable fit ID: stage|rho|seed|fold|model (rho as compact decimal)."""
    rho_s = f"{float(rho):g}"
    return f"{stage}|{rho_s}|{int(generator_seed)}|{int(fold)}|{model}"


def parse_fit_id(fit_id: str) -> dict[str, Any]:
    parts = fit_id.split("|")
    if len(parts) != 5:
        raise ValueError(f"malformed fit_id {fit_id!r}")
    stage, rho_s, seed_s, fold_s, model = parts
    return {
        "stage": stage,
        "rho": float(rho_s),
        "generator_seed": int(seed_s),
        "fold": int(fold_s),
        "model": model,
    }


def enumerate_screen_jobs(
    *,
    rho_grid: tuple[float, ...] = S7_RHO_GRID,
    generator_seed: int = S7_SCREEN_SEED,
    n_folds: int = S7_N_FOLDS,
    models: tuple[str, ...] = S7_MODELS,
) -> list[dict[str, Any]]:
    """Predeclared screen jobs: |rho| × folds × models (105 under frozen spec)."""
    jobs: list[dict[str, Any]] = []
    for rho in rho_grid:
        for fold in range(int(n_folds)):
            for model in models:
                fit_id = make_fit_id("screen", rho, generator_seed, fold, model)
                jobs.append(
                    {
                        "fit_id": fit_id,
                        "stage": "screen",
                        "rho": float(rho),
                        "generator_seed": int(generator_seed),
                        "fold": int(fold),
                        "model": model,
                    }
                )
    return jobs


def check_param_match(
    ca_params: int,
    tc_params: int,
    *,
    tolerance: float = S7_PARAM_MATCH_TOLERANCE,
) -> dict[str, Any]:
    """Refuse CA/TC mismatch beyond tolerance unless matching was predeclared."""
    ca_n = int(ca_params)
    tc_n = int(tc_params)
    if ca_n <= 0 or tc_n <= 0:
        raise ValueError("parameter counts must be positive")
    denom = max(ca_n, tc_n)
    relative = abs(ca_n - tc_n) / denom
    record = {
        "cross_attention": ca_n,
        "token_concat": tc_n,
        "relative_error": round(relative, 6),
        "tolerance": float(tolerance),
        "matched": relative <= float(tolerance),
    }
    if not record["matched"]:
        raise ValueError(
            f"CA/TC parameter mismatch: relative error {relative:.4f} "
            f"> {tolerance} (ca={ca_n}, tc={tc_n}); refuse fits unless "
            "deterministic label-free matching was declared before fits"
        )
    return record


def count_parameters(model) -> int:
    return int(sum(p.numel() for p in model.parameters() if p.requires_grad))


@dataclass(frozen=True)
class Provenance:
    """Frozen hashes that must match exactly for a valid resume."""

    protocol_id: str
    spec_sha256: str
    source_sha256: dict[str, str]
    input_sha256: dict[str, str]
    extra: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "protocol_id": self.protocol_id,
            "spec_sha256": self.spec_sha256,
            "source_sha256": dict(sorted(self.source_sha256.items())),
            "input_sha256": dict(sorted(self.input_sha256.items())),
        }
        if self.extra:
            payload["extra"] = dict(self.extra)
        return payload

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Provenance":
        return cls(
            protocol_id=str(raw["protocol_id"]),
            spec_sha256=str(raw["spec_sha256"]),
            source_sha256={str(k): str(v) for k, v in dict(raw["source_sha256"]).items()},
            input_sha256={str(k): str(v) for k, v in dict(raw["input_sha256"]).items()},
            extra=dict(raw["extra"]) if "extra" in raw else None,
        )

    def fingerprint(self) -> str:
        return sha256_text(json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")))


class S7FitLedger:
    """Append-only fit ledger with immutable completed IDs and hash freeze."""

    def __init__(
        self,
        root: Path | str,
        *,
        max_total_fits: int = S7_MAX_TOTAL_FITS,
        smoke_fit_limit: int = S7_SMOKE_FIT_LIMIT,
    ) -> None:
        self.root = Path(root)
        self.max_total_fits = int(max_total_fits)
        self.smoke_fit_limit = int(smoke_fit_limit)
        self.provenance_path = self.root / PROVENANCE_NAME
        self.ledger_path = self.root / LEDGER_NAME
        self.invalid_path = self.root / INVALID_MARKER
        self._provenance: Provenance | None = None
        self._records: dict[str, dict[str, Any]] = {}
        self._invalid_reason: str | None = None

    @property
    def is_invalid(self) -> bool:
        return self._invalid_reason is not None or self.invalid_path.exists()

    @property
    def invalid_reason(self) -> str | None:
        if self._invalid_reason is not None:
            return self._invalid_reason
        if self.invalid_path.exists():
            return self.invalid_path.read_text(encoding="utf-8").strip() or "invalid"
        return None

    def mark_invalid(self, reason: str) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self._invalid_reason = reason
        self.invalid_path.write_text(reason.rstrip() + "\n", encoding="utf-8")

    def freeze(self, provenance: Provenance) -> Provenance:
        """Write provenance once; refuse conflicting freezes / resumes."""
        if self.is_invalid:
            raise RuntimeError(f"ledger invalid: {self.invalid_reason}")
        self.root.mkdir(parents=True, exist_ok=True)
        if self.provenance_path.exists():
            existing = Provenance.from_dict(
                json.loads(self.provenance_path.read_text(encoding="utf-8"))
            )
            if existing.to_dict() != provenance.to_dict():
                reason = (
                    "resume hash refusal: frozen provenance differs from "
                    f"requested (existing={existing.fingerprint()}, "
                    f"requested={provenance.fingerprint()})"
                )
                self.mark_invalid(reason)
                raise RuntimeError(reason)
            self._provenance = existing
            return existing
        self.provenance_path.write_text(
            json.dumps(provenance.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._provenance = provenance
        return provenance

    def load(self) -> None:
        if self.invalid_path.exists():
            self._invalid_reason = self.invalid_path.read_text(encoding="utf-8").strip()
        if self.provenance_path.exists():
            self._provenance = Provenance.from_dict(
                json.loads(self.provenance_path.read_text(encoding="utf-8"))
            )
        self._records = {}
        if not self.ledger_path.exists():
            return
        with self.ledger_path.open(encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                row = json.loads(text)
                fit_id = str(row["fit_id"])
                if fit_id in self._records:
                    raise RuntimeError(
                        f"duplicate fit_id {fit_id!r} at ledger line {line_no}"
                    )
                self._records[fit_id] = row

    def assert_resume_hashes(self, provenance: Provenance) -> None:
        """Require an existing freeze and exact hash match before more fits."""
        if self.is_invalid:
            raise RuntimeError(f"ledger invalid: {self.invalid_reason}")
        if not self.provenance_path.exists():
            raise RuntimeError("no frozen provenance; call freeze() before resume")
        existing = Provenance.from_dict(
            json.loads(self.provenance_path.read_text(encoding="utf-8"))
        )
        if existing.to_dict() != provenance.to_dict():
            reason = (
                "resume hash refusal: source/config/input hashes changed after "
                f"outcomes (existing={existing.fingerprint()}, "
                f"requested={provenance.fingerprint()})"
            )
            self.mark_invalid(reason)
            raise RuntimeError(reason)
        self._provenance = existing

    @property
    def completed_ids(self) -> frozenset[str]:
        return frozenset(self._records)

    @property
    def records(self) -> dict[str, dict[str, Any]]:
        """Shallow copy of completed fit rows (immutable IDs; callers must not rewrite)."""
        return {fit_id: dict(row) for fit_id, row in self._records.items()}

    @property
    def n_completed(self) -> int:
        return len(self._records)

    def remaining_budget(self) -> int:
        return max(0, self.max_total_fits - self.n_completed)

    def smoke_remaining(self) -> int:
        smoke_done = sum(
            1 for row in self._records.values() if row.get("stage") == "smoke"
        )
        return max(0, self.smoke_fit_limit - smoke_done)

    def record_fit(self, fit_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Append one completed fit. Immutable: refuse rewrite of known IDs."""
        if self.is_invalid:
            raise RuntimeError(f"ledger invalid: {self.invalid_reason}")
        if self._provenance is None and not self.provenance_path.exists():
            raise RuntimeError("freeze provenance before recording fits")
        if self._provenance is None:
            self.load()
        if fit_id in self._records:
            raise RuntimeError(f"immutable fit refusal: {fit_id!r} already recorded")
        if self.n_completed >= self.max_total_fits:
            raise RuntimeError(
                f"budget exhausted: {self.n_completed}/{self.max_total_fits} fits"
            )
        parsed = parse_fit_id(fit_id)
        stage = str(payload.get("stage", parsed["stage"]))
        if stage == "smoke" and self.smoke_remaining() <= 0:
            raise RuntimeError(
                f"smoke budget exhausted: limit {self.smoke_fit_limit}"
            )
        row = {
            "fit_id": fit_id,
            "stage": stage,
            "rho": float(payload.get("rho", parsed["rho"])),
            "generator_seed": int(payload.get("generator_seed", parsed["generator_seed"])),
            "fold": int(payload.get("fold", parsed["fold"])),
            "model": str(payload.get("model", parsed["model"])),
            "status": str(payload.get("status", "ok")),
        }
        for key, value in payload.items():
            if key not in row:
                row[key] = value
        self.root.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        self._records[fit_id] = row
        return row

    def coverage(
        self,
        *,
        stage: str = "screen",
        rho: float | None = None,
        generator_seed: int | None = None,
        n_folds: int = S7_N_FOLDS,
        models: tuple[str, ...] = S7_MODELS,
    ) -> dict[str, Any]:
        """Report whether every model×fold cell is present for a stage/rho."""
        expected: list[str] = []
        if rho is None:
            rhos = list(S7_RHO_GRID) if stage == "screen" else [1.0]
        else:
            rhos = [float(rho)]
        seed = S7_SCREEN_SEED if generator_seed is None else int(generator_seed)
        for r in rhos:
            for fold in range(int(n_folds)):
                for model in models:
                    expected.append(make_fit_id(stage, r, seed, fold, model))
        present = [fid for fid in expected if fid in self._records]
        missing = [fid for fid in expected if fid not in self._records]
        return {
            "stage": stage,
            "expected": len(expected),
            "present": len(present),
            "missing": missing,
            "complete": not missing,
        }
