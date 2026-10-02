# Cursor Auto continuation — 2026-09-30

## Objective

Finish the professor-direction investigation, decide whether one new synthetic pairing-use control is scientifically justified, and execute it only if the prospective protocol passes every no-fit gate below. A well-supported **NO FIT** decision is a successful finish. Do not optimize until cross-attention wins. The result must remain useful if every new control is negative or invalid.

This continuation is separate from the finished NN-v2 primary and S7-v1/v2. The September 29 professor package was researcher-confirmed sent. No professor reply is recorded. Original professor direction comes from the July 2 and July 21 MOM, not worker handoffs.

## Live status at handoff

| Item | Checked state | Source |
|---|---|---|
| GNHF | All three `p22-investigation-*` tmux sessions ended on September 30. | `tmux list-sessions`: no server; lane logs and branch tips checked. |
| Lane A | Stopped in iteration 1 after a graceful-stop request. Zero commits; no report. Cause of stop not established. | `LANE_A.log`, 12 KB. |
| Lane B | Complete, one local commit `4d0c3b9`. It proposed S8 pairing-use control, **DRAFT / NO FITS**. | `gnhf/read-users-anuragdan-caf4c8` and `outputs/LANE_B.md`, `DRAFT_PROTOCOL_S8.md`. |
| Lane C | Complete, one local commit `010a07f`. It recommends bounded internal paper; external NeMO validation blocked by QC, specimen identity, and feature contract. Power remains `POWER_UNESTABLISHED`. | `gnhf/read-users-anuragdan-ea5475` and `outputs/LANE_C.md`, `COHORT_TABLE.md`. |
| NN-v2 primary | `ladder_v3` verifier PASS; CA−TC donor BA estimate 0.0267, CI [−0.0250, 0.0768]; `B_NULL`. | `docs/nn_v2/ladder_verification.json`. |
| S7-v2 | `INVALID`: planned pooled null failed for token-concat and gated fusion; implementation used mean-fold null statistic; PC_FAIL; no confirmation. 119 unique successful fits. | S7-v2 independent review at base commit `808fa734` and raw sidecars. |
| Main checkout | Dirty with unrelated changes; preserve all. `status.md` still contains older S7 planning language, so use versioned S7-v2 evidence for scientific claims. | `git status --short`; vault status and S7-v2 review. |

The source checkout for this GNHF launch is `/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202` at `808fa734a8dc2d89d34853204251bd9decea2a06`. It has a pre-existing unstaged `paper/draft.md` change. `--worktree` starts a new branch from committed HEAD; do not copy, discard, stage, or modify that paper change.

## Source ownership

- Read `AGENTS.md`, `status.md`, `docs/INDEX.md`, [investigation PLAN](PLAN.md), original July MOM, and live versioned verifier/review before work. Meeting notes are professor sources; B/C are worker reports.
- Read Lane B from branch `gnhf/read-users-anuragdan-caf4c8` at `4d0c3b9` and Lane C from `gnhf/read-users-anuragdan-ea5475` at `010a07f`. Check their diffs and cited evidence. Do not merge branches blindly. Copy only accepted report files into this new integration worktree with source SHA noted.
- Read raw S7-v2 sidecars from `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_split_v2_20260929/`. Treat them as immutable. Never write through a symlink into an old result root.
- Keep this continuation's outputs under `tasks/nn/professor_direction_investigation_20260929/continuation/` in the new GNHF worktree, and any accepted new synthetic raw data under a **new** `reports/generated/nn_s8_*` root. Do not edit the sent professor packet, original MOM, finished NN-v2 primary JSON, S7-v1/v2 spec, result or ledger.

## Ordered work and acceptance

### C0 — Preflight and provenance (no fits)

Record exact source commit, worktree path, branch, GNHF command/version, input hashes, free disk, existing local changes and raw evidence paths. Recheck S7-v2 result against independent review. Verify Lane B/C commit ownership with `git show --stat` and read their full reports. Verify no other GNHF session still runs or writes shared raw roots. If an input is missing, preserve a blocker and stop dependent work.

