# Data Card

**Data mode:** synthetic (primary) and legacy read-only (Tasic evidence only)
**Approval state:** blocked
**Real dataset matrices tracked:** none

## Synthetic fixture (verified)

Generator: `p22.testing.make_synthetic_multimodal`.

Default shape used in development: 12 donors × 20 cells, 3 classes, view_a
features, view_b features, float32, finite values, neutral identifiers
(`donor_*`, `cell_*`, `class_*`). Same seed reproduces identical arrays;
different seed changes them. Imperfect class signal plus donor nuisance are
injected on purpose. No biological gene, peak, or cohort names.

Shipped pilot config: `configs/toy_pilot.json` (synthetic only while approval is
blocked).

## Splits (verified)

Unit of split: donor. `make_donor_split` / `validate_donor_split` reject null
IDs, donor overlap, invalid fractions, and incomplete cell assignment. Label
balance is reported, not promised.

## Transforms (verified)

`fit_train_only` fits StandardScaler or PCA on training cell IDs only. Held-out
IDs are refused during fit. Fitted parameters are frozen for validation and
test. Metadata stores transformer class, parameters, training-ID hash, feature
count, timestamp, and package version.

## Legacy Tasic (verified boundary)

Tracked under `legacy/tasic_proxy_view/` with SHA-256 manifest. Both views come
from one RNA matrix. Projection was fitted before the split. Split and
intervals are cell-level. No donor grouping. No intervention test. Not
condition-specific evidence. See that README for evidence labels.

## Access and licence (unknown for any future real data)

No approved real dataset is present. Licence, controlled-access status, pairing
of modalities, and donor identifiers for any future cohort remain `unknown`
until a dated approval record and a passing preflight report exist.

## Generated outputs

Runs, reports, and executed notebooks: `reports/generated/` (ignored).
