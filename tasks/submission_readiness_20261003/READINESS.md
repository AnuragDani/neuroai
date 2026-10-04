# Submission readiness handoff — 2026-10-03

**Status:** `READY_FOR_RESEARCHER_REVIEW`

This stage prepares a provisional venue package. It does **not** certify submission-ready manuscripts, invent author/funding/ethics facts, contact anyone, submit, publish, push or authorize research fits.

**Provisional venue:** BMC Research Notes — Research note ([VENUES.md](VENUES.md)). Researcher must confirm or replace (H1).

---

## Outputs (all required)

| Task | Artifact | Role |
|---|---|---|
| S1 | [VENUES.md](VENUES.md) | Five-venue comparison; provisional BMC Research Notes recommendation |
| S2 | [paper/submission_20261003/draft.md](../../paper/submission_20261003/draft.md) | Provisional venue-adapted Markdown copy |
| S3 | [AUDIT.md](AUDIT.md) | Automated vs manual source/figure audit |
| S3 | [INPUTS_NEEDED.md](INPUTS_NEEDED.md) | Researcher-owned facts H1–H12 (+ optional H13) |
| S4 | This file | Final checks, hashes, budget, stop disposition |
| Stage list | [todo.md](todo.md) | S1–S4 marks |

Accepted manuscripts remain the scientific authority: [paper/draft.md](../../paper/draft.md), [paper/short_paper.md](../../paper/short_paper.md), [paper/claims.csv](../../paper/claims.csv), [paper/refs_frozen.bib](../../paper/refs_frozen.bib). Prior stage closeout unchanged: [tasks/next_action_20261003/CLOSEOUT.md](../next_action_20261003/CLOSEOUT.md).

---

## S4 verification commands (repo root; no `--write`)

| # | Command | Exit | Verdict |
|---|---|---:|---|
| 1 | `.venv-p22/bin/python paper/check_paper.py --json` | 0 | `ok: true`, `failures: 0` (empty citations/numbers/forbidden/figures/word_counts/claim_sources) |
| 2 | `.venv-p22/bin/python paper/check_paper.py --draft paper/submission_20261003/draft.md --refs paper/refs_frozen.bib --claims paper/claims.csv --json` | 0 | `ok: true`, `failures: 0` (same empty report fields) |
| 3 | `.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3` | 0 | `verdict: PASS`; `advantage: false`; `problems: []`; primary estimate ≈0.026667, CI ≈[-0.0250, 0.076786], margin 0.07 |

Checkers and the ladder verifier were not modified. Source ledgers were not rewritten to obtain PASS.

---

## Definition of Done checklist

| Criterion | Evidence | Met? |
|---|---|---|
| Venue comparison + provisional recommendation from official sources or documented unknowns | [VENUES.md](VENUES.md) | Yes |
| Venue-specific copy with correct refs/image paths; accepted numbers unchanged | [draft.md](../../paper/submission_20261003/draft.md); checker #2 PASS; AUDIT N1–N14 PASS | Yes |
| Required automated checks PASS | Commands 1–3 above | Yes |
| Manual source/figure audit coverage and limits recorded | [AUDIT.md](AUDIT.md) §F; C3 PDF entailment and F4 re-plot unresolved by design/budget | Yes |
| No unsupported scientific/source claim left unlabeled in provisional draft | AUDIT: 0 failed numerical/path checks; unresolved items named | Yes |
| INPUTS_NEEDED names owners and completion conditions without invented facts | [INPUTS_NEEDED.md](INPUTS_NEEDED.md) H1–H12 owner=Researcher | Yes |
| READINESS links outputs, records hashes/checks/budget; submission pending inputs | This file | Yes |
| Task marks agree; no completed task repeated | [todo.md](todo.md) S1–S4 complete | Yes |

Missing funding/author/venue confirmation alone does **not** block this status (per stage contract).

---

## Source / figure audit coverage (from S3)

| Class | PASS | Unresolved | Failed |
|---|---:|---:|---:|
| Automated (A) | 4 | 0 | 0 |
| Numerical leaves (N) | 14 | 0 | 0 |
| Citations (C) | 3 | 1 (C3 primary-PDF entailment; budget) | 0 |
| Figures (F) | 3 | 1 (F4 generator re-plot; not authorized) | 0 |
| Venue local (V) | 4 | 1 (V5 Word/portal export; V2 publisher word-count method uncertain) | 0 |

Automated PASS ≠ citation entailment or full PNG scientific-content audit.

---

## Network budget (stage cumulative; not reset)

| Metric | Cap | Used | Notes |
|---|---:|---:|---|
| External requests | 24 | ≈25 (S1 overage; stop) | S2–S4: **0** new external requests |
| Documentation bytes | 32 MiB | ≈0.56 MiB | ≪ cap |

Citation PDF re-fetch remains blocked for this stage (optional researcher H13 under a new budget).

---

## Focused diffs (this stage vs pre-stage commit `e2c6e99`)

Tracked stage additions only (5 files, +449 lines at S1–S3 close; this handoff adds READINESS + list/status/index updates):

- `paper/submission_20261003/draft.md` (new provisional copy)
- `tasks/submission_readiness_20261003/VENUES.md`
- `tasks/submission_readiness_20261003/AUDIT.md`
- `tasks/submission_readiness_20261003/INPUTS_NEEDED.md`
- `tasks/submission_readiness_20261003/todo.md`

**Unchanged vs prior CLOSEOUT / PAPER_COMPLETION registers (live rematch):**

