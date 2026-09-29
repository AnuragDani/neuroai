# T5 live no-fit preflight — S7-v2

Updated: 2026-09-29. Evidence for [TODO T5](../../../tasks/nn/s7_v2/TODO.md). Zero model fits.

## Decision

**PASS** — 55/55 train/val/test triplets class-valid; v2 ledger has zero fit rows; v1 ledger/provenance unchanged; disk/path gates pass.

## Command

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/run_nn_s7_covariance.py --split-v2 --preflight-only
```

Exit 0; `action=preflight_only`.

## Gates

| Check | Result |
|---|---|
| split_manifest_ok / independent recount | `True` / `True` |
| n_seeds × n_triplets | 11 × 55 (expected 11 × 55) |
| All partitions 16/8/6 + both classes | `True` |
| Seed 1001 fold-0 test classes (v1 was 6/0) | `{'0': 4, '1': 2}` |
| CA/TC param match (≤10%) | matched=`True`, relative_error=`0.011752` |
| Free disk ≥11 GiB | free_gib=`26.647`, ok=`True` |
| V2 fit ledger rows | `0` (fit_ledger exists=`False`) |
| V2 checkpoints | `[]` |
| V1 fit_ledger sha256 | `5e23387a3ad5c75f70d6926e5de7f2848e5363b820dedac21a92288a4657d2a8` (unchanged=`True`) |
| V1 provenance sha256 | `d9e941d24cb0e28ee5baca8b0fdbec0233a3a84a001f135eeee7412af8a62888` (unchanged=`True`) |
| Path separation v1≠v2 | `True` |
| split_manifest_sha256 | `9a845b5c0b8622624a40dc0cee6771d5d567e8c288c0be1f23bfcfd75668e2be` |

## Artifacts

- Durable root: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929`
- Manifest: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/split_manifest_v2.json`
- Preflight: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/preflight.json`
- Resources: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/resources_preflight.json`
- Provenance (frozen, zero fits): `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/ledger/provenance.json`
- Screen split log: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/split_logs/split_log_seed_1001.json`
- Worktree pointer: `reports/generated/nn_s7_covariance_split_v2_20260929/preflight_pointer.json`
- Machine audit: [T5_LIVE_NOFIT_PREFLIGHT.json](T5_LIVE_NOFIT_PREFLIGHT.json)

## Independent partition summary

All 55 partitions re-parsed from the saved manifest. Problems: `none`.

Seed 1001 outer test class counts by fold: [{'0': 4, '1': 2}, {'0': 3, '1': 3}, {'0': 3, '1': 3}, {'0': 3, '1': 3}, {'0': 3, '1': 3}].

## Authorization note

T5 PASS authorizes **Checkpoint B** recording only. No smoke/screen/confirmation fits until Checkpoint B freeze evidence is recorded. No retuning; biological primary remains `B_NULL`.
