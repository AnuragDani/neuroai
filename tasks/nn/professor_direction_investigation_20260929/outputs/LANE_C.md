# Lane C — cohort, design adequacy, and biological-value audit

**Lane:** C only (metadata / saved-record inspection).  
**Branch:** `gnhf/read-users-anuragdan-ea5475`  
**SHA:** `808fa734a8dc2d89d34853204251bd9decea2a06` (S7-v2 review base; matches PLAN)  
**Date:** 2026-09-29  
**Scope lock:** no model fits, no data acquisition, no edits to scientific JSON / status / MOM / paper / packet / other lanes.  
**Companion table:** [COHORT_TABLE.md](COHORT_TABLE.md)

## Stop decision

**Lane C ACCEPT** — go/no-go recommendation recorded below with auditable sources.  
**Biological joint `A_ADVANTAGE` power:** `POWER_UNESTABLISHED` (inputs do not support a donor-n target).  
**Recommended next scientific path:** **bounded internal detectability-limit / null paper** (framing F4 already chosen). Independent paired external validation remains **blocked / deferred (T13)** pending QC, specimen-independence, and feature-compatibility preflight — not authorized from this lane.

---

## Exact sources inspected

| Role | Path | Live key facts used |
|---|---|---|
| Investigation plan | `tasks/nn/professor_direction_investigation_20260929/PLAN.md` | Lane C C1–C3; A_ADVANTAGE joint rule; evidence rules |
| Status / index | `status.md`, `docs/INDEX.md`, `AGENTS.md` | Primary `B_NULL`; power `POWER_UNESTABLISHED`; S7-v1/v2 `INVALID`; external deferred |
| Professor MOM (original) | Vault `MOM/2026-07-02/…`, `MOM/2026-07-21/…` (+ repo `MOM/*/README.md` indexes) | Jul 2: cell-state spectrum beyond coarse person-level; Jul 21: Tasic = engineering check; paired RNA/ATAC; concat baseline; faithfulness; complex differentiating benchmark |
| Protocol freeze | `docs/nn_v2/PROTOCOL_FREEZE.md` | Primary = R3_ca−R3_tc donor BA, margin 0.07, donor bootstrap |
| Primary verifier | `docs/nn_v2/ladder_verification.json` | estimate 0.0267; CI [−0.0250, 0.0768]; `advantage=false`; verdict PASS |
| Ladder summary | `docs/nn_v2/ladder_summary.json` | outcome `B_NULL`; secondary `LINEAR_SUFFICIENT` |
| Sampling / cohort | `docs/nn_v2/sampling_cap1000_seed22.json` | n_donors=30 (15+15); 248998 available / 30000 selected; 37 libraries; PCW10–20; H5AD sha256 `08d6eff…` |
| Spectrum | `docs/nn_v2/spectrum.json`, `SPECTRUM.md` | `SPECTRUM_NULL`; 9 eligible types; 0 Holm-sig; support floor excludes AST/MIC/… |
| Dosage / chr21 | `docs/nn_v2/chr21_excluded.json`, `v6/CHR21_FORCED.md` | `DOSAGE_DOMINATED`; chr21_dosage AUROC 1.0; forced CA−TC 0.060 [0.011, 0.113] = `D_SMALL_POSITIVE` (not A_ADVANTAGE) |
| Faithfulness | `docs/nn_v2/faithfulness.json` | `CA_PAIRING_UNUSED`; `pc_status=N/A` |
| Nuisance | `docs/nn_v2/NUISANCE_PROBE.md` | `R2_REJECTED` / `PROBE_DROP_INSUFFICIENT`; library probe unscorable 0/150 |
| Detectability (synthetic) | `docs/nn_v2/v6/detectability.json`, `DETECTABILITY.md` | S4 planted; n=30; detection fraction 0 for all δ≤1.0; `min_detectable_delta=null` |
| Finish feasibility | `tasks/nn/finish_20260928/FEASIBILITY.md`, `HYPOTHESIS.md`, `PLAN.md` | P0–P3 precision rules; A_ADVANTAGE definition; T13 external blocked |
| Paper framing | `paper/framing.md` | F4 detectability-limit paper; no method-advantage / transportability claims |
| External candidates | `docs/PAIRED_DS_MULTIOME_DATASET_OPTIONS.md`, `docs/PAIRED_MULTIOME_AUDIT.md` | GSE305146 = same cohort; NeMO 13+13 reserved external; GSE280175 RNA-only |
| Results claim limits | `docs/nn_v2/NN_V2_RESULTS_2026-09-23.md` | Study `STUDY_PARTIAL`; external T13 deferred |

