"""Tiny fixtures prove ingestion contracts, not biological results."""

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile

import numpy as np
import pandas as pd
import pytest

from p22.data.multiome import age_overlap_summary, metadata_report, normalize_metadata


def metadata():
    return pd.DataFrame(
        {
            "donor_id": ["A", "A", "B"],
            "library_id": ["L1", "L2", "L3"],
            "barcode": ["AA", "AA", "BB"],
            "condition": ["Ctrl", "Ctrl", "Ts21"],
            "age_raw": [15, 15, 22],
        }
    )


def normalized(frame=None, **kwargs):
    return normalize_metadata(
        metadata() if frame is None else frame,
        condition_map={"Ctrl": 0, "Ts21": 1},
        **({"age_unit": "obstetric_GW", "age_source": "documented LMP"} | kwargs),
    )


def test_age_conversion_preserves_original_and_boundaries():
    result = normalized()
    assert result.age_raw.tolist() == [15, 15, 22]
    assert result.age_pcw.tolist() == [13, 13, 20]
    assert result.age_conversion.eq("GW_minus_2_approximate").all()
    assert age_overlap_summary(result)["donors_per_class"] == {"0": 1, "1": 1}
    assert age_overlap_summary(result)["status"] == "SUPPORTED"
    assert normalized(age_unit="PCW").age_pcw.tolist() == [15, 15, 22]


@pytest.mark.parametrize(
    "unit,source", [("GW", "paper"), ("obstetric_GW", ""), ("unknown", "paper")]
)
def test_age_ambiguous_units_remain_unresolved(unit, source):
    result = normalized(age_unit=unit, age_source=source)
    assert result.age_pcw.isna().all()
    assert age_overlap_summary(result)["status"] == "NOT_APPLICABLE"


def test_age_missing_does_not_convert_to_zero():
    frame = metadata()
    frame.loc[2, "age_raw"] = np.nan
    assert np.isnan(normalized(frame).age_pcw.iloc[2])


def test_manifest_reports_count_gap_without_deleting_cells():
    result = normalized()
    report = metadata_report(result, published_cells=2, expected_donors=2)
    assert report["metadata_cells"] == 3
    assert report["published_cells"] == 2
    assert report["count_difference"] == 1
    assert report["release_qc_status"] == "UNRESOLVED"
    assert report["donors_per_class"] == {"0": 1, "1": 1}
    assert report["retained_cells"] is None
    assert len(result) == 3


@pytest.mark.parametrize("failure", ["duplicate", "conflict", "missing", "unknown_label"])
def test_manifest_rejects_ambiguous_identity(failure):
    frame = metadata()
    if failure == "duplicate":
        frame.loc[1, "library_id"] = "L1"
    elif failure == "conflict":
        frame.loc[1, "condition"] = "Ts21"
    elif failure == "missing":
        frame.loc[1, "donor_id"] = None
    else:
        frame.loc[1, "condition"] = "unknown"
    with pytest.raises(ValueError):
        normalized(frame)


def geo_soft(atac_donor="donor1"):
    return "\n".join(
        f"^SAMPLE = GSM{i}\n!Sample_title = fetal brain, Library L1_{kind}, assay\n"
        f"!Sample_characteristics_ch1 = name: {donor}\n"
        "!Sample_characteristics_ch1 = group: CON\n"
        "!Sample_characteristics_ch1 = dev stage_pcw: 10\n"
        "!Sample_characteristics_ch1 = in final_analysis: TRUE\n"
        for i, kind, donor in ((1, "atac", atac_donor), (2, "gex", "donor1"))
    )


def test_manifest_geo_libraries_pair_assays_without_counting_two_donors():
    from p22.data.multiome import parse_geo_libraries

    libraries = parse_geo_libraries(geo_soft())
    assert len(libraries) == 1
    assert libraries.iloc[0].donor_id == "donor1"
    assert libraries.iloc[0].gex_accession == "GSM2"
    assert libraries.iloc[0].atac_accession == "GSM1"
    assert libraries.iloc[0].in_final_analysis


def test_manifest_geo_libraries_reject_disagreeing_assays():
    from p22.data.multiome import parse_geo_libraries

    with pytest.raises(ValueError, match="disagree"):
        parse_geo_libraries(geo_soft(atac_donor="other"))


