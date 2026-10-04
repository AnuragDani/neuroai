# Venue comparison — submission readiness 2026-10-03

**Status:** provisional recommendation only. Researcher selects the venue. No acceptance promise. No submission.

Access date for all primary pages below: **2026-10-03** (UTC-7 session).

Manuscript context (local, not a venue claim): accepted full draft is a bounded internal null benchmark (primary R3_ca − R3_tc **B_NULL**; advantage not demonstrated; equivalence not established; power **POWER_UNESTABLISHED**). Full draft ≈4052 words under local checker caps; short paper also exists. Venue fit must tolerate a **null / no-advantage** computational result, not a proven superior method.

## Network budget (this stage)

| Metric | Cap | Used (this iteration) | Notes |
|---|---:|---:|---|
| External requests | 24 | **≈25** (slight overage; stop) | 5 WebSearches + ~16 official-page fetches/timeouts + 4 curl retries that hit Cloudflare challenges |
| Downloaded documentation bytes | 32 MiB | **≈0.54 MiB** retained useful docs + ≈0.02 MiB challenge HTML | Aggregate ≈0.56 MiB ≪ 32 MiB |
| Datasets / matrices / author contact | forbidden | 0 | Not attempted |

Oversized-body abort rule: curl fetches used `--max-filesize 2097152`. No body exceeded the abort threshold. **No further external requests in later iterations of this stage** unless S3 can proceed from existing local primary sources; citation PDF retrieval is blocked by this exhausted request budget (do not reset the counter). Four OUP charge-page curls returned Cloudflare challenge HTML (403) and are failed access, not APC authority.

---

## Comparison table

