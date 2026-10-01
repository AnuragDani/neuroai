# Q0 Preflight — data-driven continuation 2026-09-30

**Disposition:** Q0 PASS (no fits, no downloads, no package installs, no scientific gate edits).  
**Recorded:** 2026-09-30 (local worktree clock).  
**Scope:** provenance, owned-file copy, root plan/checklist append, runtime/input availability. Q1+ deferred.

## Identity

| Item | Value |
|---|---|
| Worktree path | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414` |
| Branch | `gnhf/execute-the-p22-data-146414` |
| HEAD / base commit | `04282f0a803cc40c5d40aa0a9a7c535a213e1560` (“gnhf 5: Completed C6 truthful closeout… NO FIT”) |
| Launch checkout | sibling `…/read-users-anuragdan-b61180` on `codex/p22-data-driven-base-20260930` at the same `04282f0` (GNHF refuses `--worktree` from a `gnhf/` branch) |
| Worktree git status at Q0 start | clean at `04282f0` (no local modifications before owned copy) |
| GNHF version | `0.1.49` (`/opt/homebrew/bin/gnhf`) |
| Run ID | `execute-the-p22-data-146414` |
| GNHF PID | `67028` |
| Agent / model | cursor / auto |
| Launch flags | `--worktree --max-iterations 60 --max-tokens 4000000 --max-rate-limit-wait 2h --prevent-sleep on --meteor-frequency 0` |
| Tmux | no server on `/private/tmp/tmux-501/default` |
| Free disk | **19.58 GiB** free (`shutil.disk_usage` on P22); meets later ≥11 GiB fit floor; **not** authorizing fits here |
| RAM | hardware 128 GiB; rough free+inactive ≈ 25 GiB at record time |
| Interpreter | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` (3.11.16) |
| `PYTHONPATH` | this worktree `src` |
| `p22.__file__` | `…/execute-the-p22-data-146414/src/p22/__init__.py` (worktree-owned) |

## Dirty main fingerprint (preserved; not merged)

Main checkout `/Users/anuragdani/Github/niw-eb1a/P22` at HEAD `9a1e77728c8b9f5d7065a6dd1be981991315a6b4` on branch `gnhf/p22-nn-cellstate` remains dirty. **Only** the owned `next_stage_20260930` plan/prompt/three diagnostic JSONs were copied into this worktree. Unrelated dirty/untracked main paths were **not** copied or staged:

- Modified: `docs/INDEX.md`, `status.md`, `tasks/nn/plan.md`, `tasks/nn/todo.md`, `tasks/plan.md`, `tasks/todo.md`
- Untracked: `paper/.gitignore`, `paper/short_paper.md`, `tasks/nn/finish_20260928/`, remainder of `tasks/nn/professor_direction_investigation_20260929/` beyond the five owned files

Dirty-main source SHA-256 for owned files (pre-copy absolute paths under main):

| Source file (main, uncommitted) | SHA-256 |
|---|---|
| `…/next_stage_20260930/PLAN.md` | `46aac7bcd58245ea7cb13f815d69c5aacf4b2f49de258cd45a31ba1c915864b8` |
| `…/next_stage_20260930/GNHF_PROMPT.md` | `49f68f9edca36dba53caa2371bfe999c48d5e4b000a0b84614e7a4d427c2659f` |
| `…/next_stage_20260930/DATA_DIAGNOSTIC.json` | `74e0dc0d7b40eab927769ce505e1daba8520d584e9eed078e5d0f84f91d78782` |
| `…/next_stage_20260930/MEASUREMENT_AUDIT.json` | `f94deb5f81e1a2f6fca7175ab939ba4fb02035f363683e6bf0120c56d45d25d0` |
| `…/next_stage_20260930/TARGETED_SAMPLING_FEASIBILITY.json` | `5c0fbd58d6c33db43c005e1c34fb6f82990efbe4d0fbe4c8ab2a0599a662b8d9` |

Dirty-main full-file SHA-256 for root checklist/plan (append sources; not wholesale replacements):  
`tasks/todo.md` `7940b53c3d09dce0140ec5dbe686057e13e2dcfd21554af64c9a7884bc16b8e8`;  
`tasks/plan.md` `a40df56874cdb57dce16d628299c90c9973521d66c1da2fcb4b29ba0793553b4`.

## Copied versus fresh evidence

**Copied (immutable imports of prior diagnostic slices; not recomputed in Q0):**

| Worktree path | SHA-256 (matches main source) | Role |
|---|---|---|
| `tasks/nn/…/next_stage_20260930/PLAN.md` | `46aac7bcd58245ea7cb13f815d69c5aacf4b2f49de258cd45a31ba1c915864b8` | Authoritative Q0–Q12 plan |
| `…/GNHF_PROMPT.md` | `49f68f9edca36dba53caa2371bfe999c48d5e4b000a0b84614e7a4d427c2659f` | Launch prompt |
| `…/DATA_DIAGNOSTIC.json` | `74e0dc0d7b40eab927769ce505e1daba8520d584e9eed078e5d0f84f91d78782` | D0 cohort/sampling diagnostic |
| `…/MEASUREMENT_AUDIT.json` | `f94deb5f81e1a2f6fca7175ab939ba4fb02035f363683e6bf0120c56d45d25d0` | D1 measurement structural audit |
| `…/TARGETED_SAMPLING_FEASIBILITY.json` | `5c0fbd58d6c33db43c005e1c34fb6f82990efbe4d0fbe4c8ab2a0599a662b8d9` | D2 sampling feasibility IDs |

