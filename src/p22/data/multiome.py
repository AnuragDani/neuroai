"""Public paired-file diagnostics. No training, QC invention, or approval changes."""

from __future__ import annotations

import gzip
import io
import json
import re
import tarfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
from scipy import io as scipy_io
from scipy import sparse

from p22.data.census import sha256_file
from p22.data.real_cohort import sample_nested_capped_cells


@dataclass
class ReadBudget:
    """Cumulative file/decompression limits, not an estimate of total process memory."""

    max_input_bytes: int = 64 * 1024**2
    max_expanded_bytes: int = 256 * 1024**2
    input_bytes: int = 0
    expanded_bytes: int = 0
    records: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.max_input_bytes < 1 or self.max_expanded_bytes < 1:
            raise ValueError("byte budgets must be positive")


def read_asset(spec: dict, budget: ReadBudget) -> bytes:
    """Read pinned local files or tar members without extraction or network access.

    Archives are untrusted: refuse links, special files, unsafe/duplicate names,
    and excessive expansion. Python 3.11 extractfile returns a read-only stream:
    https://docs.python.org/3.11/library/tarfile.html#tarfile.TarFile.extractfile
    """
    path = Path(spec["path"])
    source = urlsplit(spec.get("source_url", ""))
    if source.scheme != "https" or not source.netloc:
        raise ValueError("asset needs an HTTPS provenance source_url (never fetched here)")
    expected = spec.get("sha256", "")
    if not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise ValueError("asset needs a pinned SHA-256 checksum")
    if path.is_symlink() or not path.is_file():
        raise ValueError("asset path must be a regular local file")
    size = path.stat().st_size
    if budget.input_bytes + size > budget.max_input_bytes:
        raise ValueError("input byte budget exceeded")
    if sha256_file(path) != expected:
        raise ValueError("asset checksum mismatch")
    budget.input_bytes += size
    remaining = budget.max_expanded_bytes - budget.expanded_bytes
    if "member" in spec:
        # ponytail: no filesystem extraction. Large archives need a separately budgeted loader.
        with tarfile.open(path, "r:*") as archive:
            names, total, target = set(), 0, None
            for member in archive:
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts or "\\" in member.name:
                    raise ValueError("unsafe archive path")
                if str(name) in names:
                    raise ValueError("duplicate archive path")
                names.add(str(name))
                if not (member.isfile() or member.isdir()) or member.issparse():
                    raise ValueError("unsafe archive member type")
                total += member.size
                if total > remaining or len(names) > 10_000:
                    raise ValueError("archive expanded byte/member budget exceeded")
                if member.name == spec["member"] and member.isfile():
                    target = member
            if target is None:
                raise ValueError("requested archive member missing")
            with archive.extractfile(target) as stream:
                raw = stream.read(remaining + 1)
    else:
        with path.open("rb") as stream:
            raw = stream.read(size + 1)
    if raw.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(remaining + 1)
    if len(raw) > remaining:
        raise ValueError("expanded byte budget exceeded")
    budget.expanded_bytes += len(raw)
    budget.records.append(
        {
            "path": str(path.resolve()),
            "member": spec.get("member"),
            "source_url": spec["source_url"],
            "sha256": expected,
            "input_bytes": size,
            "expanded_bytes": len(raw),
        }
    )
    return raw


def read_features(asset: dict, budget: ReadBudget, *, modality: str | None = None) -> pd.DataFrame:
    """Read two-/three-column MEX or six-column ARC features without discarding coordinates."""
    features = pd.read_csv(
        io.BytesIO(read_asset(asset, budget)),
        sep="\t",
        header=None,
        dtype=str,
        keep_default_na=False,
    )
    if len(features.columns) == 2 and modality in ("Gene Expression", "Peaks"):
        features[2] = modality
    if len(features.columns) not in (3, 6) or features.empty:
        raise ValueError("features need id, name, and explicit modality")
    names = ["feature_id", "feature_name", "modality"]
    if len(features.columns) == 6:
        names += ["chromosome", "start", "end"]
    features.columns = names
    if "start" in features:
        for column in ("start", "end"):
            values = pd.to_numeric(features[column], errors="raise")
            if not np.isfinite(values).all() or (values != np.floor(values)).any():
                raise ValueError("feature coordinates must be finite integers")
            features[column] = values.astype(np.int64)
        known = (features.start >= 0) & (features.end > features.start)
        known &= features.chromosome.str.strip().ne("")
        unmapped_rna = (
            features.modality.eq("Gene Expression")
            & features.start.eq(-1)
            & features.end.eq(-1)
            & features.chromosome.eq("")
        )
        if (~known & ~unmapped_rna).any():
            raise ValueError("feature intervals must have nonnegative start < end")
        features["coordinates_known"] = known
    if features.feature_id.eq("").any() or features.feature_id.duplicated().any():
        raise ValueError("empty or duplicate feature identifiers")
    if not features.modality.isin(["Gene Expression", "Peaks"]).all():
        raise ValueError("unknown feature modality")
    if modality and not features.modality.eq(modality).all():
        raise ValueError("features disagree with declared modality")
    return features