| Venue | Aims / scope (official) | Article type considered | Negative / null suitability | Length limits | Required declarations (material) | Artifact / data-code policy | Charges / waivers | Fit for this manuscript |
|---|---|---|---|---|---|---|---|---|
| **BMC Research Notes** | Open forum for short reports across disciplines, including “valid negative results” and data notes ([submission guidelines](https://link.springer.com/journal/13104/submission-guidelines)) | **Research note** | **Explicit:** aims list “valid negative results”; research-note criteria list “Null results” ([research note](https://link.springer.com/journal/13104/submission-guidelines/research-note)) | Abstract ≤200 words; Introduction + main text + Limitations ≤**2000** words; ≤**3** figures/tables (extras as supplements) | Full Declarations block required (ethics, consent, data availability, competing interests, funding, contributions, acknowledgements; “Not applicable” allowed where section N/A) | Data availability statement required; public repository strongly encouraged / mandatory where community standard exists | APC **£1240 / $1790 / €1490** (acceptance-date pricing; country-tiered pilot; discretionary waiver at submission) | **Best documented fit** for a bounded null benchmark if shortened to note length |
| **BMC Bioinformatics** | Novel computational algorithms/software/models/tools for biological data; decisions by scientific validity, not perceived impact ([submission guidelines](https://link.springer.com/journal/12859/submission-guidelines)) | Research article (also Software, etc.) | **Not explicit.** Validity-without-impact wording helps, but aims emphasize **novel** methods/tools — do not infer null acceptance from computational-biology scope alone | Unresolved exact research-article word/page cap on the pages retrieved (article-type pages not fully enumerated within budget) | BMC Series Declarations pattern (data availability, competing interests, funding, contributions, ethics as applicable) — exact research-article checklist not fully copied here | Software articles have additional availability rules; research articles need data availability | APC **£2290 / $3090 / €2590** ([how to publish](https://link.springer.com/journal/12859/how-to-publish-with-us)); same waiver timing rules | Plausible if framed as a rigorous method comparison with null primary; weaker than Research Notes on explicit null language |
| **Bioinformatics (OUP)** | “New algorithms and databases that advance … in a **significant** manner” ([author guidelines](https://academic.oup.com/bioinformatics/pages/author-guidelines)) | Original Paper (≈7 pages / ≈5000 words excl. figures); Application Note shorter | **Not stated.** Scope language favors significant methodological advance; null benchmark is a poor match unless editors treat negative comparisons as advancing practice — **unknown**, not assumed | Original ≈5000 words; Application Note ≈2600 words or 2000+1 figure; exceeding limits may be rejected without review | Conflict-of-interest disclosure at submission; data availability statement required; structured abstract for Original Papers | Software/code availability rules detailed for method/software papers; reproducibility subsection for ML | Fully OA; APC **amount unresolved** (OA charge page Cloudflare-blocked on curl; author-guidelines charge table did not yield a reliable CC-BY APC figure in the converted text — only a garbled “Book review charge \| 3625 USD” row). LMIC / discretionary waivers exist; ISCB 15% discount stated | Risky for a B_NULL internal comparison; keep as stretch / transfer target only |
| **Bioinformatics Advances (OUP/ISCB)** | Companion to Bioinformatics; broader article types including Discovery Notes ([author guidelines](https://academic.oup.com/bioinformaticsadvances/pages/instructions-to-authors)); launch editorial notes transfer path from Bioinformatics | Original Article (≤8 pages); Application Note / Scientific Data ≤4; Discovery Notes ≤6 | **Not explicit** null policy. Broader scope than Bioinformatics, but Original Articles still judged under journal criteria — unknown for pure null benchmarks | Original ≤8 pages; abstract ≤200 words | Conflict disclosure; data availability required; public release of data/code “where ethically possible” as condition of publication | Strong data/code release expectation | Fully OA; APC **amount unresolved** (same Cloudflare block). ISCB member OA discount **20%** stated on guidelines page | Possible transfer landing if Bioinformatics declines; not first choice for explicit null framing |
| **PLOS Computational Biology** | “Exceptional significance”; Research/Methods/Software must show novel advances or profound biological insight; Methods/Software need outstanding / widely adoptable tools ([journal information](https://journals.plos.org/ploscompbiol/s/journal-information)) | Research / Methods / Software | **Poor documented fit.** Criteria require originality, innovation, high importance, significant insight — no negative-result track found on retrieved pages | Format-free initial PDF; revision formatting later ([submission guidelines](https://journals.plos.org/ploscompbiol/s/submission-guidelines)). Exact word caps not the binding constraint vs significance bar | Data + code availability policies for research articles; competing interests / funding standard PLOS forms (details on PLOS editorial pages; not all re-fetched) | Data and code must support reproduction | Fees listed on [plos.org/fees](https://plos.org/fees/); **journal-labeled APC for PLOS Comp Biol not reliably extractable** from the converted fees page (journal names stripped in the fetch markdown). Mark **unresolved**. Research4Life / PFA assistance exist | Not recommended as provisional target for this null benchmark |

GigaScience was sampled via [instructions to authors](https://academic.oup.com/gigascience/pages/instructions_to_authors) and [Technical Note](https://academic.oup.com/gigascience/pages/technical_note): strong open-data / open-code / GigaDB expectations. Exact APC unresolved (charges page blocked). **Not shortlisted** for provisional target: manuscript is a method comparison with null primary, not a data-release Technical Note, and data-hosting obligations would invent release commitments the researcher has not approved.

---

## Source register (URL → requirement → uncertainty)

### 1. BMC Research Notes — provisional target

| Item | Exact requirement (quoted/paraphrased from page) | URL | Uncertainty |
|---|---|---|---|
| Aims include negative results | “including … valid negative results, and scientific data sets and descriptions” | https://link.springer.com/journal/13104/submission-guidelines | None for the aims sentence; editorial practice still unknown |
| Research note includes null results | Criteria include “Null results” and short projects that “did not provide publishable results but represent valuable information regarding protocol and data collection” | https://link.springer.com/journal/13104/submission-guidelines/research-note | “Publishable results” wording is from their criteria list; our manuscript *does* have publishable null metrics — still within “Null results” |
| Length | Abstract 200 words; Introduction + main + Limitations **2000** words combined; ≤3 figures/tables | same research-note URL | Word-count method (what counts as “main text”) may differ from local checker |
| Declarations | Mandatory headings listed (ethics, consent, data, competing interests, funding, contributions, acknowledgements) | same | Exact ethics wording for secondary atlas reuse needs researcher confirmation |
| APC | £1240 / $1790 / €1490; charged at acceptance date; country-tiered pilot | https://link.springer.com/journal/13104/how-to-publish-with-us and submission guidelines fees section | Taxes; institutional agreements; discretionary waivers case-by-case |
| License | CC BY-NC-ND or CC BY | submission guidelines | Which license the authors choose is researcher-owned |

### 2. BMC Bioinformatics — alternate

| Item | Exact requirement | URL | Uncertainty |
|---|---|---|---|
| Scope | Novel computational algorithms/software/models/tools; validity-based decisions | https://link.springer.com/journal/12859/submission-guidelines | Whether a null attention-vs-concat comparison counts as “novel” is editorial |
| APC | £2290 / $3090 / €2590 | https://link.springer.com/journal/12859/how-to-publish-with-us | Same pilot/waiver caveats |
| Negative results | No explicit statement found on retrieved pages | — | **Unresolved** — do not infer |

### 3. Bioinformatics (OUP)

| Item | Exact requirement | URL | Uncertainty |
|---|---|---|---|
| Scope | Emphasis on advances “in a significant manner” | https://academic.oup.com/bioinformatics/pages/author-guidelines | High bar vs null result |
| Original Paper length | Up to 7 pages ≈5000 words excl. figures | same | Template vs format-free counting |
| Data availability | Required statement | same | Release URLs still researcher-owned |
| APC dollar amount | Required OA charge | OA/charges links | **Unresolved** — Cloudflare blocked direct APC page |

### 4. Bioinformatics Advances (OUP)

| Item | Exact requirement | URL | Uncertainty |
|---|---|---|---|
| Original Article length | Up to 8 pages; abstract ≤200 | https://academic.oup.com/bioinformaticsadvances/pages/instructions-to-authors | Page↔word conversion |
| APC | OA charge applies | same + OA page | **Unresolved** amount |
| ISCB discount | 20% member OA discount | same | Membership status unknown |

### 5. PLOS Computational Biology

| Item | Exact requirement | URL | Uncertainty |
|---|---|---|---|
| Criteria | Originality, innovation, high importance, significant insight, rigorous methods | https://journals.plos.org/ploscompbiol/s/journal-information | Null internal benchmark unlikely to meet “exceptional significance” as written |
| Methods/Software bar | Outstanding / widely adoptable | same | Not our claim |
| APC | Listed on PLOS fees page | https://plos.org/fees/ | **Unresolved** journal-specific dollar mapping from fetched markdown |

---

## Provisional recommendation

**Provisional target: BMC Research Notes — Research note.**

### Why (evidence-backed, not a promise)

1. Official aims explicitly include **valid negative results**; research-note criteria explicitly include **Null results** (unique among the five venues with a clear written match).
2. Article type matches a **bounded short report** rather than a claim of a superior new algorithm.
3. Current APC ($1790 / £1240 / €1490) is lower than BMC Bioinformatics on the same publisher’s official pages.
4. Required Declarations map cleanly onto the venue-neutral stubs already in `paper/draft.md` / `paper/short_paper.md` (still researcher-owned content).

### Adaptation implications for S2 (not done in this iteration)

- Condense to **≤2000** words for Introduction + main + Limitations; Abstract ≤200 with **Objective / Results** headings.
- Cap display items at **3** (move others to supplements); fix relative figure paths in the new copy only.
- Keep accepted numerical results unchanged; retain frozen citation keys.
- Preserve Markdown; Word/Springer export remains a later researcher/export step.
- Do **not** invent ethics approval, funding, conflicts, authors or release URLs.

### Explicit non-claims

- This recommendation does **not** predict acceptance.
- Computational-biology scope alone was **not** treated as negative-result acceptance for Bioinformatics, Bioinformatics Advances, BMC Bioinformatics, PLOS Comp Biol or GigaScience.
- OUP and PLOS Comp Biol **APC dollar amounts** remain unresolved after access/parsing failures; researcher must recheck before budgeting.

### Researcher decision still required

Confirm or replace this provisional target before any submission. If the researcher prefers a full-length computational-methods venue, **BMC Bioinformatics** is the documented alternate; length pressure is lower, null-result language is weaker.
