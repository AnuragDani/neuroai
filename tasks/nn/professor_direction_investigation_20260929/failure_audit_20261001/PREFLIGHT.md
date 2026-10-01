# R0 Preflight — failure audit 2026-10-01

**Disposition:** R0 PASS (no fits, no downloads, no package installs, no scientific gate edits, no vault/MOM/sent-packet edits).  
**Recorded:** 2026-10-01 01:09–01:11 PDT (local worktree clock).  
**Scope:** provenance, owned-file copy, root plan/checklist append, runtime/input/raw availability, new output root. R1+ deferred.

## Identity

| Item | Value |
|---|---|
| Worktree path | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180-gnhf-worktrees/execute-the-p22-data-146414-gnhf-worktrees/execute-p22-s-failur-d8f02c` |
| Branch | `gnhf/execute-p22-s-failur-d8f02c` |
| HEAD / base commit | `67245a2b19de9d6fb094fc01190590d9362d6d43` (“gnhf 13: Completed Q12 verified closeout…”) |
| Launch base | sibling tip `codex/p22-failure-audit-base-20261001` at the same `67245a2` (GNHF refuses `--worktree` from a `gnhf/` branch) |
| Worktree git status at R0 start | clean at `67245a2` (no local modifications before owned copy) |
| GNHF version | `0.1.49` (`/opt/homebrew/bin/gnhf`) |
| Run ID | `execute-p22-s-failur-d8f02c` |
| GNHF PID | `49939` |
| Agent / model | cursor / auto |
| Launch flags | `--worktree --max-iterations 50 --max-tokens 16000000 --max-rate-limit-wait 2h --prevent-sleep on --meteor-frequency 0` |
| Free disk | **15.08 GiB** free (`shutil.disk_usage` on P22); meets later ≥4 GiB artifact floor; **not** authorizing fits here |
| RAM | hardware 128 GiB; rough free+inactive ≈ 25.59 GiB at record time |
| Interpreter | `/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python` (3.11.x via venv) |
| `PYTHONPATH` | this worktree `src` |
| `p22.__file__` | `…/execute-p22-s-failur-d8f02c/src/p22/__init__.py` (worktree-owned) |

## Dirty main fingerprint (preserved; not merged)

Main checkout `/Users/anuragdani/Github/niw-eb1a/P22` at HEAD `9a1e77728c8b9f5d7065a6dd1be981991315a6b4` on branch `gnhf/p22-nn-cellstate` remains dirty. **Only** the owned `failure_audit_20261001` plan/prompt/null diagnostic were copied into this worktree. Unrelated dirty/untracked main paths were **not** copied or staged:

- Modified: `docs/INDEX.md`, `status.md`, `tasks/nn/plan.md`, `tasks/nn/todo.md`, `tasks/plan.md`, `tasks/todo.md`
- Untracked: `paper/.gitignore`, `paper/short_paper.md`, `tasks/nn/finish_20260928/`, remainder of `tasks/nn/professor_direction_investigation_20260929/` beyond the three owned files for this stage

Dirty-main source SHA-256 for owned files (pre-copy absolute paths under main):

| Source file (main, uncommitted) | SHA-256 |
|---|---|
| `…/failure_audit_20261001/PLAN.md` | `bbf51df12552324c68d0bf8be2b6ca71a2496844a1b78c3e18c823b43bfaff65` |
| `…/failure_audit_20261001/GNHF_PROMPT.md` | `75baacb2098bc7a5e74eb7ef6e0444313beeccd07fad5a41db38b534261330dc` |
| `…/failure_audit_20261001/NULL_INVARIANCE_DIAGNOSTIC.json` | `d6207ea0b5a0372bec5a90e6091cdccfdc4ce73eafe5ed05b61299c903abbedf` |

Dirty-main full-file SHA-256 for root checklist/plan (append sources; **not** wholesale replacements):  
`tasks/todo.md` `eb7b2db986676f8119923aa52a2502a21762dfc9ffe47b791e5adb776622ca2e`;  
`tasks/plan.md` `23b8d7f2948c6a930e52c1c918d9050ec0ffe5cce4a662bae223eec9109dc4a7`.

Note: dirty-main `tasks/todo.md` still has unchecked Q0–Q12 boxes; this worktree retains the completed Q0–Q12 dispositions from `67245a2`. Only the R0–R10 block was extracted and prepended.

## Copied versus fresh evidence

**Copied (immutable imports of prior diagnostic slices; not recomputed in R0):**

| Worktree path | SHA-256 (matches main source) | Role |
|---|---|---|
| `tasks/nn/…/failure_audit_20261001/PLAN.md` | `bbf51df12552324c68d0bf8be2b6ca71a2496844a1b78c3e18c823b43bfaff65` | Authoritative R0–R10 plan |
| `…/GNHF_PROMPT.md` | `75baacb2098bc7a5e74eb7ef6e0444313beeccd07fad5a41db38b534261330dc` | Launch prompt |
| `…/NULL_INVARIANCE_DIAGNOSTIC.json` | `d6207ea0b5a0372bec5a90e6091cdccfdc4ce73eafe5ed05b61299c903abbedf` | No-fit rho=0 orthogonality / shuffle diagnostic |

**Fresh in this worktree (R0):**

| Artifact | Role |
|---|---|
| This `PREFLIGHT.md` | Provenance / runtime / writer / raw-root record |
| Appended R0–R10 section in worktree `tasks/todo.md` | Canonical checklist (older Q0–Q12 and prior sections preserved; R0 marked DONE) |
| Appended 2026-10-01 section in worktree `tasks/plan.md` | Root plan pointer (older sections preserved) |
| `reports/generated/nn_failure_audit_20261001/attempt_counter.json` | New owned raw root + cumulative counters (gitignored under `/reports/generated/`) |

Pre-append worktree SHA-256: `tasks/todo.md` `5ef2cbcdc99b487fa11084d504c56b32a490fa2ae8d608b4e1c7136094e4318c`; `tasks/plan.md` `a40df56874cdb57dce16d628299c90c9973521d66c1da2fcb4b29ba0793553b4`.

Post-R0 worktree SHA-256: `tasks/todo.md` `3d0d26d8ca851b6bda3f404eabce0f6ae385c0b982cce83a64b9975405a8d03d` (R0 marked DONE with evidence; Q0–Q12 DONE dispositions retained); `tasks/plan.md` `23b8d7f2948c6a930e52c1c918d9050ec0ffe5cce4a662bae223eec9109dc4a7` (matches dirty-main appended plan byte-for-byte). Recompute this `PREFLIGHT.md` SHA-256 after any further edit.

## New output root and overwrite refusal

| Item | Value |
|---|---|
| New raw root | `reports/generated/nn_failure_audit_20261001/` (this worktree; gitignored) |
| Cumulative counters | `attempt_counter.json` zeros: scientific fits 0/90; diagnostic fits 0/12; generator-only draws 0/256; fitting hours 0/6; artifacts 0/4 GiB; network 0 |
| Overwrite policy | Refuse writes through shared old-result roots (S9 / S7-v2 / ladder_v3) and refuse second scoring of existing sidecars; new artifacts must live under the new raw root |
| Shared old raw | Read-only via absolute prior worktree paths below — **never write through** |

## Shared raw / input paths (read-only)

| Path | Availability |
|---|---|
| Prior S9 raw `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/…/execute-the-p22-data-146414/reports/generated/nn_s9_analytic_pairing_20260930/` | EXISTS (49 fits; checkpoints; donor_predictions; ledger; provenance) |
| S9 provenance.json | EXISTS; sha256 `69b018194e35ac8172dec91e37b11109925fbcec6e7d074d9a556ca93499d621` |
| Prior Q12 HANDOFF / VERIFICATION / execute.json / NO_FIT_REVIEW / SYNTHETIC_PROTOCOL.json (this worktree tracked) | EXISTS (hashes below) |
| H5AD `/Users/anuragdani/Github/niw-eb1a/P22/data/real/f16c25da-15bd-46a4-9a3f-17093f27a2f1.h5ad` | EXISTS |
| S7-v2 durable `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/` | EXISTS (immutable; never write through) |
| ladder_v3 `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/` | EXISTS (not reopened in R0) |
| Verifier JSON `docs/nn_v2/ladder_verification.json` | EXISTS; sha256 `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |

