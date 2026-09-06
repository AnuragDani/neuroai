"""Tiny fixtures prove ingestion contracts, not biological results."""

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
