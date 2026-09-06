"""Interval equality is necessary; overlapping peaks do not imply exact shared counts."""

import pytest

from p22.data.atac_features import audit_peak_spaces


def audit(left, right, **kwargs):
    return audit_peak_spaces(
        {"left": left, "right": right},
        genome_builds={"left": "GRCh38", "right": "GRCh38"},
        count_units={"left": "tn5_insertions", "right": "tn5_insertions"},
        **kwargs,
    )


def test_overlapping_intervals_need_recount_and_missing_is_not_zero():
    report = audit(["chr1:0-10", "chr1:10-20"], ["chr1:5-15", "chr1:10-20"])
    assert report["status"] == "NEEDS_RECOUNT"
    assert report["n_exact_common_regions"] == 1
    assert report["unmeasured_regions"] == {"left": 1, "right": 1}
    assert report["zero_fill_allowed"] is False
    assert report["exact_projection_possible"] is False


def test_matching_regions_alone_do_not_pass_provenance_gate():
    report = audit(["chr1:0-10"], ["chr1:0-10"])
    assert report["status"] == "INCONCLUSIVE"


def test_exact_reference_features_pass_independent_of_row_order():
    report = audit(
        ["chr1:0-10", "chr2:0-10"],
        ["chr2:0-10", "chr1:0-10"],
        reference={"kind": "fixed_reference", "source": "https://example.org/v1"},
    )
    assert report["status"] == "PASS"
    assert len(report["common_regions_sha256"]) == 64
    assert report["row_order_identical"] is False


@pytest.mark.parametrize("region", ["chr1:2-1", "chr1:-1-3", "not-a-region"])
def test_bad_regions_fail(region):
    with pytest.raises(ValueError):
        audit([region], ["chr1:0-10"])


def test_count_units_and_build_must_match():
    result = audit_peak_spaces(
        {"left": ["chr1:0-10"], "right": ["chr1:0-10"]},
        genome_builds={"left": "GRCh37", "right": "GRCh38"},
        count_units={"left": "fragments", "right": "tn5_insertions"},
    )
    assert result["status"] != "PASS"
