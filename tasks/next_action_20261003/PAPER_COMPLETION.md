# Paper completion — next action 2026-10-03

Date: 2026-10-03. Scope: Task 2 bounded-paper preparation after Checkpoint A.
Dependencies satisfied: Task 1 / Checkpoint A PASS ([EVIDENCE_BOUNDARY.md](EVIDENCE_BOUNDARY.md)); Task 3 desk decision already published separately and does not alter accepted paper evidence.
No fits, downloads, research network requests, external scores, submissions, messages or push.

Status: **preparation complete; submission pending**.

## Changed sections

| File | Change |
|---|---|
| `paper/draft.md` | Revision label set to `PREPARATION_2026-10-03`. Added venue-neutral **Declarations** section with unresolved researcher-owned items. Accepted scientific Results/Discussion/Limitations/provenance text retained from the 2026-10-02 reconciliation. |
| `paper/short_paper.md` | Added matching venue-neutral **Declarations** section. Accepted numerical claims, dosage/null/power framing and M9 exclusion retained. |
| `paper/claims.csv` | Unchanged in this pass (ledger already reconciled 2026-10-02). |

Scientific numbers were not retargeted. Declaration stubs invent no funding, conflicts, author facts, ethics approvals, professor endorsement or submission readiness.

## Runnable checks (post-edit)

Commands from repository root (no `--write`; no learning):

```sh
.venv-p22/bin/python paper/check_paper.py --json
.venv-p22/bin/python gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3
```

| Command | Exit | Outcome |
|---|---:|---|
| `paper/check_paper.py --json` | 0 | `ok: true`; failures 0; citations/numbers/forbidden/figures/word_counts/claim_sources all empty |
| `gnhf/verify_ladder.py --run reports/generated/nn_20260923/ladder_v3` | 0 | `verdict: PASS`; primary estimate `0.026666666666666672`; CI `[-0.0250, 0.07679]`; margin `0.07`; advantage `false` |

Draft word counts after edit: total 4052/5000; Abstract 159/200; Methods 1094/1400; Results 1298/1500; Introduction+Related Work 521/900; Discussion+Limitations 611/700. Declarations sit outside those section caps.

## Manual claim checks (scientific wording)

Compared manuscript statements with [EVIDENCE_BOUNDARY.md](EVIDENCE_BOUNDARY.md) and live gate leaves. The numerical checker does not certify meaning; these are manual.

| Claim class | Manuscript location | Boundary / gate | Result |
|---|---|---|---|
| Primary R3_ca − R3_tc BA +0.0267, CI [-0.0250, 0.0768], margin 0.07, advantage not demonstrated / `B_NULL` | draft Abstract/Results; short Abstract/Results | Boundary primary table; `ladder_verification.json` `primary_recomputed`; `ladder_summary.json` `outcome` | PASS — matches; no equivalence claim |
| Absolute selected arms (R3_ca/tc, RNA, pseudobulk) | draft + short result tables | Boundary absolute metrics; verifier `per_arm` | PASS at displayed precision |
| Dosage dominance (chr21 dosage BA/AUROC 1.0; no-chr21 neural near chance / `DOSAGE_DOMINATED`) | draft Results; short Results/Discussion | Boundary absolute metrics + dosage caveat; draft cites chr21-excluded leaves | PASS |
| Power / detectability (`POWER_UNESTABLISHED`; synthetic detectability ≠ real-data power) | draft Results/Limitations; short Discussion | Boundary power label; `DETECTABILITY` framing in full-draft review | PASS |
| Later controls S7/S9/S10 `INVALID`, S8 `NO FIT` | draft Results; short §VI | Boundary scientific labels | PASS — no method-validation claim |
| M9 / masked pilot excluded; `NOT_AUTHORIZED`; E5 `NO_GO` | draft Internal provenance; short Internal provenance | Boundary M9/M10/E5 labels | PASS — excluded from accepted results |
| Endpoint / professor limits (`ENDPOINT_UNRESOLVED`; pending objective endorsement) | draft Internal provenance | Boundary Q2 + professor/worker distinction | PASS — no invented endorsement |