def test_manifest_geo_libraries_reject_missing_assay():
    from p22.data.multiome import parse_geo_libraries

    with pytest.raises(ValueError, match="both"):
        parse_geo_libraries(geo_soft().split("^SAMPLE = GSM2")[0])


def asset(path, data, **extra):
    path.write_bytes(data)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_url": "https://example.org/public-fixture",
        **extra,
    }


def test_asset_checksum_and_gzip_budget(tmp_path):
    from p22.data.multiome import ReadBudget, read_asset

    spec = asset(tmp_path / "table.gz", gzip.compress(b"hello"))
    budget = ReadBudget(max_input_bytes=1000, max_expanded_bytes=5)
    assert read_asset(spec, budget) == b"hello"
    assert budget.expanded_bytes == 5
    assert budget.records[0]["sha256"] == spec["sha256"]
    with pytest.raises(ValueError, match="expanded"):
        read_asset(spec, ReadBudget(max_expanded_bytes=4))
    with pytest.raises(ValueError, match="input"):
        read_asset(spec, ReadBudget(max_input_bytes=1))
    with pytest.raises(ValueError, match="checksum"):
        read_asset(spec | {"sha256": "0" * 64}, ReadBudget())


def test_asset_reads_nested_gzip_without_extracting(tmp_path):
    from p22.data.multiome import ReadBudget, read_asset

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        data = gzip.compress(b"hello")
        member = tarfile.TarInfo("folder/metadata.csv.gz")
        member.size = len(data)
        archive.addfile(member, io.BytesIO(data))
    spec = asset(tmp_path / "public.tar", buffer.getvalue(), member=member.name)
    assert read_asset(spec, ReadBudget()) == b"hello"
    assert not (tmp_path / "folder").exists()


@pytest.mark.parametrize("unsafe", ["../escape", "/absolute", "symlink", "duplicate"])
def test_asset_rejects_unsafe_archives(tmp_path, unsafe):
    from p22.data.multiome import ReadBudget, read_asset

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo(unsafe)
        if unsafe == "symlink":
            member.type, member.linkname = tarfile.SYMTYPE, "target"
        archive.addfile(member)
        if unsafe == "duplicate":
            archive.addfile(member)
    spec = asset(tmp_path / "bad.tar", buffer.getvalue(), member=unsafe)
    with pytest.raises(ValueError, match="unsafe|duplicate"):
        read_asset(spec, ReadBudget())


def mex_assets(tmp_path, prefix="", *, matrix=None, features=None, barcodes="AA\nBB\n"):
    return {
        "matrix": asset(
            tmp_path / f"{prefix}matrix.mtx",
            (
                matrix
                or "%%MatrixMarket matrix coordinate integer general\n3 2 3\n1 1 2\n2 2 3\n3 1 4\n"
            ).encode(),
        ),
        "features": asset(
            tmp_path / f"{prefix}features.tsv",
            (
                features
                or "gene1\tG1\tGene Expression\nchr1:0-5\tchr1:0-5\tPeaks\n"
                "chr1:5-10\tchr1:5-10\tPeaks\n"
            ).encode(),
        ),
        "barcodes": asset(tmp_path / f"{prefix}barcodes.tsv", barcodes.encode()),
    }


def test_mex_combined_and_separate_layouts_give_same_paired_cells(tmp_path):
    from scipy import sparse

    from p22.data.multiome import ReadBudget, load_mex, pair_and_cap

    meta = normalized(metadata().iloc[[0, 2]])
    combined = load_mex(mex_assets(tmp_path), ReadBudget())
    paired = pair_and_cap(combined, None, meta, cap=1)
    assert sparse.isspmatrix_csr(paired["rna"])
    assert paired["rna"].toarray().tolist() == [[2], [0]]
    assert paired["atac"].toarray().tolist() == [[0, 4], [3, 0]]
    rna = load_mex(
        mex_assets(
            tmp_path,
            "r",
            matrix="%%MatrixMarket matrix coordinate integer general\n1 2 1\n1 1 2\n",
            features="gene1\tG1\n",
        ),
        ReadBudget(),
        modality="Gene Expression",
    )
    atac = load_mex(
        mex_assets(
            tmp_path,
            "a",
            matrix="%%MatrixMarket matrix coordinate integer general\n2 2 2\n1 2 3\n2 1 4\n",
            features="chr1:0-5\tchr1:0-5\nchr1:5-10\tchr1:5-10\n",
        ),
        ReadBudget(),
        modality="Peaks",
    )
    split = pair_and_cap(rna, atac, meta, cap=1)
    assert (split["rna"] != paired["rna"]).nnz == 0
    assert (split["atac"] != paired["atac"]).nnz == 0


