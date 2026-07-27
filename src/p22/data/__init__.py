"""Data contracts: donor-aware splitting and train-only transforms."""

from p22.data.splits import (
    DonorSplit,
    donor_split_problems,
    make_donor_split,
    validate_donor_split,
)

__all__ = [
    "DonorSplit",
    "donor_split_problems",
    "make_donor_split",
    "validate_donor_split",
]