| Path | Live SHA-256 matches register? |
|---|---|
| `paper/draft.md` | Yes (`fa16ffad…812e`) |
| `paper/short_paper.md` | Yes (`7a69ecd9…0f12f`) |
| `paper/claims.csv` | Yes (`e768510a…f3d89`) |
| `tasks/next_action_20261003/EVIDENCE_BOUNDARY.md` | Yes (`703761e8…3dc5`) |
| `tasks/next_action_20261003/PAPER_COMPLETION.md` | Yes (`d09ae594…3f16`) |
| `tasks/next_action_20261003/EXTERNAL_DESK_DECISION.md` | Yes (`50ea32c0…c91e`) |
| `docs/nn_v2/ladder_verification.json` | Yes (`aec19fda…7256`) |
| `docs/nn_v2/ladder_summary.json` | Yes (`9add634e…c4c7`) |
| `MOM/README.md` | Yes (`18e8c8ad…a4c9`) |
| `MOM/2026-07-02/README.md` | Yes (`d411701b…2fa0`) |
| `MOM/2026-07-21/README.md` | Yes (`cf732e33…5e0e6`) |

`git diff` against accepted manuscripts / claims / prior-stage closeout paths for this stage: **empty** (no modifications). Past closeouts and their hash registers were not edited.

---

## Preserved scientific labels

Primary R3_ca − R3_tc **B_NULL**; M9 **NOT_AUTHORIZED**; M10 diagnostic-only; S7/S9/S10 **INVALID**; S8 **NO FIT**; E5 **NO_GO**; Q2 **ENDPOINT_UNRESOLVED**; power **POWER_UNESTABLISHED**. No equivalence, proven absence of signal, CA superiority, validated cell-state biology or new professor endorsement.

---

## Unresolved researcher inputs (owners)

All rows in [INPUTS_NEEDED.md](INPUTS_NEEDED.md): **owner = Researcher** (Anurag Dani unless reassigned).

| IDs | Topic | Blocks `READY_FOR_RESEARCHER_REVIEW`? |
|---|---|---|
| H1 | Venue confirmation | No (provisional package complete) |
| H2–H3 | Authors / affiliations / contributions | No |
| H4–H5 | Funding / competing interests | No |
| H6–H7 | Ethics / consent for publication | No |
| H8–H9 | Data/code release URLs | No |
| H10–H11 | APC budget / license | No |
| H12 | Word/portal export packaging | No |
| H13 | Optional citation PDF entailment refresh | No (optional) |

Submission / portal upload / outbound contact remain **unauthorized** until the researcher acts.

---

## Final artifact hashes (S4)

Paths relative to repository root. This file excludes its own hash to avoid self-reference.

| Artifact | SHA-256 |
|---|---|
| `paper/submission_20261003/draft.md` | `50779ebb58aa4957b926dc2e3c7c69ebdde83bed4cd32eac469cebcd6a1dbd4a` |
| `paper/draft.md` | `fa16ffad2feb37d5a22a30b492c587a4a8920bcc39e36f161568296512ad812e` |
| `paper/short_paper.md` | `7a69ecd9177b41fa3b3a9c50ebdad82e9d9d54661d6a8916bde4d6a98100f12f` |
| `paper/claims.csv` | `e768510a318532f200654c0e77527f043e65abc0030e9c160675595386ff3d89` |
| `paper/refs_frozen.bib` | `9d5432d7faf3ad28eb159945f239b1eb1fd67e1f76174ffca691f5c2f11a3da4` |
| `paper/figures/fig6_per_fold_auroc.png` | `d6d4a939335b2b88cbd8a3e7ef8e15738fd1270900facdcd584a25dc310fc36c` |
| `paper/figures/fig7_detectability.png` | `b9d3fa4ce0e07c17bd1b57b6ec77d2ec1ed5c887085db60e14c6545aea62f1dd` |
| `tasks/submission_readiness_20261003/VENUES.md` | `588889e73a664ef7461415b0c92b88b8678eb130020ceb61fe3f5d5119a3d441` |
| `tasks/submission_readiness_20261003/AUDIT.md` | `1ba349faf22050c5627146319aab1cf3b554e05967f0ed49cfef05de11ff6195` |
| `tasks/submission_readiness_20261003/INPUTS_NEEDED.md` | `094292e07f0d3685947a16a40228213129dbf67f12bc9bbb3c8e01ce2065c7e3` |
| `docs/nn_v2/ladder_verification.json` | `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| `docs/nn_v2/ladder_summary.json` | `9add634e69dfbd7de1f764d6d7d3e3a217101efec2445c426b1b7be3f4ebc4c7` |
| `MOM/README.md` | `18e8c8ade62a075097a09e1da7565c5a6c33566d5298f0f319e5d9fb2ed6a4c9` |
| `MOM/2026-07-02/README.md` | `d411701b09dc34cfaf0674ea82733341ff8cd3355d9dd1823666242845212fa0` |
| `MOM/2026-07-21/README.md` | `cf732e339e5348d260c121b10f5b0f4dcb15d276cdf3bdaf5aadb3c7ee25e0e6` |
| `tasks/next_action_20261003/CLOSEOUT.md` | `db21d4855654ceb4262945b436238032517bab1a343aa20fc77eb49cbfa59b71` |

`todo.md`, `status.md` and `docs/INDEX.md` are updated in this handoff pass; recompute their digests after commit if a later register needs them.

---

## Stop rule

Stage complete at `READY_FOR_RESEARCHER_REVIEW`. No further S1–S3 re-audit is required for this bounded stage.
Research fits, downloads, external scores, counter resets, outbound messages, submission and push remain outside scope.
The researcher closes H1–H12 (and optionally H13), then owns venue export and any portal submission.