@pytest.mark.parametrize(
    "bad", ["shape", "negative", "fraction", "duplicate", "dense", "barcodes", "budget"]
)
def test_mex_rejects_invalid_counts_before_pairing(tmp_path, bad):
    from p22.data.multiome import ReadBudget, load_mex

    matrix = "%%MatrixMarket matrix coordinate integer general\n3 2 1\n1 1 1\n"
    if bad == "shape":
        matrix = matrix.replace("3 2 1", "900000000 2 1")
    elif bad == "negative":
        matrix = matrix.replace("1 1 1", "1 1 -1")
    elif bad == "fraction":
        matrix = matrix.replace("integer", "real").replace("1 1 1", "1 1 0.5")
    elif bad == "duplicate":
        matrix = matrix.replace("3 2 1", "3 2 2") + "1 1 1\n"
    elif bad == "dense":
        matrix = "%%MatrixMarket matrix array integer general\n3 2\n1\n1\n1\n1\n1\n1\n"
    spec = mex_assets(
        tmp_path, matrix=matrix, barcodes="AA\nAA\n" if bad == "barcodes" else "AA\nBB\n"
    )
    with pytest.raises(ValueError):
        load_mex(spec, ReadBudget(), max_nnz=0 if bad == "budget" else 100)


def test_mex_refuses_mismatched_barcode_order(tmp_path):
    from p22.data.multiome import ReadBudget, load_mex, pair_and_cap

    combined = load_mex(mex_assets(tmp_path), ReadBudget())
    reverse = load_mex(mex_assets(tmp_path, "other", barcodes="BB\nAA\n"), ReadBudget())
    with pytest.raises(ValueError, match="ordered barcodes"):
        pair_and_cap(combined, reverse, normalized(metadata().iloc[[0, 2]]), cap=1)


def test_mex_preserves_six_column_arc_coordinates(tmp_path):
    from p22.data.multiome import ReadBudget, load_mex

    spec = mex_assets(
        tmp_path,
        features=(
            "gene1\tG1\tGene Expression\tchr1\t0\t10\n"
            "chr1:0-5\tchr1:0-5\tPeaks\tchr1\t0\t5\n"
            "chr1:5-10\tchr1:5-10\tPeaks\tchr1\t5\t10\n"
        ),
    )
    block = load_mex(spec, ReadBudget())
    assert block["features"].chromosome.tolist() == ["chr1"] * 3
    assert block["features"].start.tolist() == [0, 0, 5]


def test_mex_preserves_unmapped_rna_but_rejects_unmapped_peaks(tmp_path):
    from p22.data.multiome import ReadBudget, load_mex

    features = (
        "gene1\tMT-ND1\tGene Expression\t\t-1\t-1\n"
        "chr1:0-5\tchr1:0-5\tPeaks\tchr1\t0\t5\n"
        "chr1:5-10\tchr1:5-10\tPeaks\tchr1\t5\t10\n"
    )
    spec = mex_assets(tmp_path, features=features)
    block = load_mex(spec, ReadBudget())
    assert not block["features"].coordinates_known.iloc[0]
    assert block["features"].start.iloc[0] == -1
    bad = mex_assets(tmp_path, "bad", features=features.replace("Gene Expression", "Peaks"))
    with pytest.raises(ValueError, match="intervals"):
        load_mex(bad, ReadBudget())