**Professor vs worker:** July 2/21 vault MOM = professor direction. September status/S7/finish docs = worker evidence and handoffs, not new professor instructions. No dated archived professor reply to the September 29 package is recorded in the inspected sources.

---

## C1 — Biological question map

| Question class | Professor intent (July) | What the cohort actually measured | Adequacy on n=15+15 internal DS multiome |
|---|---|---|---|
| **Q-donor disease prediction** | Fair multimodal comparison vs concat/simple baselines (Jul 21); not Tasic label recovery | Donor DS vs CON from paired RNA+ATAC; primary CA−TC | **Answered as null for CA advantage:** verifier `B_NULL`. Dosage alone separates perfectly (AUROC 1.0). Beyond-dosage disease prediction is **not** supported as a CA-specific finding. |
| **Q-cell-state spectrum** | Gradual cell-state / spectrum beyond coarse person-level (Jul 2 [00:36]/[20:51]) | Donor-trained per-cell scores → per-type DS−CON donor-mean diffs | **Not demonstrated:** `SPECTRUM_NULL` (9 eligible types; Holm nonsignificant). Scores inherit donor disease labels; no independent biological state readout. |
| **Q-regulatory / pairing mechanism** | Paired independent modalities + faithfulness (Jul 21) | I3 pairing shuffle; ATAC use; attention readouts | **Not demonstrated:** `CA_PAIRING_UNUSED`; PC `N/A`; routing `NOT_SHOWN_USED` (from results claim limits). No mechanism claim justified. |
| **Q-dosage / chr21 confounding** | (technical necessity of fair controls) | chr21-excluded + chr21-forced sensitivities | **Dosage-dominated:** N11 `DOSAGE_DOMINATED`. Chr21-forced secondary `D_SMALL_POSITIVE` is **not** primary attention evidence and **must not** be treated as `A_ADVANTAGE`. |

### Cohort structure that bounds beyond-dosage questions

- **Donors:** 15 DS + 15 CON (sampling artifact; spectrum docs agree).
- **Age:** PCW 10–20 uneven (e.g. PCW12/13 = 6 each; PCW10/14/15 = 1 each) — age–disease imbalance risk for spectrum claims.
- **Libraries:** 37 unique libraries across 30 donors — multiplex / library structure present; library nuisance probe **unscorable** under donor-held-out splits.
- **Cell-type support:** 9 types meet floor (≥20 cells/donor and ≥8 donors/group); 6 types excluded (AST, MIC, NEU_RELN, NEU_low, OPC, VASC) — spectrum coverage incomplete for rare types.
- **ATAC:** paired by design in Lattke/GSE305146; peak-set compatibility across libraries/cohorts remains a separate preflight (audit: zero shared exact peak intervals between example libraries).

**C1 verdict:** The internal cohort can support an honest **donor-level method-null / dosage-dominated** report. It does **not** currently support a defensible beyond-dosage cell-state or regulatory claim with independent biological support.

---

## Three quantities that must stay distinct

| Quantity | Definition | Saved value / status | Not to be confused with |
|---|---|---|---|
| **Synthetic label amplitude (δ)** | Planted S4 context-interaction strength in detectability grid | δ ∈ {0.1…1.0}; X4 task | Between-model CA−TC effect; biological power |
| **Observed between-model effect** | Real-label R3_ca − R3_tc donor BA (and synthetic CA−TC under planted δ) | Primary estimate **0.0267**, CI **[−0.0250, 0.0768]**; X4 mean contrasts ≈ −0.01…0.03 | Joint `A_ADVANTAGE` probability; proof of underpowering alone |
| **Biological joint `A_ADVANTAGE` probability** | P(estimate ≥ 0.07 **and** CI lower > 0) under a justified donor sampling design for a real biological estimand | **`POWER_UNESTABLISHED`** | Narrow synthetic CI; selected-screen control contrast; chr21-forced secondary |

