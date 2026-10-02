# M0 Preflight — masked ATAC computational pilot 2026-10-01

**Disposition:** M0 PASS (no fits, no downloads, no package installs, no scientific gate edits, no vault/MOM/sent-packet edits).  
**Recorded:** 2026-10-01 (local worktree clock).  
**Scope:** provenance, owned-file copy, root plan/checklist append, runtime/input/raw availability, new output root. M1+ deferred.

## Identity

| Item | Value |
|---|---|
| Worktree path | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/masked-atac-20261001` |
| Branch | `gnhf/execute-the-p22-mask-6010ee` |
| HEAD / base commit | `8c17ed86d04d78ab66e938db6a96fa4866e05bd2` (“gnhf 11: Finished R9–R10 closeout…”) |
| Launch base | sibling tip `codex/p22-masked-atac-base-20261001` at the same `8c17ed8` (GNHF refuses `--worktree` from a `gnhf/` branch) |
| Worktree git status at M0 start | clean at `8c17ed8` (no local modifications before owned copy) |
| GNHF version | `0.1.49` (`/opt/homebrew/bin/gnhf`) |
| Run ID | `execute-the-p22-mask-6010ee` |
| Agent / model | cursor / auto |
| Free disk | **16.20 GiB** free (`shutil.disk_usage` on P22); meets later ≥4 GiB artifact floor; **not** authorizing fits here |
| RAM | hardware 128 GiB; rough free+inactive ≈ 80 GiB at record time |
| Interpreter | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` (3.11.x via venv) |
| `PYTHONPATH` | this worktree `src` |
| `p22.__file__` | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/masked-atac-20261001/src/p22/__init__.py` (worktree-owned) |

## Dirty main fingerprint (preserved; not merged)

Main checkout `/Users/anuragdani/Github/niw-eb1a/P22` at HEAD `9a1e77728c8b9f5d7065a6dd1be981991315a6b4` on branch `gnhf/p22-nn-cellstate` remains dirty. **Only** this stage’s `PLAN.md` and `GNHF_PROMPT.md` were copied into this worktree. Unrelated dirty/untracked main paths were **not** copied or staged.

Dirty-main source SHA-256 for owned files (pre-copy absolute paths under main):

| Source file (main, uncommitted) | SHA-256 |
|---|---|
| `…/masked_atac_pilot_20261001/PLAN.md` | `a9bf38e474e868bd0b32403cce5998ee825bde78e6947e9b28bf19bfbbe0e834` |
| `…/masked_atac_pilot_20261001/GNHF_PROMPT.md` | `7b022478a6d9a8a16b3bf70842492ee8df31e0512339f515ca64125f7a4dfafd` |

Dirty-main root `tasks/plan.md` after its M-block prepend matches this worktree post-append byte-for-byte (`2374a8e9787862859db80bdf03f0495b827b755c5cd4b70186fb5059487faf3d`). Dirty-main `tasks/todo.md` still has unchecked R0–R10 boxes; this worktree retains completed R0–R10 dispositions from `8c17ed8`. Only the M0–M10 block was extracted and prepended.

## Copied versus fresh evidence

**Copied (immutable imports of this stage’s plan/prompt; not recomputed):**

| Worktree path | SHA-256 (matches main source) | Role |
|---|---|---|
| `tasks/nn/…/masked_atac_pilot_20261001/PLAN.md` | `a9bf38e474e868bd0b32403cce5998ee825bde78e6947e9b28bf19bfbbe0e834` | Authoritative M0–M10 plan |
| `…/GNHF_PROMPT.md` | `7b022478a6d9a8a16b3bf70842492ee8df31e0512339f515ca64125f7a4dfafd` | Launch prompt |

**Fresh in this worktree (M0):**

| Artifact | Role |
|---|---|
| This `PREFLIGHT.md` | Provenance / runtime / writer / raw-root record |
| Prepended M0–M10 section in worktree `tasks/todo.md` | Canonical checklist (older R0–R10 DONE and prior sections preserved; M0 marked DONE) |
| Prepended 2026-10-01 masked-ATAC section in worktree `tasks/plan.md` | Root plan pointer (older sections preserved; matches dirty-main plan byte-for-byte) |
| `reports/generated/nn_masked_atac_pilot_20261001/attempt_counter.json` | New owned raw root + zeroed counters (gitignored under `/reports/generated/`) |

Pre-append worktree SHA-256: `tasks/todo.md` `0a6db41aafc182e54d81938d3f4b50ed1b3ef06e0662b67e2b390dd73bd60494`; `tasks/plan.md` `23b8d7f2948c6a930e52c1c918d9050ec0ffe5cce4a662bae223eec9109dc4a7`.

Post-M0 plan SHA-256: `tasks/plan.md` `2374a8e9787862859db80bdf03f0495b827b755c5cd4b70186fb5059487faf3d` (matches dirty-main).  
Post-M0 checklist SHA-256: `tasks/todo.md` `62ac69000b678f473c63a49e455844ea397f25581f1770f63da033ecf07f4cdd` (M0 marked DONE; R0–R10 DONE retained). Recompute this `PREFLIGHT.md` SHA-256 after any further edit.

## New output root and overwrite refusal

| Item | Value |
|---|---|
| New raw root | `reports/generated/nn_masked_atac_pilot_20261001/` (this worktree; gitignored) |
| Cumulative counters | `attempt_counter.json` zeros: total attempts 0/40; smoke fits 0/5; fitting hours 0/6; artifacts 0/4 GiB; network 0; workers 1 × torch threads 2 |
| Overwrite policy | Refuse writes through shared old-result roots (S10 / S9 / S7-v2 / ladder_v3) and refuse second scoring of existing sidecars; new artifacts must live under the new raw root |
| Shared old raw | Read-only via absolute prior worktree paths below — **never write through** |

## Shared raw / input paths (read-only)

| Path | Availability |
|---|---|
| H5AD `/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` | EXISTS (1,569,658,860 B); prior recorded SHA-256 `08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb` (not rehashed in M0) |
| Exact ATAC counts `…/p22-results-executio-debda8/…/atac_tiebreak_measured_20260921/counts/counts.npz` | EXISTS; matrix SHA-256 `5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969` (465 regions; from Q3 `regulatory_coverage.json`) |
| Union BED `…/execute-the-p22-data-146414/configs/atac_tiebreak_union_2026-09-21.bed` | EXISTS; bed SHA-256 `d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23` |
| Region sets `…/execute-the-p22-data-146414/configs/atac_tiebreak_region_sets_2026-09-21.json` | EXISTS; SHA-256 `13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407` |
| Ordered cells SHA-256 | `7a56c2a906f66b528dd673f944c067a006d4f09127eda70ced4155c281a09e53` (248,998 cells / 30 donors) |
| Prior S10 raw `…/execute-p22-s-failur-d8f02c/reports/generated/nn_failure_audit_20261001/s10_corrected_null_pairing_20261001/` | EXISTS (read-only; never write through) |
| Prior S9 raw `…/execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930/` | EXISTS (read-only) |
| S7-v2 durable `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/` | EXISTS (immutable) |
| ladder_v3 `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/` | EXISTS (not reopened in M0) |

Count unit pinned by Q3: `unique_fragment_overlap`. Fresh metadata-only BED inspection cited in PLAN: **58 overlapping interval pairs** in the 465-region union — target-ID removal alone is insufficient (M1 must quantify under whole-chromosome mask).

## Prior artifact hashes (immutable labels)

| Record | SHA-256 | Label retained |
|---|---|---|
| R10 `HANDOFF.md` | `c15d5c4ca04a0b3418bb297b5614f589c5c635bc14aa77dc9da9c643f3bc36ac` | S10 INVALID; stop; primary `B_NULL` |
| R10 `VERIFICATION.json` | `d4dcda8c0e4dbd3631b7494af1f59ecce120562d6541f3e4e823fde13ddf1564` | verified closeout |
| R4 `GUIDANCE_AND_CLAIMS.md` | `c452b45c8533a15d8631856cf26323adfc620a09a221a157a1b649bb1586af6f` | claim L2 computational permitted; Q2 blocks L4 only |
| R5 `TASK_DATA_OPTIONS.md` | `5802efde787aba17b487d27cd970c131f3042f0ff369e60992854a5bafd49d96` | claim-2 masked ATAC candidate recorded |
| Q3 `regulatory_coverage.json` | `7633c1f0c5a7d548f20e56c6ca5884a9a5645145d042ba5b11940c1dd5f4b724` | 465-region exact union contracts |
| Vault July 2 MOM transcript | `38871f240c5a0f7f95ea9e279fa5b73a4306152e24a6b1b5515a509011529a91` | professor record (read-only) |
| Vault July 21 MOM transcript | `0bce4ea91e7daefac37645bfc6dc35b4742473ea3b5152737ded8bf9eff3ace2` | professor record (read-only) |

Worktree `MOM/2026-07-02/` and `MOM/2026-07-21/` hold README pointers only; original transcripts live in the vault paths above and are **not** rewritten.

## Runtime imports (no installs)

| Package | Version |
|---|---|
| numpy | 1.26.4 |
| scipy | 1.17.1 |
| pandas | 2.2.2 |
| h5py | 3.16.0 |
| torch | 2.8.0 |

Import check exit code 0 with `PYTHONPATH=<worktree>/src`.

## Preserved scientific labels (not reopened in M0)

| Label | Status |
|---|---|
| Primary study gate | **`B_NULL`** |
| S7-v1 / S7-v2 | **`INVALID`** |
| Prior S8 | **`NO FIT`** |
| S9 analytic pairing | **`INVALID`** (immutable) |
| S10 corrected-null pairing | **`INVALID`** (immutable) |
| Q2 independent cell-state endpoint | **`ENDPOINT_UNRESOLVED`** (blocks claim level 4 only; does **not** block this claim-level-2 measured-target pilot) |
| Power | `POWER_UNESTABLISHED` |
| Study | `STUDY_PARTIAL` |

This pilot is **claim level 2: computational prediction**. It does not relabel Q2/S10 or claim biological state, causal mechanism, or external validation.

## Writers and concurrency

- Single writer for status/checklist and the new raw root.
- No concurrent writers; M1 may proceed only after this M0 PASS record.
- No push/merge; orchestrator commits owned files.

## M0 acceptance checklist

- [x] Copy only this stage’s PLAN.md / GNHF_PROMPT.md; source and worktree SHA-256 match.
- [x] Append M0–M10 block to root `tasks/todo.md` / `tasks/plan.md` without overwriting older R/Q/M/E sections.
- [x] Record base/head, `p22.__file__`, interpreter, source/input hashes, shared raw paths, runtime headroom and writers.
- [x] Define unique output root and durable zeroed counters; old primary/S7/S9/S10 and vault/MOM/sent packet remain read-only.

**Next:** M1 — verify measured inputs and whole-target-chromosome masking contract (no fits).
