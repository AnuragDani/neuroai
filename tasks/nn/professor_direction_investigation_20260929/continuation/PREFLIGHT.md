# C0 Preflight — professor-direction continuation 2026-09-30

**Disposition:** C0 PASS (no fits, no downloads, no scientific edits).  
**Recorded:** 2026-09-30 (local worktree clock).  
**Scope:** provenance only. Lane A recovery, decision, protocol, fits deferred to C1+.

## Identity

| Item | Value |
|---|---|
| Worktree path | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180` |
| Branch | `gnhf/read-users-anuragdan-b61180` |
| HEAD / base commit | `808fa734a8dc2d89d34853204251bd9decea2a06` (“Record independent S7-v2 pooled-gate review”) |
| `.gnhf/.../base-commit` | identical `808fa734…` |
| Worktree git status | clean (no local modifications) |
| GNHF version | `0.1.49` (`/opt/homebrew/bin/gnhf`) |
| Run ID | `read-users-anuragdan-b61180` |
| GNHF PID | `38020` |
| Agent / model | cursor / auto |
| Launch flags | `--worktree --max-iterations 45 --max-tokens 1600000 --max-rate-limit-wait 2h --prevent-sleep on --meteor-frequency 0` |
| Tmux session (this run) | `p22-investigation-continuation` (only P22 investigation tmux session present) |
| Free disk | **29.57 GiB** free (`df` / `shutil.disk_usage`); meets later ≥11 GiB fit preflight floor; **not** authorizing fits here |
| Node | `v22.21.1` |

Source launch checkout (parent, not this worktree):  
`/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202` at the same `808fa734`. That checkout has an **unrelated unstaged** `paper/draft.md` change. This continuation worktree did **not** copy, stage, or modify it.

## Ordered task inputs (hashes)

| Input | SHA256 |
|---|---|
| `CONTINUATION_20260930.md` (absolute under main tasks tree) | `a6e8fb8ac6aa760ed80e42fbaf7e56b970467cb1b720ba03e0e5c4d653edf666` |
| `PLAN.md` (investigation) | `1abc1422130d589e91a04440ad61a293949060722b36e2d1682594b002cd774d` |
| Vault July 2 MOM transcript | `38871f240c5a0f7f95ea9e279fa5b73a4306152e24a6b1b5515a509011529a91` |
| Vault July 21 MOM transcript | `0bce4ea91e7daefac37645bfc6dc35b4742473ea3b5152737ded8bf9eff3ace2` |

Professor sources vs workers: July 2/21 vault MOM = professor direction. Repo `MOM/2026-07-02/README.md` and `MOM/2026-07-21/README.md` are navigation only. Lane B/C reports and September packets are **worker** material, not new professor instructions. No dated professor reply to the September 29 package is recorded.

## Live scientific gates (rechecked, no recompute of raw ladder folds in C0)

| Gate | Live reading | Evidence |
|---|---|---|
| ladder_v3 verifier | `verdict=PASS`; primary CA−TC estimate `0.026666…`, CI `[−0.0250, 0.076785…]`, `advantage=false` → archived primary **`B_NULL`** | `docs/nn_v2/ladder_verification.json` sha256 `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| S7-v2 result doc | Scientific label **`INVALID`**; cites mean-fold token_concat BA `0.341667`; PC_FAIL; T9 skipped; 119 fits | `docs/nn_v2/s7_v2/S7_V2_RESULT.md` sha256 `24356a2899fcf6b63d68a8d54804224484cad2d2af16bd1a254c46397fdb0b4c` |
| S7-v2 independent review | Accept stop/`INVALID`; pooled rho-0 token_concat **0.330357**, gated_fusion **0.325893** both fail `[0.35,0.65]`; mean-fold vs pooled mismatch noted; confirmation correctly skipped | `docs/nn_v2/s7_v2/CODEX_REVIEW_20260929.md` sha256 `f25b3786788967b52135df73d06328932dc6bb7c4d0a5fdbbdc98c9f491d0aa3` |
| S7-v2 durable stage_state | `screen_label=INVALID`, `pc_label=PC_FAIL`, `confirm_label=CONFIRM_SKIPPED`, `confirmation_eligible=false` | `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/stage_state.json` sha256 `705e185bb216ea7bf12dd623bd7bda4efe1d83fb0c21ec5f65a7e7f51323f608` |
| S7-v2 fit ledger | **119** unique `ok` rows (14 smoke + 105 screen); 119 donor_prediction sidecars | ledger `fit_ledger.jsonl` sha256 `53920364c1e1afba48384598c9f998d9429e6ebb4107956e6b1631e3f6ba3be2`; `provenance.json` sha256 `52cde0ba8b3aabf107647ae7435ce5a00f728ed2bd8d0333d7e5da6ad9b6f6b4` |
| Power / study | `POWER_UNESTABLISHED`; study `STUDY_PARTIAL` (status snapshot; not upgraded here) | `status.md` |

**Conflict note (known, already reviewed):** `S7_V2_RESULT` / T7 cite mean-fold null BA; independent review and frozen v2 spec require **pooled** donor BA. Both paths fail the null band → `INVALID` stands. C0 does not repair history. Full arithmetic recomputation from all sidecars is C1.

