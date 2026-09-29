# S7-v2 Checkpoint B — immutable fit-authorization freeze

Date: 2026-09-29. Gate after T5 `55/55` no-fit PASS. **Zero model fits at freeze.** Authorizes **T6 smoke only** (`≤14` fits via `--split-v2 --once`). Does not authorize screen/PC/confirmation until T6 acceptance.

Machine record: [CHECKPOINT_B.json](CHECKPOINT_B.json).

## Freeze identity

| Field | Value |
|---|---|
| Git branch | `codex/p22-s7-v2-plan-20260929` |
| Git commit | `a363826f01504d57cdea768937a2a20451366e7f` |
| Worktree | clean at freeze (Checkpoint B docs added after measurement) |
| Protocol ID | `S7_covariance_split_v2_20260929` |
| Durable root | `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929` |

## Exact next command (T6)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/run_nn_s7_covariance.py --split-v2 --once
```

Prior no-fit command (already PASS): `--split-v2 --preflight-only`.

## Frozen hashes (from live `ledger/provenance.json`)

| Artifact | SHA256 |
|---|---|
| V2 `BENCHMARK_SPEC.json` | `e8b127ad576a7a179532e830547d57010b7de2ac327983f49ba848928dfde88f` |
| Split manifest content (`split_manifest_sha256`, excludes self-hash + recount) | `9a845b5c0b8622624a40dc0cee6771d5d567e8c288c0be1f23bfcfd75668e2be` |
| On-disk `split_manifest_v2.json` file | `8ef4aa58bca3e7b7e68cc78664dd36b54c6c390c933400a3ee460bcb824818c4` |
| V2 `ledger/provenance.json` file | `52cde0ba8b3aabf107647ae7435ce5a00f728ed2bd8d0333d7e5da6ad9b6f6b4` |

**Inputs** (`input_sha256`):

| Key | SHA256 |
|---|---|
| `h5ad` | `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb` |
| `nn_inputs_config` | `45d9b540d2a1c906879867003a488e7a54a9e4818a82f776b91643f77ae9f766` |
| `region_sets_sha256_json` | `13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407` |
| `tracked_union_bed` | `d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23` |
| `atac_tiebreak_counts` | `5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969` |

**Fitting sources** (`source_sha256`, 13 files — live rehash matched provenance at freeze):

| File | SHA256 |
|---|---|
| `loop.py` | `195274bf29284e17746bef20020394737d175666361c5537fb0cdac1df347c1a` |
| `multiome_runner.py` | `119f93e269eee11a27b93e29f1c85a192b25793d9fad28e546bba99c93abd0b5` |
| `planted_signal.py` | `a3a6a7f3e5e5550038a38d9e5bff15abd09486d6b238f23c0bfa182cef8e3a5e` |
| `s7_confirm_exec.py` | `45e15aa402739cd18aa6bda3c1cfbfc4680714a9763047b0be2d0cb57bb85dde` |
| `s7_confirmation.py` | `0167290a59a4f7e0a44fedc072cc64a40555e987884648c2e399303ae55ae073` |
| `s7_handoff.py` | `16d9240648d3ba5bf7b8f64845105d7f7b798d1835d0758bb71445f4213393ac` |
| `s7_ledger.py` | `e018cd03d5ea9353a10f71afd8b636576f4e0a50207b84d5624a8890a93467f7` |
| `s7_pairing.py` | `6475afd4d3d9e21ded6ce73b61e629a21ab10b8a11977cb2b56ed83652cef61e` |
| `s7_pairing_exec.py` | `75cfefc6ad0c673540c7c9676f07fa161a8ea1d97f29009b5fa2206effdc3e1b` |
| `s7_pipeline.py` | `72e701d04d9ab0ad8fc6b7a6692732cb77fbec2a12f66d052e77122c1f6d2dad` |
| `s7_runner.py` | `b86a495a66771b8b736dbd4aba61d12b2b603d73a6138f406e24e37b4679d6e9` |
| `s7_screen.py` | `96c829566877b64faba284b087253f34a8d0b91af858c2c498d24c71e8a78cb3` |
| `s7_setup.py` | `a309e205293dffcddd30eb3aaa31f332fc5ea8b1e5e80e35601eee411ace07b3` |

## No-fit gate

| Check | Result |
|---|---|
| V2 `fit_ledger.jsonl` | **absent** → 0 fit rows |
| V2 checkpoints | `[]` |
| Split manifest | `ok=true`, `n_triplets=55`, independent recount `ok=true` |
| T5 evidence | [T5_LIVE_NOFIT_PREFLIGHT.md](T5_LIVE_NOFIT_PREFLIGHT.md) PASS |
| Focused tests | `pytest tests/test_nn_s7_setup.py -q` → **24 passed** |
| `git diff --check` | clean |
| V1 `fit_ledger.jsonl` | `5e23387a3ad5c75f70d6926e5de7f2848e5363b820dedac21a92288a4657d2a8` (unchanged) |
| V1 `provenance.json` | `d9e941d24cb0e28ee5baca8b0fdbec0233a3a84a001f135eeee7412af8a62888` (unchanged) |

## Resource snapshot at freeze

| Resource | Value | Cap / gate |
|---|---|---|
| Free disk | **26.771 GiB** | ≥11 GiB required |
| RSS baseline (fresh idle venv python, `ps`) | **14.734 MiB** (15088 KiB) | ≤32 GiB RSS |
| `ru_maxrss` (macOS bytes) | 15450112 | informational |
| Artifact budget | 0 GiB used at freeze | ≤2 GiB |
| Absolute fit ceiling | — | ≤480; smoke ≤14 |

## Freeze rule

Fitting sources listed above are frozen before T6. **Any post-fit change** to those sources (or to frozen spec/input/split hashes) marks the v2 run **`INVALID`**; preserve completed artifacts and do **not** start a replacement batch within this GNHF task. Never overwrite v1. No retuning, seed search, real-label fits, push, or merge.

## Gate decision

**PASS — Checkpoint B.** T6 smoke (`--split-v2 --once`, ≤14 fits) may start under frozen hashes and resource caps. Screen/PC/confirmation remain blocked until T6 acceptance.