**Pass:** `continuation/PREFLIGHT.md` lists concrete paths/hashes, branch SHAs, clean new worktree scope, and no conflicting writer. No fits, downloads or scientific edits.

### C1 — Finish missing Lane A evidence audit (saved outputs only)

1. Inventory ladder_v3, S7-v1 and S7-v2 frozen protocols, executed source, hashes, fold/seed/model coverage, donor sidecars, checkpoint provenance and gate scripts.
2. Recompute the canonical real CA−TC point estimate/CI from saved records if raw files support it; otherwise state exactly which raw evidence is missing and retain verifier PASS as archived, not freshly reproduced.
3. Recompute S7-v2 pooled and mean-fold BA for all seven arms at rho 0 and 1, donor coverage, null/marginal gates, CA vs every comparator and pairing-PC saved summary. Verify confirmation was skipped. Keep `INVALID` even if implementation statistic is repaired later.
4. Trace CLI → generator/labels → donor split → train-only transforms → model fit → checkpoint reload → donor aggregation/bootstrap → gate → writer. Search every caller before proposing a shared-function fix. Separate confirmed protocol deviation, possible optimization failure, cohort/design limits, and GNHF orchestration errors.

**Pass:** `continuation/LANE_A_RECOVERY.md` has claim/source/recomputed value/gate table, ranked cause tree and exact file/line evidence. Mark claims `KNOWN`, `LIKELY`, or `UNKNOWN`. No code change or fit.

### C2 — Audit Lane B/C and decide research path (no fits)

Check Lane B taxonomy against the cited primary papers and actual code. Check Lane C donor/cohort numbers against saved JSON. Keep the null paper viable. Write a decision comparing: (a) publish bounded internal null/detectability paper now; (b) one prospective **pairing-use** synthetic control; (c) external paired-cohort preflight later. A new real-label CA advantage run on the same 30 donors is not justified by current evidence.

Critically assess Lane B's S8 draft before adopting it:

- S8 reuses the S7 covariance signal class after two invalid attempts. Explain what new question it answers and why this is not an outcome-guided search for a favourable threshold or seed. It cannot count as independent replication of S7.
- The proposed central 95% chance band from constant/Bernoulli predictions is **not automatically** a valid null for seven fitted, correlated models. Specify a null calibration that matches the tested statistic and fitted-model mechanism, or reject S8. Account for seven-arm joint gate and fixed 30-donor split without inspecting new outcomes to adjust thresholds.
- An invalid null gate cannot be converted to a method claim. A passing pair shuffle must show sensitivity to *within-cell pairing* while preserving donor-level marginals and label integrity. Explain why a positive or negative shuffle difference is interpretable on this generator.
- Fix one primary statistic, donor unit, bootstrap resampling scheme, exactly one decision rho, fixed fake-label generator seed, fair supervision/tuning budget and test-fold class support. Reject any design that quietly changes these after seeing new results.
- Reconcile task goal: S8 asks whether CA uses pairing, **not** whether CA beats all simpler models. Never promote `PAIRING_POSITIVE` to `A_ADVANTAGE` or a biological mechanism claim.

**Pass:** `continuation/DECISION.md` records I0–I5 from PLAN.md as PASS, FAIL or UNRESOLVED with evidence, chosen path, rejected paths and limits. If any critical gate fails, choose **NO FIT**, finish bounded-paper recommendation and stop. Do not mark review PASS by assertion alone.

### C3 — Freeze a new protocol only if C2 passes (no fits)

If and only if C2 accepts one scientifically distinct pairing-use test, write `continuation/S8_PROTOCOL.md` and a machine-readable spec with a **new protocol ID**, output root, input/source hashes, generator equation, fake-label IDs, donor split manifest, features, all seven arms, parameter counts, fixed training settings, primary estimand/statistic, null/marginal/PC gate order, result precedence and complete budget. Do not copy Lane B's draft without resolving its chance-calibration concern. Declare whether null band uses calibrated distribution or another justified fixed rule; never tune it to S7-v2 outcomes. Declare invalid/incomplete/negative/positive outcomes separately.

