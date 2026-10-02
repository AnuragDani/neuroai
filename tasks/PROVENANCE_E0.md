# E0 portable provenance — 2026-10-02

**Disposition:** `PORTABLE_PROVENANCE_PASS`

Canonical measured inputs and pilot sidecars resolve under the primary
checkout. Former worktree absolute paths are provenance records only;
hashed consolidation archives remain the immutable secondary source.

## Checks

- Canonical paths without worktrees: `True`
- Archive hashes OK (28/28): `True`
- Pilot sidecars retain exact hashes (30/30): `True`
- Live worktrees absent: `True` (28/28)
- Research fits this stage: `0`

## Measured digests

- ATAC matrix match: `True` (`5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969`)
- Union BED match: `True`
- Region sets match: `True`
- Ordered cells (counts.json) match: `True`
- Former worktree ATAC resolves: `False`

## Scientific labels preserved

- `masked_atac_m9`: **NOT_AUTHORIZED**
- `primary`: **B_NULL**
- `prior_S10_S9_S7`: **INVALID**
- `prior_S8`: **NO FIT**

## Missing older live dependencies

- `all_28_secondary_worktrees`: removed; preserved as hashed tar archives under reports/generated/consolidation_20261002/
- `ordered_cells_txt`: never shipped beside counts.npz; ordered-cell SHA is pinned via counts.json cells_sha256 and H5AD obs_names

## Contract

- `configs/execution_repair_portable_inputs_2026-10-02.json`
- Report JSON: `tasks/provenance_e0.json`

No research fits. E1 next.
