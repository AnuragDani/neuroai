# Bounded preparation closeout — 2026-10-03

**Status: preparation complete; submission pending.** This completes only Tasks 1–4 of this dated plan.
The wider study remains partial. No new experiments or independent biological-state claims are authorized.

## What finished

| Task | Evidence | Result |
|---|---|---|
| 1: evidence boundary | [EVIDENCE_BOUNDARY.md](EVIDENCE_BOUNDARY.md) | Exact arm/source leaves and preserved scientific labels |
| 2: bounded manuscripts | [PAPER_COMPLETION.md](PAPER_COMPLETION.md), [full paper](../../paper/draft.md), [short paper](../../paper/short_paper.md) | Venue-neutral declaration placeholders, open items with owners |
| 3: offline desk decision | [EXTERNAL_DESK_DECISION.md](EXTERNAL_DESK_DECISION.md) | NO_GO_NOW, inherited contracts, no acquisition |
| 4: closeout | This document and updated task lists/status | Completion evidence recorded, no automatic continuation |

GNHF committed Tasks 1–3 in 7ef505a, a58be8e and 755b4d0. It stopped during Task 4 at 2,366,372 / 2,000,000 tokens.
The run totals include 2,063,680 cache-read tokens, 266,623 input tokens and 36,069 output tokens.
Its log records three successful iterations and an aborted fourth iteration. Codex completed the remaining closeout directly.
This does not convert the original runner status to success. The saved run log remains unchanged.

## Fresh final verification

Commands ran from the repository root without learning or `--write`:

```sh
.venv-p22/bin/python paper/check_paper.py --json
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```

- Paper checker: exit 0, ok=true, failures=0.
- Saved-fold replay: exit 0, PASS, problems=[] and advantage=false.
- Primary R3_ca minus R3_tc BA: +0.0266667, CI [-0.0250,+0.0767857], margin 0.07.
- Evidence-boundary register: 17/17 listed hashes match live files.
- Paper-completion register: 8/8 listed hashes match live files.
- Immutable full-executor lock: 17/17 live hashes match.
- Original July 2 MOM SHA-256: 38871f240c5a0f7f95ea9e279fa5b73a4306152e24a6b1b5515a509011529a91.
- Original July 21 MOM SHA-256: 0bce4ea91e7daefac37645bfc6dc35b4742473ea3b5152737ded8bf9eff3ace2.

The manuscript diff against the launch commit changes revision metadata and declaration stubs only.
Accepted scientific sections and claims.csv remain unchanged. Numerical checks do not certify all citation meanings or figure contents.
Manual claim/citation/figure checks and their limits are recorded in PAPER_COMPLETION.md. Figure-content/venue packaging checks remain partial.
This is preparation completion, not new scientific acceptance or submission certification.

The offline bag declares the DSdevctx fragment package at 20,610,908,160 bytes. Actual availability and recount feasibility remain unresolved.
The desk note's future-contract wording now requires resolution. A waiver cannot establish exact input compatibility or specimen independence.

## Definition of Done evidence

| Criterion | Completion evidence |
|---|---|
| Outputs exist | Task table and resolving links above |
| Evidence is traceable | Exact leaves/hashes in EVIDENCE_BOUNDARY and live matches above |
| Paper checks pass | Fresh commands above, manual checks and limits in PAPER_COMPLETION |
| Scientific limits explicit | B_NULL, M9 NOT_AUTHORIZED, M10 diagnostic-only, prior INVALID/NO FIT, E5 NO_GO, Q2 ENDPOINT_UNRESOLVED and POWER_UNESTABLISHED retained |
| Desk bounded | Source-backed NO_GO_NOW, no download/scoring recommendation |
| Open items honest | Researcher-owned completion conditions in PAPER_COMPLETION and manuscript declarations |
| Completion evidenced | This closeout, final hashes below and consistent task/status marks |
| Scope intact | Document-only tracked changes, worker zero-activity records, unchanged source/gate hashes and offline verification |

## Remaining submission items

The researcher owns funding, conflicts, authors/affiliations/contributions and ethics/data-use statements.
Venue selection, accession/release links, bibliography typesetting, figure packaging and venue formatting remain open.
Exact completion conditions are listed in PAPER_COMPLETION.md. Do not mark the papers submission-ready before these requirements close.
No professor response is required to collect these facts or choose a venue.

## Stop rule

This preparation stage ends here. No restart of the four-task GNHF job is needed.
Research fits, downloads, external scores, counter resets, outbound messages, submission and push remain outside this completed stage.
A new research proposal requires its own question, evidence, exact input contracts and reviewed execution scope.

## Final artifact hashes

Paths are relative to the repository root. CLOSEOUT.md excludes its own hash to avoid self-reference.

| Artifact | SHA-256 |
|---|---|
| `paper/draft.md` | `fa16ffad2feb37d5a22a30b492c587a4a8920bcc39e36f161568296512ad812e` |
| `paper/short_paper.md` | `7a69ecd9177b41fa3b3a9c50ebdad82e9d9d54661d6a8916bde4d6a98100f12f` |
| `paper/claims.csv` | `e768510a318532f200654c0e77527f043e65abc0030e9c160675595386ff3d89` |
| `tasks/next_action_20261003/EVIDENCE_BOUNDARY.md` | `703761e88a22f3f091d9a446f9a1eaebd03f59596ed84b3e705f0a482ca53dc5` |
| `tasks/next_action_20261003/PAPER_COMPLETION.md` | `d09ae59436f7f70967b2830914d0975e93b4508a05cc22f3fc0b531976913f16` |
| `tasks/next_action_20261003/EXTERNAL_DESK_DECISION.md` | `50ea32c0b77eb7dfc690ababfeab01996586fdb1d3ff8c3b69412dce524fc91e` |
| `tasks/next_action_20261003/PLAN.md` | `6c608a855e1a30c8b5f60532d37ca5946ce20c8207581dbf82323eeab4a19687` |
| `tasks/next_action_20261003/todo.md` | `71f70b2b5714fe2d94ac65fdf0dd163d57bef10bb6e5e3ebe6b64b003d8e83dc` |
| `tasks/todo.md` | `ddd65aecbf7ad66770944f94241c13bf896eaa12421ae4b263cf4e0b0ae9a29b` |
| `status.md` | `5767164dbf0db06bb3b4bd99173a2776072fe877d33769a8046b1b040b9bbc6b` |
| `docs/INDEX.md` | `9be35bad03f9fdf0a34b85959ee1dade6dc68e3c047232f3791a13f84bd150f1` |
| `docs/nn_v2/ladder_verification.json` | `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| `docs/nn_v2/ladder_summary.json` | `9add634e69dfbd7de1f764d6d7d3e3a217101efec2445c426b1b7be3f4ebc4c7` |
| `configs/execution_repair_full_executor_lock_2026-10-02.json` | `6a7dee7e1253478034db145f2269b4c209232a7fd206e9e6363c9deab83ce571` |