def load_mex(
    assets: dict, budget: ReadBudget, *, modality: str | None = None, max_nnz: int = 10_000_000
) -> dict:
    """Read bounded 10x MEX counts as cells-by-features CSR, never a dense atlas.

    Explicit spmatrix=True matches installed SciPy 1.17.1; reject array-format
    headers before mmread can allocate a dense matrix. Format references:
    https://docs.scipy.org/doc/scipy/reference/generated/scipy.io.mmread.html
    https://www.10xgenomics.com/support/software/cell-ranger-arc/latest/analysis/feature-barcode-matrices
    """
    features = read_features(assets["features"], budget, modality=modality)
    barcodes = tuple(read_asset(assets["barcodes"], budget).decode().splitlines())
    if (
        not barcodes
        or len(set(barcodes)) != len(barcodes)
        or any(not b.strip() or "\t" in b for b in barcodes)
    ):
        raise ValueError("empty, duplicate, or malformed barcodes")
    raw = read_asset(assets["matrix"], budget)
    rows, columns, entries, storage, kind, symmetry = scipy_io.mminfo(io.BytesIO(raw))
    if storage != "coordinate" or kind not in ("integer", "real") or symmetry != "general":
        raise ValueError("only general coordinate count matrices are accepted")
    if rows != len(features) or columns != len(barcodes):
        raise ValueError("matrix dimensions disagree with features/barcodes")
    if max_nnz < 1 or entries < 0 or entries > max_nnz:
        raise ValueError("matrix entry budget exceeded")
    counts = scipy_io.mmread(io.BytesIO(raw), spmatrix=True)
    if (
        not np.isfinite(counts.data).all()
        or (counts.data < 0).any()
        or (counts.data != np.floor(counts.data)).any()
    ):
        raise ValueError("counts must be finite nonnegative integers")
    matrix = counts.T.tocsr()
    if matrix.nnz != counts.nnz:
        raise ValueError("duplicate matrix coordinates")
    return {"matrix": matrix, "features": features, "barcodes": barcodes}


def pair_and_cap(rna: dict, atac: dict | None, metadata: pd.DataFrame, *, cap: int) -> dict:
    """Keep matched nuclei across modalities and sample by donor using existing helpers."""
    other = rna if atac is None else atac
    if rna["barcodes"] != other["barcodes"]:
        raise ValueError("RNA and ATAC ordered barcodes disagree")
    barcodes = rna["barcodes"]
    if metadata.barcode.duplicated().any() or set(metadata.barcode) != set(barcodes):
        raise ValueError("metadata must join each matrix barcode exactly once")
    ordered = metadata.set_index("barcode").loc[list(barcodes)].reset_index()
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
        raise ValueError("cell cap must be a positive integer")
    samples = sample_nested_capped_cells(
        ordered, np.ones(len(ordered), dtype=bool), caps=(cap,), seed=22
    )[cap]
    rna_mask = rna["features"].modality.eq("Gene Expression").to_numpy()
    atac_mask = other["features"].modality.eq("Peaks").to_numpy()
    if not rna_mask.any() or not atac_mask.any():
        raise ValueError("both RNA and ATAC features are required")
    return {
        "rna": sparse.csr_matrix(rna["matrix"][samples][:, rna_mask]),
        "atac": sparse.csr_matrix(other["matrix"][samples][:, atac_mask]),
        "metadata": ordered.iloc[samples].reset_index(drop=True),
        "source_rows": samples,
        "rna_features": rna["features"].loc[rna_mask].reset_index(drop=True),
        "atac_features": other["features"].loc[atac_mask].reset_index(drop=True),
    }


def parse_geo_libraries(soft_text: str) -> pd.DataFrame:
    """Read GSE305146's explicit sample characteristics, never infer donors from titles."""
    samples = []
    current = None
    for line in soft_text.splitlines():
        if line.startswith("^"):
            current = None
            if line.startswith("^SAMPLE = "):
                current = {"accession": line.split(" = ", 1)[1]}
                samples.append(current)
        elif current is not None and line.startswith("!Sample_title = "):
            current["title"] = line.split(" = ", 1)[1]
        elif current is not None and line.startswith("!Sample_characteristics_ch1 = "):
            key, value = line.split(" = ", 1)[1].split(": ", 1)
            if key in current and current[key] != value:
                raise ValueError(f"conflicting GEO characteristic: {key}")
            current[key] = value
    libraries = {}
    for sample in samples:
        match = re.search(r"Library ([^ ,]+)_(atac|gex)(?:,|$)", sample.get("title", ""))
        if match is None:
            raise ValueError("unrecognized GEO library title")
        library, assay = match.groups()
        required = ("name", "group", "dev stage_pcw", "in final_analysis")
        if any(not sample.get(key, "").strip() for key in required):
            raise ValueError("missing GEO donor or retention characteristic")
        if sample["in final_analysis"] not in ("TRUE", "FALSE"):
            raise ValueError("unknown GEO final-analysis flag")
        row = {
            "library_id": library,
            "donor_id": sample["name"],
            "condition": sample["group"],
            "age_raw": float(sample["dev stage_pcw"]),
            "in_final_analysis": sample["in final_analysis"] == "TRUE",
        }
        old = libraries.setdefault(library, row.copy())
        if any(old[key] != value for key, value in row.items()):
            raise ValueError(f"GEO assays disagree for library {library}")
        key = f"{assay}_accession"
        if key in old:
            raise ValueError(f"duplicate GEO assay for library {library}")
        old[key] = sample["accession"]
    if not libraries or any(
        not {"gex_accession", "atac_accession"}.issubset(row) for row in libraries.values()
    ):
        raise ValueError("each GEO library needs both RNA and ATAC sample records")
    result = pd.DataFrame(libraries.values()).sort_values("library_id").reset_index(drop=True)
    if result.groupby("donor_id").condition.nunique().gt(1).any():
        raise ValueError("GEO donor labels disagree across libraries")
    return result