**Fresh in this worktree (Q0):**

| Artifact | Role |
|---|---|
| This `PREFLIGHT.md` | Provenance / runtime / writer record |
| Appended Q0–Q12 section in worktree `tasks/todo.md` | Canonical checklist (older sections preserved) |
| Appended 2026-09-30 section in worktree `tasks/plan.md` | Root plan pointer (older sections preserved) |

Pre-append worktree SHA-256: `tasks/todo.md` `524858628c8880bd72cc4246e9c902c7cb6c0152c052fef42d2b095aa752e160`; `tasks/plan.md` `95351c8eefeed7c0035aa4cf118776dd7ba1ab3807c712c4f42cd89d03fa8ab4`.

Post-Q0 worktree SHA-256: `tasks/todo.md` `3f9819e31d469e722389ba78888aa4006a84d88bc01a8bc918d0a0ec654455a5` (Q0 marked DONE with evidence); `tasks/plan.md` `a40df56874cdb57dce16d628299c90c9973521d66c1da2fcb4b29ba0793553b4` (matches dirty-main appended plan byte-for-byte). Recompute this `PREFLIGHT.md` SHA-256 after any further edit.

## Shared raw / input paths (read-only)

| Path | Availability |
|---|---|
| H5AD `/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` | EXISTS |
| Sampling record `/Users/anuragdani/Github/niw-eb1a/P22/docs/nn_v2/sampling_cap1000_seed22.json` (sha256 `e515b2eee03804b3836256ba3e8b7604fa6a8043e50c06c36b24988250423b2f`) | EXISTS; matches `DATA_DIAGNOSTIC.source_sha256` |
| Tracked union BED `/Users/anuragdani/Github/niw-eb1a/P22/configs/atac_tiebreak_union_2026-09-21.bed` | EXISTS |
| ATAC tie-break counts NPZ under `P22-gnhf-worktrees/p22-results-executio-debda8/…/atac_tiebreak_measured_20260921/counts/counts.npz` | EXISTS |
| ladder_v3 `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/` | EXISTS |
| S7-v2 durable `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/` | EXISTS (immutable; never write through) |
| Verifier JSON `docs/nn_v2/ladder_verification.json` (main tree / this worktree tracked copy) | EXISTS |

New raw outputs for this continuation must use a **new** unique root under this worktree (or a new `reports/generated/nn_*_20260930*` path owned here). Do not symlink-write into ladder_v3 or S7-v2 roots.

## Runtime imports (no installs)

| Package | Version |
|---|---|
| numpy | 1.26.4 |
| scipy | 1.17.1 |
| pandas | 2.2.2 |
| h5py | 3.16.0 |
| torch | 2.8.0 |

Import check exit code 0 with `PYTHONPATH=<worktree>/src`.

## Preserved scientific labels (not reopened in Q0)

| Record | Label |
|---|---|
| Primary | `B_NULL` |
| Study | `STUDY_PARTIAL` |
| Biological power | `POWER_UNESTABLISHED` |
| S7-v1 / S7-v2 | `INVALID` |
| Prior continuation C0–C6 | `NO FIT` (rejected particular S8 draft; not a ban on all future designs) |

Professor July 2/21 vault MOM remain professor records; this plan and prior continuation are worker interpretation.

## Conflicting writers

| Process | Relevance |
|---|---|
| This GNHF PID `67028` | Owner of this worktree only |
| GNHF PID `34169` / `91107` | P27 objectives in other repos; **not** writers on P22 ladder_v3 / S7-v2 / this next_stage folder |
| Other P22 worktrees (Lane B/C tips, finish branches, etc.) | Present; no observed writer on shared S7-v2 or ladder_v3 during Q0 (`lsof` empty on ladder_v3) |

**Q0 writer conclusion:** no conflicting writer on shared scientific raw roots for this continuation. Parallel GNHF elsewhere is out of scope.

## Q0 acceptance checklist

| Requirement | Status |
|---|---|
| Start from `04282f0`; worktree/branch/GNHF identity recorded | PASS |
| Dirty main preserved; unrelated dirty files not copied/staged | PASS |
| Only dated plan, prompt, three diagnostic JSONs copied; source SHA-256 match | PASS |
| Q checklist + root plan entry appended; older sections retained | PASS |
| Copied vs fresh evidence distinguished | PASS |
| Interpreter imports + `p22.__file__` from worktree `src` | PASS |
| Shared input/raw paths available or named blockers | PASS (all checked paths exist) |
| Disk/RAM/writers recorded; no fits/downloads/installs | PASS |

**Q0 result: PASS.** Next ordered unit: **Q1** — reproducible diagnostic replay + failure tests (`REPLAY.md`, new raw root, focused regressions).