**Joint success event (frozen):** estimate ≥ 0.07 **and** 95% donor-bootstrap CI lower bound > 0 (`tasks/nn/finish_20260928/PLAN.md` / `HYPOTHESIS.md`). CI lower need **not** be ≥ 0.07.

---

## C3 — Design adequacy / power sketch

### What saved outputs allow

1. **Descriptive precision at n=30 (real primary):** CI half-width ≈ 0.051 around estimate 0.0267. Point estimate is **0.043 below** the 0.07 margin; CI includes 0. Precision alone does not explain the null — the estimate never cleared the margin (`FEASIBILITY.md`).
2. **Synthetic detectability at n=30 (X4 S4):** for all planted δ ≤ 1.0, detection fraction = 0 (CI excludes 0 in 0/5 repeats). `min_detectable_delta = null`. Mean CA−TC contrasts remain ≪ 0.07. Reading in JSON: planted interaction only; **no biological claim**.
3. **Implication:** non-detection mixes (a) small realized CA−TC gap under current architecture/protocol and (b) donor-bootstrap width. Scaling donor n without a CA-unique between-model effect is **not** a justified plan (`FEASIBILITY.md` Diagnosis).

### Simulation assumptions (explicit; not a power certificate)

If a future donor-level simulation were attempted from **saved** inputs only, the admissible assumptions are:

| Assumption | Status from saved records |
|---|---|
| Design effect / true between-model Δ | **Unknown.** Real Δ̂ ≈ 0.027; synthetic X4 mean contrasts ~0–0.03; no CA-unique Δ ≥ 0.07 observed |
| Outcome variance / ICC | Partially reflected in existing donor-bootstrap widths; **no separate ICC estimate** archived for power |
| Target detection probability | Protocol exploratory screen used 0.8 in X4 / P2 language — **not** established biological power |
| Same protocol, arms, aggregation, bootstrap | Required; changing any invalidates transfer from X4 |
| Synthetic confirmation ≠ biological power | P2/P3 in `FEASIBILITY.md`: fresh synthetic seeds on reused cohort background are **not** independent biological cohorts |

**Because a plausible between-model design effect ≥ 0.07 is not identified in saved outputs, Lane C marks `POWER_UNESTABLISHED` and does not output a spurious donor-n target.**

### Separate biological estimand (spectrum)

Donor-mean score diffs exist with CIs, but all Holm-adjusted tests are nonsignificant at this n. No independent cell-state assay, confound-controlled estimand, or external spectrum replication is available. **Biological spectrum power also remains unestablished**; no go for a new spectrum claim on this cohort alone.

---

## C2 — External paired-cohort feasibility (metadata only)

| Candidate | Role | Donors | Paired RNA+ATAC | Independence | Access / file status (from records) | Blockers for validation **now** |
|---|---|---|---|---|---|---|
| **GSE305146 / CELLxGENE f16c25da…** | Internal development (current study) | 15+15 | Yes | **Same cohort** as current H5AD | Local H5AD hashed; GEO MEX audited | Cannot serve as independent external validation |
| **Vuong / NeMO `col-umstjg0`** | Reserved external multimodal | 13+13 in metadata | Yes (processed MEX) | Different study; IDs differ; **specimen overlap unresolved** | Open processed counts listed (~2.11 GiB core); controlled raw needs NIMH approval | QC discrepancy 117532 vs 113801 (−3731) unresolved; age unit GW vs PCW; peak/feature compatibility; no accepted external evaluation run (T13) |
| **GSE280175** | RNA-only external | 5+5 | **No** | Different study | Public GEO | Cannot close multimodal gap |
| **HF brain Zarr / GSE204684** | Pretrain / engineering only | N/A for DS design | No / no DS arm | Overlap risk / no DS | Public | Not DS paired validation |