def normalize_metadata(
    frame: pd.DataFrame,
    *,
    condition_map: dict[str, int],
    age_unit: str = "unknown",
    age_source: str = "",
) -> pd.DataFrame:
    """Validate library-qualified identities and preserve documented age provenance."""
    result = frame.copy().reset_index(drop=True)
    if result.empty:
        raise ValueError("metadata is empty")
    for column in ("donor_id", "library_id", "barcode", "condition"):
        if column not in result or result[column].isna().any():
            raise ValueError(f"missing metadata identity: {column}")
        result[column] = result[column].astype(str)
        if result[column].str.strip().eq("").any():
            raise ValueError(f"empty metadata identity: {column}")
    if result.duplicated(["library_id", "barcode"]).any():
        raise ValueError("duplicate library/barcode keys")
    if not condition_map or any(value not in (0, 1) for value in condition_map.values()):
        raise ValueError("condition_map must explicitly map source labels to 0 or 1")
    result["label"] = result.condition.map(condition_map)
    if result.label.isna().any():
        raise ValueError("unknown condition label")
    result["label"] = result.label.astype(int)
    if result.groupby("donor_id").label.nunique().gt(1).any():
        raise ValueError("conflicting condition labels for a donor")
    result["cell_id"] = [
        json.dumps([library, barcode], separators=(",", ":"))
        for library, barcode in zip(result.library_id, result.barcode, strict=True)
    ]
    if "age_raw" not in result:
        result["age_raw"] = np.nan
    age = pd.to_numeric(result.age_raw, errors="coerce")
    valid = np.isfinite(age) & age.gt(0)
    documented = bool(age_source.strip())
    result["age_unit"] = age_unit
    result["age_source"] = age_source
    result["age_conversion"] = "unresolved"
    result["age_pcw"] = np.nan
    if documented and age_unit in ("PCW", "obstetric_GW"):
        converted = age - (2 if age_unit == "obstetric_GW" else 0)
        valid &= converted.gt(0)
        result.loc[valid, "age_pcw"] = converted[valid]
        result.loc[valid, "age_conversion"] = (
            "GW_minus_2_approximate" if age_unit == "obstetric_GW" else "identity_PCW"
        )
    if result.groupby("donor_id").age_pcw.nunique().gt(1).any():
        raise ValueError("conflicting developmental ages for a donor")
    return result


def age_overlap_summary(frame: pd.DataFrame, low: float = 13, high: float = 20) -> dict:
    """Count donors with documented ages inside inclusive canonical-PCW bounds."""
    if not np.isfinite([low, high]).all() or low > high:
        raise ValueError("invalid age range")
    donors = frame.groupby("donor_id").agg(label=("label", "first"), age=("age_pcw", "first"))
    kept = donors.loc[donors.age.between(low, high)]
    counts = {str(label): int(kept.label.eq(label).sum()) for label in (0, 1)}
    return {
        "status": "SUPPORTED" if all(counts.values()) else "NOT_APPLICABLE",
        "age_pcw_range": [low, high],
        "donors_per_class": counts,
        "unknown_age_donors": int(donors.age.isna().sum()),
        "excluded_donors": int(len(donors) - len(kept)),
        "support_is_not_power": True,
    }


def metadata_report(frame: pd.DataFrame, *, published_cells: int, expected_donors: int) -> dict:
    """Separate observed metadata counts from published and unverified retained counts."""
    if published_cells < 1 or expected_donors < 1:
        raise ValueError("published counts must be positive")
    donors = frame.drop_duplicates("donor_id")
    difference = len(frame) - published_cells
    return {
        "metadata_cells": len(frame),
        "published_cells": published_cells,
        "count_difference": difference,
        "retained_cells": None,
        "release_qc_status": "UNRESOLVED" if difference else "COUNT_MATCH_ONLY",
        "n_donors": len(donors),
        "expected_donors": expected_donors,
        "donor_count_matches": len(donors) == expected_donors,
        "donors_per_class": {str(v): int(donors.label.eq(v).sum()) for v in (0, 1)},
        "cells_per_class": {str(v): int(frame.label.eq(v).sum()) for v in (0, 1)},
        "n_libraries": int(frame.library_id.nunique()),
        "age_overlap": age_overlap_summary(frame),
        "specimen_independence": "UNRESOLVED",
        "confirmatory_ready": False,
    }