## Prior artifact hashes (immutable labels)

| Record | SHA-256 | Label retained |
|---|---|---|
| Q12 `HANDOFF.md` | `49bd1d2f781c1358abe993cb0d7a9292aefc814b7feda1f39e55c758e03fd996` | S9 INVALID; Q11 BLOCKED; stop |
| Q12 `VERIFICATION.json` | `4a7f31ffe12252b4d5fea95702b0c1137dc8d7446dcced12a60f986582a18f71` | focused 60 PASS |
| Q10 `execute.json` | `8e98bb6b6bf7a6861371db065bff09ea9e786676ae33502c130a650584be9985` | 49/49 INVALID |
| Q9 `NO_FIT_REVIEW.json` | `1f34a4b7c0ad352e4815aa00ce5556b6969a23919ff3fc657fea198fc36a2b2d` | independent PASS |
| Q7 `SYNTHETIC_PROTOCOL.json` | `eedf5e77c4ba08d8a801609e5a2bdfccc5d882e2d297d9469c4af364ad25ec7a` | PROTOCOL_FROZEN |
| Vault July 2 MOM transcript | `38871f240c5a0f7f95ea9e279fa5b73a4306152e24a6b1b5515a509011529a91` | professor record (read-only) |
| Vault July 21 MOM transcript | `0bce4ea91e7daefac37645bfc6dc35b4742473ea3b5152737ded8bf9eff3ace2` | professor record (read-only) |
| Vault `external_shared/STATUS.md` | `78a82a9a2fd53bd97ed25228642130bb9131e1d8a6919321e216684f38774e0e` | sent-packet status (not edited) |

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