**Feasibility verdict:** An independent paired-validation **candidate exists** (NeMO), but acceptance preflight is **not complete**. Expected transfer/compute were inventoried in dataset-options (~2 GiB counts; fragments ~19 GiB optional) — **not** acquired by this lane. Leakage risk: fitting or feature selection on NeMO would invalidate external contrast; same-study CELLxGENE/GSE305146 must never be labeled external.

**Practical external margin (record only, not power):** dataset-options formula at 13+13 → practical margin **0.08** if that cohort were accepted — larger than internal 0.07; still not a power guarantee.

---

## Cohort decision matrix (go / no-go)

| Path | Go? | Why |
|---|---|---|
| Bounded internal paper (F4 detectability-limit / advantage-not-demonstrated) | **GO** | Primary `B_NULL`, spectrum null, dosage-dominated, faithfulness unused, framing already F4; matches professor honesty rules |
| New real-label CA advantage fit on same 30 donors | **NO-GO** | Between-model Δ̂ ≪ 0.07; `POWER_UNESTABLISHED`; S7 controls `INVALID` (method path separately gated — out of Lane C ownership) |
| Beyond-dosage cell-state / regulatory claim on internal cohort | **NO-GO** | `SPECTRUM_NULL`; no independent biological readout; chr21-forced secondary ≠ primary |
| Independent paired external validation (T13) | **NO-GO now / BLOCKED** | NeMO QC + specimen independence + feature contract unresolved; acquisition not authorized; study remains `STUDY_PARTIAL` |
| RNA-only external (GSE280175) | **Not multimodal** | Orthogonal RNA track only; does not answer CA pairing question |

---

## Missing data / unresolved inputs

1. Accepted NeMO QC reconciliation for the 3,731-nucleus release gap.  
2. Certified specimen non-overlap crosswalk (UCLA/NIH vs HDBR provenance documented as no-overlap-evidence, not certified identity).  
3. Cross-cohort ATAC common-region / recount contract acceptance.  
4. Saved planted PC models under ladder_v3 (`pc_status=N/A`) — blocks pairing-use claims; method repair is Lane A/B territory.  
5. Any dated professor reply to the September 29 package (none in inspected record).  
6. Justified biological between-model design effect for joint `A_ADVANTAGE` simulation — **absent** → power stays unestablished.

---

## Comparison: bounded internal paper vs feasible independent paired validation

| Dimension | Bounded internal paper | Independent paired validation |
|---|---|---|
| Evidence ready | Yes — frozen ladder_v3 + sensitivities + claim ledger | No — candidate only |
| Scientific claim allowed | Advantage not demonstrated; dosage limits; detectability limits; no transportability | Would require accepted cohort + frozen external protocol + post-preflight evaluation |
| Risk if forced now | Overclaim (equivalence, mechanism, spectrum localization) | Invalid “external” success from unresolved QC/overlap/features |
| Alignment with July direction | Honest null / non-demonstration is valid; Tasic not promoted | Matches Jul 21 pivot to true independent modalities **only after** preflight |

**Lane C recommendation:** Prefer **bounded internal paper**. Treat external paired validation as a **separate later phase** after explicit access/QC/independence/feature gates — not as a fix for internal `B_NULL` or `POWER_UNESTABLISHED`.

---

## Acceptance checklist (Lane C)

| Deliverable | Status |
|---|---|
| Cohort decision matrix | Done (above) |
| Explicit available / blocked inputs | Done (Missing data + C2 table) |
| Auditable power assumptions; `POWER_UNESTABLISHED` when unsupported | Done |
| Distinguish δ / between-model effect / joint A_ADVANTAGE probability | Done |
| Bounded paper vs external validation comparison | Done |
| Branch / SHA / exact sources | Done |
| Compact cohort table | [COHORT_TABLE.md](COHORT_TABLE.md) |
| No fits / acquisition / shared edits | Honored |

**Stop reason:** Lane C acceptance criteria met; report committed locally with evidence. No push or merge.
