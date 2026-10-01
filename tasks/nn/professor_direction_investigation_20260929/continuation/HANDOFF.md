# C6 — Continuation handoff → **NO FIT** (complete)

**Date:** 2026-09-30.  
**Scientific label:** **`NO FIT`** (I2 control-design FAIL; S8 not frozen; C3–C5 unauthorized).  
**Chosen path:** bounded internal null / detectability-limit paper (framing F4).  
**Not claimed:** `INVALID` / `INCOMPLETE` / `PAIRING_NEGATIVE` / `PAIRING_POSITIVE` for any new synthetic batch (none was authorized or run).

## Identity

| Item | Value |
|---|---|
| Worktree | `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202-gnhf-worktrees/read-users-anuragdan-b61180` |
| Branch | `gnhf/read-users-anuragdan-b61180` |
| Integration base | `808fa734a8dc2d89d34853204251bd9decea2a06` |
| Tip at C6 write | `a554687bc9d1fad8b4e02495166d64204ea34eb6` (C0–C2 commits; C6 adds this handoff + status/index) |
| GNHF | `0.1.49`; run `read-users-anuragdan-b61180` |
| Ordered task | `CONTINUATION_20260930.md` sha256 `a6e8fb8a…` |

Professor sources: July 2 / July 21 vault MOM. Lane A recovery, Lane B `4d0c3b9`, Lane C `010a07f` are worker evidence. No dated professor reply to the September 29 package was found.

## Tasks done (C0–C6)

| Step | Outcome | Evidence |
|---|---|---|
| **C0** Preflight | **PASS** | [PREFLIGHT.md](PREFLIGHT.md) sha256 `fb19bfa8…` |
| **C1** Lane A recovery | **PASS** (saved outputs only) | [LANE_A_RECOVERY.md](LANE_A_RECOVERY.md) sha256 `3a1bbe93…` |
| **C2** Lane B/C audit + path | **NO FIT**; path **(a)** | [DECISION.md](DECISION.md) sha256 `fb4c57f7…`; [lane_reports/](lane_reports/) |
| **C3** Freeze S8 protocol | **SKIPPED** (unauthorized after I2 FAIL) | — |
| **C4** Implementation / tests | **SKIPPED** | — |
| **C5** Synthetic fits / PC | **SKIPPED**; budget used **0** | No `nn_s8_*` root |
| **C6** Closeout | **THIS FILE** | status.md + docs/INDEX.md updated |

## Commands / recomputes (no fits)

```bash
# C1 — ladder gate from saved folds (no --write)
python3 gnhf/verify_ladder.py \
  --run /Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3 \
  --summary docs/nn_v2/ladder_summary.json
# → verdict PASS; CA−TC 0.026666…; CI [−0.0250, 0.076785…]; advantage=false

# C1 — S7-v2 pooled vs mean-fold BA from immutable donor_predictions/
# (local recompute documented in LANE_A_RECOVERY.md §3; no CLI rewrite of stage_state)

# C2 — Lane ownership (read-only; branches not merged)
git show --stat 4d0c3b943ac61022a86644fffee30915a0feab56
git show --stat 010a07f
```

**Tests / linters:** not required for this documentation-only closeout; no source or fit code changed in C0–C6.

## Gate outcomes

| Gate | Result |
|---|---|
| I0 provenance | **PASS** |
| I1 reproducibility (saved-record recompute) | **PASS** |
| **I2 control design** | **FAIL** → overall **NO FIT** |
| I3 design adequacy (for chosen paper path) | **PASS** (`POWER_UNESTABLISHED` explicit) |
| I4 biology / mechanism claim path | **FAIL** for beyond-dosage claims; does not block null paper |
| I5 independent protocol review | **N/A** (no freeze attempted) |
| Ladder_v3 | Verifier **PASS**; primary **`B_NULL`** |
| S7-v1 / S7-v2 | Remain **`INVALID`** (immutable) |
| S8 | **Not frozen**; draft chance-null calibration **rejected** |

## Scientific interpretation (one page)

This continuation asked whether one new synthetic pairing-use control was scientifically justified after S7-v1/v2 `INVALID` and primary `B_NULL`. Lane A recovery confirmed the archived gates from saved records: ladder CA−TC ≈ 0.0267 with CI including 0; S7-v2 pooled ρ=0 null fails for `token_concat` (0.330357) and `gated_fusion` (0.325893); implementation mean-fold under-reports those failures; pairing PC remains `PC_FAIL`; confirmation correctly skipped. Lane C cohort/power claims match live JSON; external NeMO stays blocked. Lane B’s S8 draft correctly shifts the estimand to pairing use, but its proposed central-95% chance band from constant/Bernoulli predictors does **not** match the fitted seven-arm pooled-BA mechanism, would pass the same ρ=0 outcomes that previously failed the frozen band, and supplies no joint calibration. Under CONTINUATION rules that is an I2 **FAIL**. Therefore the justified path is **(a)** write the bounded internal null/detectability paper already framed as F4—not another covariance-class synthetic control, not a real-label remake on the same 30 donors, and not external acquisition in this run. A well-supported **NO FIT** is the finished scientific answer for this ordered task.

## Raw paths (immutable; not written by this run)

| Root | Role |
|---|---|
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/ladder_v3/` | Canonical real ladder |
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/` | S7-v1 durable |
| `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/` | S7-v2 durable |
| *(none)* | No `nn_s8_*` created |

## Budget

| Cap | Used |
|---|---|
| 150 attempted fits / 12 fitting hours / 2 GiB new artifacts | **0** / **0** / **0** |
| Package installs / push / merge / vault / packet / MOM edits | **None** |

## Accepted claims

- Primary advantage **not demonstrated** (`B_NULL`); study `STUDY_PARTIAL`; power `POWER_UNESTABLISHED`.
- S7-v1 and S7-v2 remain **`INVALID`**; do not relabel by switching mean-fold↔pooled after outcomes.
- Honest bounded internal null / detectability-limit paper (F4) is the writing path.
- Worker Lane B/C reports audited with source SHAs; branches not merged into this tip.

## Rejected / not authorized

- Freezing or fitting any S8 protocol under Lane B’s chance-null draft.
- Real-label CA advantage refit on the same 30 donors.
- External NeMO acquisition or preflight as this run’s next action.
- Searching for a positive synthetic result after NO FIT.
- Promoting hypothetical pairing outcomes to biology or `A_ADVANTAGE`.

## Remaining blockers (outside this GNHF stop)

1. Future pairing-use protocol (new ID) would need a fitted-mechanism null + seven-arm joint rule **without** outcome-guided threshold shopping, then independent I5 review before any fit.
2. NeMO T13 blockers unchanged (QC, specimen independence, feature contract).
3. Local branch only — not pushed or merged; status does not claim remote publication of this closeout.

## Stop

**COMPLETE — C0–C6 truthful handoff with scientific `NO FIT`.** C3–C5 correctly skipped. GNHF stop condition met. Do not continue searching for a positive result.