Raw S7-v2 root (immutable for this run; never write through symlink into it):  
`/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/`  
Also present: `preflight.json` sha256 `9a86bedb7a7dec930cd88d1a73e8f90adecfc35444df0f640124ae08f2fa2b68`; `split_manifest_v2.json` sha256 `8ef4aa58bca3e7b7e68cc78664dd36b54c6c390c933400a3ee460bcb824818c4`.

No `nn_s8_*` output root exists yet (expected).

## Lane ownership verification

### Lane A — missing report (to recover in C1)

| Item | State |
|---|---|
| Log | `/Users/anuragdani/Github/niw-eb1a/P22/tasks/nn/professor_direction_investigation_20260929/LANE_A.log` (12 549 bytes) |
| Branch tip | `gnhf/read-users-anuragdan-27ac1d` → **same** `808fa734` (0 commits ahead) |
| Worktree | removed; only B/C/continuation worktrees remain under the parent gnhf-worktrees folder |
| Output report | **absent** (no `outputs/LANE_A.md`) |
| Stop evidence | Log ends with “graceful stop requested”; wrapped summary: 1 iteration, 0 good, 0 commits, tokens 0. Cause of external stop **not established** beyond graceful-stop UI. Mid-run text shows sidecar-schema inspection had started. |

### Lane B — commit `4d0c3b9` (do not merge blindly)

```
git show --stat 4d0c3b943ac61022a86644fffee30915a0feab56
```

- Author tip worktree: `…/read-users-anuragdan-caf4c8` @ `4d0c3b9`
- Files only: `outputs/LANE_B.md`, `outputs/DRAFT_PROTOCOL_S8.md` (+304 lines)
- Message: selected DRAFT pairing-use protocol S8; **DRAFT / NO FITS**
- Content hashes (blob via `git show`):  
  - `LANE_B.md` sha256 `337980e348f386ce28ca94f063de0f03288793f01b5cb22d46b9eb663c6dc726`  
  - `DRAFT_PROTOCOL_S8.md` sha256 `f8469885c951c6e473e47517868f7433b7fcc431227c2bde122bd0544bdd060a`
- **Not copied into this worktree in C0.** Integration copy only after C2 audit.
- Pre-noted scientific concern for later C2/C3: draft ρ=0 null uses “central 95% chance band” from constant/Bernoulli predictors — CONTINUATION requires calibrated null matching fitted seven-arm statistic or reject S8.

### Lane C — commit `010a07f` (do not merge blindly)

```
git show --stat 010a07f3b4798ab8cb81e5d71ac782e04c511413
```

- Author tip worktree: `…/read-users-anuragdan-ea5475` @ `010a07f`
- Files only: `outputs/LANE_C.md`, `outputs/COHORT_TABLE.md` (+203 lines)
- Recommends bounded internal paper; external NeMO validation blocked; power **`POWER_UNESTABLISHED`**
- Content hashes:  
  - `LANE_C.md` sha256 `a3d35d0e221478c0a0abccc1a865101db56b3d3fdc8c9ae3efb15d4fab6402ba`  
  - `COHORT_TABLE.md` sha256 `aec3c4f2f1f8fdf85f78e6f908299915fab8affe30a0eb816245ba9b5ad853e0`
- **Not copied into this worktree in C0.**

## Concurrent writers / shared-root safety

| Process | Relevance |
|---|---|
| This GNHF `38020` + tmux `p22-investigation-continuation` | Owner of this worktree only |
| Other GNHF PIDs (`13427` P* packet stop-when; `22975` P27 U01–U10) | Different repos/objectives; **not** writing `nn_s7_covariance_split_v2_20260929` or any `nn_s8_*` root |
| Prior `p22-investigation-*` lane tmux sessions | **Gone** (only continuation session listed) |
| Open writers on S7-v2 durable root | None observed (`lsof` empty / no matches) |
| Symlink write-through risk | Continuation outputs path = this worktree `tasks/nn/professor_direction_investigation_20260929/continuation/`; new synthetic data (if ever authorized) must use a **new** `reports/generated/nn_s8_*` root |

**C0 writer conclusion:** no conflicting writer on shared S7/S8 scientific raw roots. Parallel GNHF elsewhere is noted but out of scope.

## Worktree scope cleanliness

- Continuation owns only files under this branch/worktree.
- Investigation task directory did not exist on base commit; C0 creates `tasks/nn/professor_direction_investigation_20260929/continuation/` for integration artifacts.
- Forbidden in this run (reaffirmed): real-label fits, data acquisition, package install, push/merge, vault edit, sent-packet edit, professor message, edits to finished NN-v2 / S7-v1 / S7-v2 result JSON or ledgers.

## C0 acceptance checklist

| Requirement | Status |
|---|---|
| Exact source commit, worktree, branch, GNHF version/command | Recorded |
| Input hashes (continuation, plan, July MOM, live gates, Lane B/C blobs, S7-v2 raw) | Recorded |
| Free disk | 29.57 GiB |
| Existing local changes in this worktree | None |
| Raw evidence paths | S7-v2 durable root + 119 sidecars present |
| S7-v2 vs independent review | `INVALID` stands; pooled/mean-fold conflict documented |
| Lane B/C `git show --stat` + tip SHAs | Verified `4d0c3b9` / `010a07f` |
| No conflicting shared-root writer | Verified for S7-v2 / absent S8 |
| No fits / downloads / scientific edits | Held |

**C0 result: PASS.** Next ordered unit: **C1** — `continuation/LANE_A_RECOVERY.md` from saved outputs only.