Resource ceiling: **150 attempted fits total**, at most two CPU workers with two torch threads each, at most 12 hours of fitting, at most 2 GiB new artifacts, and at least 11 GiB free disk before fits. No hyperparameter, seed, rho or comparator search. The 119-fit plan is an estimate, not permission to exceed the cap. No real disease labels may enter synthetic model fitting.

**Pass:** protocol/spec committed **before** any fit; independent no-fit checker recomputes splits, labels, hashes, parameter gap, budget and gate predicates; a recorded source review finds no leakage or old-path write. If no independent review is available within this run, record `NO_FIT_REVIEW_PENDING` and stop. This scientific gate is stricter than a task checkbox.

### C4 — Minimal implementation and verification, conditional (no fits until final gate)

Reuse S7-v2 code where scientifically identical. Add only the smallest versioned path/statistic/gate changes required by the new protocol. Ensure gate code uses **pooled donor BA** where the spec says pooled and logs mean-fold BA descriptively. Validate with one focused counterexample that pooled and mean-fold can differ. Test split class support, donor purity, output isolation, checkpoint identity, within-donor shuffle marginal preservation, missing-fit refusal, resource cap and result-label precedence. Run focused tests and one full suite after final source change. Save exact commands/counts. Do not install packages.

**Pass:** source/spec/input hash freeze, no-fit CLI completes on live inputs, zero new fit rows, tests PASS, provenance and budget checks PASS. Any source/spec change after first fit makes the new batch `INVALID`; do not silently resume with mixed provenance.

### C5 — One bounded synthetic run, conditional

Only after C0–C4 pass and protocol is committed: smoke ≤14 attempts; then one fixed screen ≤105 attempts; then predeclared pairing interventions on saved checkpoints with **zero new fits**. Recompute every gate from raw held-out donor sidecars. Stop at first invalid null, marginal, class-support, coverage, checkpoint or resource gate. If screen is valid but no pairing sensitivity, result is `PAIRING_NEGATIVE`. If screen and PC pass, `PAIRING_POSITIVE` supports only this implementation's use of the constructed pairing signal. Do **not** run advantage confirmation, new real-label fits, external acquisition or another S8 variant.

**Pass:** immutable attempted-fit ledger, complete per-donor sidecars, saved model/input/spec hashes, intervention seeds and CIs, independent saved-record recomputation, correct label and a one-page failure/success interpretation. A failed fit or invalid control is a result, not an invitation to select a new seed.

### C6 — Closeout

Write `continuation/HANDOFF.md`: exact branch/commit, tasks done, commands, tests, gate outcomes, scientific label, raw paths, budget used, accepted/rejected claims, and remaining blockers. Update repository `status.md` and `docs/INDEX.md` only after a material accepted gate or blocker, with direct links and no claim that local changes were pushed. Do not update vault paper, professor packet or MOM. Commit only owned files in the isolated branch. Never push or merge. Stop GNHF after truthful handoff, even if final answer is NO FIT, INVALID or PAIRING_NEGATIVE.

## Stop precedence

1. Missing data/provenance, cohort identity failure, conflicting writer, unreviewed protocol, or design flaw → **NO FIT** with evidence.
2. After fit starts: changed source/spec/input, leakage, invalid control or protocol deviation → `INVALID`; preserve artifacts, no replacement run.
3. Resource/coverage/checkpoint gap without design invalidity → `INCOMPLETE`; preserve exact missing jobs, no threshold change.
4. Complete valid control with insensitive pairing intervention → `PAIRING_NEGATIVE`.
5. Complete valid control with sensitive pairing intervention → `PAIRING_POSITIVE`, synthetic and implementation-specific only.

All paths in this runbook are local. The runner has authorization from this user request to perform **one bounded synthetic control** only after the prospective gates pass. This does not authorize real-label refits, external cohort acquisition, paid compute, package installation, pushing, publication or professor communication.
