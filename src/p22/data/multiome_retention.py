"""Join the pinned final CELLxGENE release to raw GEO libraries without reading X."""

import hashlib

import h5py
import numpy as np
import pandas as pd
from anndata.io import read_elem

from p22.data.multiome import ReadBudget, normalize_metadata, verified_asset_path


def read_retained_release(spec: dict, budget: ReadBudget, libraries: pd.DataFrame):
    """Read only identity columns; bound row count before materializing metadata.

    Uses installed AnnData 0.12's encoded-element reader, not a full AnnData load:
    https://anndata.readthedocs.io/en/0.12.x/generated/anndata.io.read_elem.html
    """
    if "member" in spec:
        raise ValueError("retained release must be a standalone H5AD")
    path = verified_asset_path(spec, budget)
    with h5py.File(path, "r") as handle:
        obs = handle["obs"]
        index = obs.attrs["_index"]
        if not 0 < len(obs[index]) <= 1_000_000:
            raise ValueError("retained metadata row budget exceeded")
        frame = pd.DataFrame(
            {
                name: read_elem(obs[source])
                for name, source in {
                    "release_cell_id": index,
                    "library_id": "library",
                    "donor_id": "donor_id",
                    "condition": "group",
                }.items()
            }
        )
    if frame.release_cell_id.isna().any() or frame.release_cell_id.duplicated().any():
        raise ValueError("retained release IDs must be unique and non-null")
    prefixes = frame.library_id.astype(str) + "_"
    if not all(
        str(cell).startswith(prefix)
        for cell, prefix in zip(frame.release_cell_id, prefixes, strict=True)
    ):
        raise ValueError("retained cell ID must carry its explicit library prefix")
    frame["barcode"] = [
        str(cell)[len(prefix) :]
        for cell, prefix in zip(frame.release_cell_id, prefixes, strict=True)
    ]
    frame = normalize_metadata(frame, condition_map={"CON": 0, "DS": 1})
    observed = frame.groupby("library_id").agg(
        retained_cells=("cell_id", "size"),
        donor_id=("donor_id", "first"),
        condition=("condition", "first"),
    )
    if frame.groupby("library_id").donor_id.nunique().gt(1).any():
        raise ValueError("GEO retained library has conflicting donors")
    geo = libraries.set_index("library_id")
    if not set(observed.index).issubset(geo.index):
        raise ValueError("retained library missing from GEO")
    for column in ("donor_id", "condition"):
        if not np.array_equal(observed[column], geo.loc[observed.index, column]):
            raise ValueError(f"retained release and GEO disagree on {column}")
    counts = libraries.copy()
    counts["retained_cells"] = counts.library_id.map(observed.retained_cells).fillna(0).astype(int)
    counts["flag_agrees_with_release"] = counts.in_final_analysis.eq(counts.retained_cells.gt(0))
    return frame, {
        "release_cells": len(frame),
        "release_donors": int(frame.donor_id.nunique()),
        "release_libraries": len(observed),
        "library_manifest": counts.to_dict(orient="records"),
        "final_flag_donors_absent_from_release": sorted(
            set(libraries.loc[libraries.in_final_analysis, "donor_id"]) - set(frame.donor_id)
        ),
        "release_flag_status": "MATCH" if counts.flag_agrees_with_release.all() else "UNRESOLVED",
        "status_note": "Exact release membership, not an explanation of source QC differences",
    }


def retained_mask(raw_metadata: pd.DataFrame, retained: pd.DataFrame):
    """Require every final-release cell in the selected library; reject donor/label drift."""
    libraries = raw_metadata.library_id.unique()
    if len(libraries) != 1 or raw_metadata.cell_id.duplicated().any():
        raise ValueError("retention join requires one library with unique cell IDs")
    final = retained.loc[retained.library_id.eq(libraries[0])].set_index("cell_id")
    raw = raw_metadata.set_index("cell_id")
    if set(final.index) - set(raw.index):
        raise ValueError("retained cells missing from raw matrix")
    for column in ("donor_id", "label"):
        if not np.array_equal(raw.loc[final.index, column], final[column]):
            raise ValueError(f"retained and raw {column} disagree")
    return raw_metadata.cell_id.isin(final.index).to_numpy(), {
        "status": "EXACT_RELEASE_JOIN",
        "retained_cells": len(final),
        "raw_only_cells": len(raw) - len(final),
        "retained_missing_raw": 0,
        "retained_release_cell_ids_sha256": hashlib.sha256(
            "\n".join(sorted(final.release_cell_id)).encode()
        ).hexdigest(),
    }
