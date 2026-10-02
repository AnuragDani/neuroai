# M10 — Saved-prediction replay (diagnostic only)

**Disposition:** `REPLAY_PASS_DIAGNOSTIC_ONLY`
**Prospective executor-review gate:** `FAIL` (reviewer `68919dae-61a9-4c39-80f7-5ad0845bbc03`)
**Scientific acceptance of M9:** `NOT_AUTHORIZED`
**Fits run this step:** `0` (counters preserved: `True`)

## Scope

Independent recomputation of donor-average cell log-loss and frozen TC−CA contrast from the 25 main + 5 smoke prediction sidecars. No fitting, no counter reset, no M8 lock mutation. Numerical agreement with EXECUTE.json is **diagnostic only** under prospective gate FAIL.

## Coverage and pins

- Pre-replay pins rematch: `True` (35 digests)
- Main 25/25 equality+loss rematch: `True`
- Smoke 5/5 equality+loss rematch: `True`
- EXECUTE primary rematch: `True`
- Counter SHA before/after: `2b4bd43c81460a7945bd5374ab2822d6bbf3440031f00639313387170857112a`

## Primary contrast (diagnostic)

- Pooled TC−CA: `0.00153716` (n_donors=30)
- Bootstrap 95% CI (seed 601001): `[-0.00219657, 0.00474564]`
- Practical margin: `0.01`
- Exploratory advantage observed: `False`
- Per-fold estimates: `{'0': 0.006530094299048078, '1': 0.0009365928300419935, '2': 0.003731936866460006, '3': 0.0029032177983771834, '4': -0.006416020028498726}`

## Resources

- Attempts: `30/40` (smoke 5; scientific 25; failed 0)
- Fitting hours (ledger): `0.0017774834488874247`
- Artifact bytes (live du): `0.012081` GiB (12668 KiB); counter field `0.0`

## Claim limits

- Claim level 2 computational prediction only.
- Does **not** authorize scientific PASS of M9.
- Does **not** promote biological state, causal mechanism, or external validation.
- Prior S10/S9/S7 `INVALID`, S8 `NO FIT`, primary `B_NULL`, Q2 `ENDPOINT_UNRESOLVED` unchanged.

Machine-readable: [REPLAY.json](REPLAY.json). Coverage: [M10_COVERAGE_REVIEW.json](M10_COVERAGE_REVIEW.json).
