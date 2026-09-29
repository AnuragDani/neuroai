# S7-v2 Checkpoint A — zero-fit implementation gate

Date: 2026-09-29. Gate only; **zero model fits**. Does not authorize T6+.

## Checks

| Check | Result | Evidence |
|---|---|---|
| T1–T3 focused tests | PASS **24 passed** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/test_nn_s7_setup.py -q` → 24 passed in 1.53s |
| `git diff --check` | PASS | exit 0 |
| V2 vs V1 scientific identity | PASS | See spec diff below |
| V1 ledger/result immutability | PASS | Live SHA256 fingerprints below; v2 durable root still absent |
| Fits attempted | **0** | No v2 durable root; no fit ledger rows |

## V2 vs V1 `BENCHMARK_SPEC.json` diff review

- V1 SHA256: `66225413f1cf7d5dae4f2a87af888deecce6124e4ea1514d2636d0d27b527ab1`
- V2 SHA256: `e8b127ad576a7a179532e830547d57010b7de2ac327983f49ba848928dfde88f`
- V2 `prior_spec_sha256` matches V1 SHA256.

**Identical scientific blocks:** `kind`, `hypothesis`, `scenario`, `generation`, `data`, `models`, `screen`, `pairing_pc`, `confirmation`, `evaluation` (including `margin=0.07`), and all non-split `training` hyperparameters (`split_seed=0`, model seed rule, folds/repeats, architecture, LR, epochs, patience, param_match). Screen seed `1001` and confirmation seeds `2001–2010` unchanged. Resource caps (fits, workers, hours, disk, RSS) unchanged except `resumption` wording for a fresh v2 ledger.

**Allowed / expected diffs only:**
- Identity: `id` → `S7_covariance_split_v2_20260929`; `base_commit` → `834b22d`
- Split/preflight: `training.split_method`, `outer_allocation`, `inner_allocation`, `split_validation`
- Paths/outputs: `outputs.*`, `supersedes`, `changes_from_v1`, `prior_spec_sha256`
- Scope/resumption prose for v2 path isolation and no reuse of INVALID v1 artifacts

**No** model family, margin, scenario, amplitude, seed list, or screen/PC/confirmation rule changes. Checkpoint A does **not** require scenario/threshold retuning → proceed to T4.

## V1 immutable fingerprints (live 2026-09-29)

| Path | SHA256 |
|---|---|
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/ledger/fit_ledger.jsonl` | `5e23387a3ad5c75f70d6926e5de7f2848e5363b820dedac21a92288a4657d2a8` |
| `…/ledger/provenance.json` | `d9e941d24cb0e28ee5baca8b0fdbec0233a3a84a001f135eeee7412af8a62888` |
| `…/ledger/RUN_INVALID.txt` | `0e4baa8272e1b69d17cd13ccb0e9d4d1ce9dd8279874c7e8699a2fc3bbb57143` |
| `…/split_class_blocker_evidence.json` | `415b3deee7719dd901d24a021326baa43f112754d9b7d2f60f8ef8bb474c8e87` |
| `docs/nn_v2/s7/S7_RESULT.md` | `d9ae29df8b4e86093e926248c1224e5216a746d37a9dc9135e0df0adb8d51222` |
| `docs/nn_v2/s7/S7_RESULT.json` | `8456440992a21355849b9a8738c558200c3d583cbe0bffb0f9199e595dc244d9` |

V2 durable root `nn_s7_covariance_split_v2_20260929` does **not** exist yet (expected until T5 live preflight).

## Gate decision

**PASS — Checkpoint A.** T4 (executed-path audit) may start. No fits authorized until T5 `55/55` no-fit preflight and Checkpoint B freeze.