No unsupported scientific/source discrepancy found. Desk `NO_GO_NOW` remains outside manuscript accepted evidence.

## Manual citation checks

| Check | Result |
|---|---|
| Full-draft `[@key]` citations vs `paper/refs_frozen.bib` | PASS via `check_paper.py` citations report (empty failures) |
| Short-paper numbered references (6 works) vs [SHORT_PAPER_REVIEW_2026-10-02.md](../../paper/SHORT_PAPER_REVIEW_2026-10-02.md) existence/metadata notes | PASS against that dated metadata check; not a retraction or entailment audit |
| Full References section typesetting | Unresolved — keys validated; venue-style bibliography expansion still required (owner: Researcher) |

## Manual figure checks

| Check | Result |
|---|---|
| Embedded markdown image paths in `draft.md` exist on disk | PASS via checker (`fig1`, `fig2`, `fig4`–`fig7` PNG paths present under `paper/figures/`) |
| Historical Fig. 3 not embedded (older summary CI) | PASS — draft notes Fig. 3 omitted; file retained on disk without embedding |
| Figure scientific contents / venue packaging | Partial — paths resolve; venue-format panels/captions remain researcher-owned |

## Open declaration and venue items

Owner for every row: **Researcher**. These prevent a submission-ready label.

| Item | Status | Completion condition |
|---|---|---|
| Funding statement | Unresolved | Exact funding text or explicit none for chosen venue |
| Competing interests | Unresolved | Conflicts disclosure or explicit none |
| Author list and contributions | Unresolved | Confirm authors, affiliations and roles |
| Ethics / data-use statement | Unresolved | Confirm reuse language for source atlas and venue |
| Data availability | Partial | Add venue-required accession/repository links beyond atlas citation |
| Code / artifact availability | Partial | Add public release URL if venue requires one |
| Bibliography typesetting | Partial | Expand frozen keys to venue reference style |
| Figure packaging | Partial | Venue-format panels/captions if required |
| Venue length and style | Unresolved | Select venue; apply length/section/style rules |

## Artifact hashes (this pass)

| Path | SHA-256 |
|---|---|
| `paper/draft.md` | `fa16ffad2feb37d5a22a30b492c587a4a8920bcc39e36f161568296512ad812e` |
| `paper/short_paper.md` | `7a69ecd9177b41fa3b3a9c50ebdad82e9d9d54661d6a8916bde4d6a98100f12f` |
| `paper/claims.csv` | `e768510a318532f200654c0e77527f043e65abc0030e9c160675595386ff3d89` |
| `tasks/next_action_20261003/EVIDENCE_BOUNDARY.md` | `703761e88a22f3f091d9a446f9a1eaebd03f59596ed84b3e705f0a482ca53dc5` |
| `docs/nn_v2/ladder_verification.json` | `aec19fda88d60a30fda4ebdb9af53c790c62d5210206a5627c54521bfd947256` |
| `docs/nn_v2/ladder_summary.json` | `9add634e69dfbd7de1f764d6d7d3e3a217101efec2445c426b1b7be3f4ebc4c7` |
| `paper/FULL_DRAFT_REVIEW_2026-10-02.md` | `e46b8f8b8bc0b4a350aa7a762d569abc16a13ade93afc8c589ff28390684191f` |
| `paper/SHORT_PAPER_REVIEW_2026-10-02.md` | `33dfd092f176f9185d84aec4d48897074ffeb606364b6c88f5a46285ce8365ca` |

## Task 2 disposition

**COMPLETE.** Accepted numerical claims remain pinned; absolute performance, dosage dominance, null contrast and power limits remain explicit; M9 stays excluded; checker and replay PASS after edits; manual claim/citation/figure checks recorded; open declaration/venue items name owner and completion condition; no submission-ready claim.