def test_public_audit_cli_reports_blockers_without_training_or_overwrite(tmp_path):
    import p22

    manifest = {
        "schema_version": 1,
        "geo": {
            "soft": asset(tmp_path / "family.soft", geo_soft().encode()),
            "published_donors": 1,
            "published_cells": 2,
            "pilot_library": "L1",
            "combined_mex": mex_assets(tmp_path),
            "comparison_library": "L2",
            "comparison_features": mex_assets(tmp_path, "compare")["features"],
        },
        "external": {
            "metadata": asset(tmp_path / "metadata.csv", metadata().to_csv(index=False).encode()),
            "published_donors": 2,
            "published_cells": 2,
            "condition_map": {"Ctrl": 0, "Ts21": 1},
            "columns": {},
            "age_unit": "obstetric_GW",
            "age_source": "documented LMP",
        },
    }
    config = tmp_path / "manifest.json"
    config.write_text(json.dumps(manifest))
    output = tmp_path / "audit"
    command = [
        sys.executable,
        str(p22.REPO_ROOT / "scripts/audit_multiome.py"),
        "--manifest",
        str(config),
        "--output-dir",
        str(output),
        "--cell-cap",
        "1",
    ]
    approvals_before = p22.APPROVALS_PATH.read_bytes()
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads((output / "audit.json").read_text())
    assert report["preflight_status"] == "COMPLETED"
    assert report["training_allowed"] is False
    assert report["external"]["count_difference"] == 1
    assert report["pilot"]["selected_cells"] == 1
    assert report["pilot"]["data_kind"] == "raw_library_not_final_qc"
    assert report["resources"]["elapsed_seconds"] >= 0
    assert (output / "SUMMARY.md").is_file()
    assert (output / "manifest.json").read_bytes() == config.read_bytes()
    assert p22.APPROVALS_PATH.read_bytes() == approvals_before
    before = (output / "audit.json").read_bytes()
    second = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert second.returncode != 0
    assert (output / "audit.json").read_bytes() == before


def test_asset_pax_headers_cannot_bypass_expansion_budget(tmp_path):
    from p22.data.multiome import ReadBudget, read_asset

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        member = tarfile.TarInfo("metadata.csv")
        member.size = 1
        member.pax_headers = {"comment": "x" * 5_000_000}
        archive.addfile(member, io.BytesIO(b"x"))
    spec = asset(tmp_path / "pax.tar.gz", gzip.compress(buffer.getvalue()), member=member.name)
    with pytest.raises(ValueError, match="expanded"):
        read_asset(spec, ReadBudget(max_expanded_bytes=16384))


@pytest.mark.parametrize("value", [True, 0, -1, 1.5, float("inf"), float("nan")])
def test_limits_and_published_counts_need_positive_integers(tmp_path, value):
    from p22.data.multiome import ReadBudget, load_mex

    with pytest.raises(ValueError):
        ReadBudget(max_input_bytes=value)
    with pytest.raises(ValueError):
        metadata_report(normalized(), published_cells=value, expected_donors=2)
    with pytest.raises(ValueError):
        metadata_report(normalized(), published_cells=3, expected_donors=value)
    with pytest.raises(ValueError):
        load_mex(mex_assets(tmp_path), ReadBudget(), max_nnz=value)


def test_budget_counters_cannot_be_injected():
    from p22.data.multiome import ReadBudget

    with pytest.raises(TypeError):
        ReadBudget(input_bytes=-1_000_000)


def test_manifest_preserves_valid_multiplexed_library():
    frame = metadata().iloc[[0, 2]].copy()
    frame["library_id"] = "GEM6"
    result = normalized(frame)
    assert result.donor_id.nunique() == 2
    assert result.library_id.nunique() == 1


def test_public_audit_cli_records_truncated_input_failure(tmp_path):
    import p22

    manifest = {
        "schema_version": 1,
        "external": {},
        "geo": {"soft": asset(tmp_path / "truncated.gz", b"\x1f\x8b\x08")},
    }
    config = tmp_path / "manifest.json"
    config.write_text(json.dumps(manifest))
    output = tmp_path / "failure"
    result = subprocess.run(
        [
            sys.executable,
            str(p22.REPO_ROOT / "scripts/audit_multiome.py"),
            "--manifest",
            str(config),
            "--output-dir",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2, result.stderr
    report = json.loads((output / "audit.json").read_text())
    assert report["preflight_status"] == "FAILED"
    assert report["training_allowed"] is False