## Preserved scientific labels (not reopened in R0)

| Record | Label |
|---|---|
| Primary | `B_NULL` |
| Study | `STUDY_PARTIAL` |
| Biological power | `POWER_UNESTABLISHED` |
| S7-v1 / S7-v2 | `INVALID` |
| Prior S8 / continuation | `NO FIT` |
| Prior S9 analytic pairing-use | `INVALID` (immutable) |
| Q2 endpoint | `ENDPOINT_UNRESOLVED` (blocks biological pilot; does not halt this audit) |

Initial no-fit diagnostic (copied): original max abs donor/channel product mean ≈ `1.73e-16`; shuffled mean abs ≈ `0.1465`. Concerns exchangeability; **does not** by itself establish the neural outcome's cause.

## Conflicting writers

| Process | Relevance |
|---|---|
| This GNHF PID `49939` | Owner of this worktree only |
| GNHF PID `37697` / `91107` | P27 objectives in other repos; **not** writers on P22 S9 / S7-v2 / this failure_audit folder |
| Prior Q12 worktree `…/execute-the-p22-data-146414` | Holds immutable S9 raw; read-only for this stage |

**R0 writer conclusion:** no conflicting writer on shared scientific raw roots for this audit. Parallel GNHF elsewhere is out of scope. `lsof` on S9 root empty/unavailable at record time.

## R0 acceptance checklist

| Requirement | Status |
|---|---|
| Start from `67245a2`; worktree/branch/GNHF identity recorded | PASS |
| Dirty main preserved; unrelated dirty files not copied/staged | PASS |
| Only dated plan, prompt, null diagnostic copied; source SHA-256 match | PASS |
| R checklist + root plan entry appended; older Q0–Q12 sections retained | PASS |
| Copied vs fresh evidence distinguished | PASS |
| Interpreter imports + `p22.__file__` from worktree `src` | PASS |
| Shared input/raw paths available or named blockers | PASS (all checked paths exist) |
| New output root + counters + overwrite refusal defined | PASS |
| Original primary/S7/S9/professor/sent-packet hashes recorded | PASS |
| Disk/RAM/writers recorded; no fits/downloads/installs | PASS |

**R0 result: PASS.** Next ordered unit: **R1** — replay immutable S9 evidence and trace actual execution/review coverage (`S9_AUDIT.md`; read-only sidecars; no fits).
