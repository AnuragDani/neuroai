# GUIDANCE_AND_CLAIMS — R4 objective and endpoint reconciliation

**Disposition:** `GUIDANCE_CLAIMS_PASS`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`  
**Dependency:** R0 PASS. No fits, downloads, package installs, vault/MOM/sent-packet edits, or scientific-label overturns.  
**Machine record:** [guidance_and_claims.json](guidance_and_claims.json)

Professor records remain distinct from worker interpretation. Historical Q2 `ENDPOINT_UNRESOLVED` is **not** silently relabeled PASS.

## Source hashes (read-only)

| Source | Absolute path | SHA-256 |
|---|---|---|
| July 2 vault MOM | `/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/2026-07-02/MOM_07-02-2026_Transcript_and_Meeting_Notes.md` | `38871f240c5a0f7f95ea9e279fa5b73a4306152e24a6b1b5515a509011529a91` |
| July 21 vault MOM | `/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/2026-07-21/MOM_07-21-2026_Transcript_and_Meeting_Notes.md` | `0bce4ea91e7daefac37645bfc6dc35b4742473ea3b5152737ded8bf9eff3ace2` |
| User attestation (worker-side) | `plan/real_data_attestation_2026-09-08.json` | recomputed at record time in JSON |
| Q2 endpoints | `…/next_stage_20260930/ENDPOINTS.md` | prior disposition `ENDPOINT_UNRESOLVED` retained |
| Failure-audit PLAN claim hierarchy | this stage `PLAN.md` §§ Professor guidance | authoritative four-level hierarchy |

Worktree `MOM/2026-07-02/` and `MOM/2026-07-21/` are navigation pointers only.

## A. Guidance-to-claim table (professor vs worker)

Exact MOM anchors. **Professor request** = transcript/direction text. **Worker restriction** = later plan/gate/attestation rule, not a professor quote.

| ID | Exact professor passage (anchor) | Professor request | Worker restriction (not professor text) | Applicable claim level(s) |
|---|---|---|---|---|
| G1 | Jul 2 [00:00]: “leverage the existing architecture and make mathematical tweaks… loss function… residuals can remove non-clinical factors.” | Mathematical customization of architecture/loss; residualize non-clinical factors | Customization only when it solves a measured defect and is verified against primary methods (failure-audit PLAN R7; NN plan D1/D10) | 1–2 (software/computational); not by itself biology |
| G2 | Jul 2 [00:36]: “coarse categorical results or individual-person-level results are too coarse… specific cell type or subtype as cohorts and study gradual spectrum changes.” | Move beyond person-level coarse outputs toward cell-type cohorts and gradual spectrum | Worker used donor DS classification as training signal + N16 spectrum readout (NN plan D2); spectrum used RNA-derived strata — **descriptive**, not independent state truth | 3 descriptive if construct disclosed; **not** 4 without orthogonal state |
| G3 | Jul 2 [14:12]: scANVI “uses labels for classification. If our method uses a different supervision setup, the comparison is not apple-to-apple.” | Equal / matched supervision when comparing methods | Equal donors/splits/features/head/budget across arms (NN plan D5); S9 seven-arm equal supervision | 1–2 |
| G4 | Jul 2 [19:30]: “We do not have a wet lab, and cell subtype categorization is already saturated.” / [20:51]: “Do not select the cell subtype categorization direction. Select something more granular, such as cell-state-related…” | Avoid saturated subtype classification as main direction without wet-lab path; prefer granular state/spectrum or related | Author cell types = strata only, never prediction target (NN plan D4); Q2 rejects RNA clusters as independent cell-state truth | Blocks claim-4 subtype/state as wet-lab-independent; does **not** forbid claim-1/2 software or masked-modality tasks |
| G5 | Jul 21 Direction: “Treat the Tasic pipeline result as an engineering validation… not as final disease or independent-multimodal evidence.” / [00:00]: gene-defined labels → circular classification | Tasic = engineering check only | No Tasic accuracy-superiority claim; PCA-proxy not an independent modality (Jul 21 Direction + [12:12]) | Clarifies claim-1 vs claim-4 |
| G6 | Jul 21 [03:40]: stratified / donor-level downsampling | Stratified and donor-aware sampling | Q4 targeted sampler; donor-held-out splits default | All empirical tasks |
| G7 | Jul 21 [14:02]–[17:39]: find a case that differentiates models; concat as simple fusion baseline; independent modalities (e.g. gene + morphology / RNA+ATAC) | Discriminating multimodal benchmark; concatenation required baseline; independently measured modalities | S9 analytic pairing-use chose software control for routing/pairing (claim 1); primary ladder used paired RNA/ATAC with concat/CA | 1–2 (descriptive level-3 remains under G2 / construct-validity rules, not this multimodal-benchmark row) |
| G8 | Jul 21 Direction + To-Do 10: faithfulness — clamp, permutation, ablation, seeds, held-out donors (Anurag [12:12] restates the same plan; not a professor quote) | Direct faithfulness / held-out intervention tests | N13 faithfulness suite; within-donor ATAC permutation (pairing break) | 1–2 required for routing claims; 3–4 when claiming modality use |
| G9 | Jul 21 Direction: “Keep disease-specific training pending until the scientific objective and dataset are approved.” / [24:15]: “anchoring on a disease… classifying disease versus control” proposed as possibility | Disease-vs-control is **one proposed direction**, pending objective/dataset approval; not the sole test of routing | `plan/real_data_attestation_2026-09-08.json`: user-reported Fang approval for **existing public-data** RNA/paired plans; `professor_approval_date: null`, `independently_verified: false`; decision_log still distinguishes attestation from dated Fang record | Disease classification under existing public paired study proceeds as **specimen outcome** (not cell-state); do **not** claim dated independent Fang endorsement of a *changed* disease objective |
| G10 | Jul 21 [25:26]: customize loss/reward/hyperparameters from papers, not defaults only | Concrete paper-grounded customization | Recorded only when defect established (R7); GenAI claims verified (Jul 2 [12:09]) | Implementation quality across levels |

## B. Four-level claim hierarchy and endpoint gates

Hierarchy from this stage PLAN (immutable definitions). Existing gates mapped per level — **not** one universal wet-lab endpoint.

| Level | Claim type | What validates it | Existing gate / evidence | Status with current inputs | Prospective amendment? |
|---|---|---|---|---|---|
| **1** | Software / mechanism control | Analytic target + oracle; planted pairing/null | S7/S8/S9 protocol + review + fit/replay; R1–R3 audits | **Proceeds** without biological endpoint. Prior S9 `INVALID` (null exchangeability + marginal) retained; corrected null/software tests remain in scope | None required to *run* claim-1; null design must be fixed before interpreting pairing-use |
| **2** | Computational prediction | Externally withheld measured genes/ATAC regions or predefined masked-modality objective; train/test masking + donor isolation | Donor-held-out splits; input/target disjointness; leakage fixtures; no independent cell-state label required | **Can proceed** on current paired RNA/ATAC matrices for a masked-measurement / pairing prediction task. Does **not** prove biological state or causal mechanism | Prospective protocol must disclose estimand = computational prediction, not biology |
| **3** | Descriptive cell-state / program analysis | RNA-derived programs OK only with **explicit construct validity** and held-out readouts; same genes cannot define *and* evaluate the target | Q2: `author_cell_type`/SCT/N16 = RNA-derived proxies; N16 `SPECTRUM_NULL` descriptive | **Limited descriptive** analysis may proceed if construct, circularity, and non-independence are disclosed; splitting alone does not remove circularity | Amendment: allow level-3 *descriptive* reports without claiming independent biology; **do not** upgrade proxies to claim 4 |
| **4** | Biological state / perturbation | Independent measurement, perturbation, or defensible orthogonal validation commensurate with claim | Q2 `ENDPOINT_UNRESOLVED` — no maturation/state assay orthogonal to RNA | **Blocked** for independent cell-state/maturation biological claims on current H5AD | **No silent Q2→PASS.** Unlock only with new orthogonal measurement or prospective narrower claim that is *not* biological state truth |

### Endpoint-gate application rule (amendment record)

**Prospective amendment (worker, 2026-10-01):** The Q2 `ENDPOINT_UNRESOLVED` gate applies to **claim level 4** (and to any statement that silently promotes RNA-derived proxies to independent biological state). It is **not** a universal stop for claim levels 1–2, nor for explicitly limited claim-3 descriptive analysis. Historical Q2 disposition remains `ENDPOINT_UNRESOLVED` (not PASS). Relaxing the *scope of application* of the gate does **not** authorize a new biological claim or experiment by itself (Checkpoint B rule).

## C. Input–target overlap and permitted interpretation

| Construct | Overlaps NN RNA/ATAC inputs? | Permitted interpretation |
|---|---|---|
| Specimen disease / `group` (CON vs DS) | No (metadata) | Existing primary donor-level outcome; **not** cell-state; claim-2 computational DS prediction OK under disclosed estimand; claim-4 “cell state” forbidden |
| `dev_PCW` / stage | No | Age covariate; ≠ intracellular state |
| `author_cell_type` / SCT / lineage masks | **Yes** (RNA-derived) | Stratification/sampling only; claim-3 descriptive with disclosure; not claim-4 truth |
| N16 OOF disease scores × type | **Yes** (model-circular) | Descriptive spectrum readout only; forbidden as independent state target |
| Analytic planted pairing (S9) | N/A (synthetic) | Claim-1 software control only |
| Masked held-out genes/regions (candidate) | Target held out by construction | Claim-2 if masking + donor isolation verified |

## D. Can research proceed with current inputs?

| Path | Proceed now? | Condition |
|---|---|---|
| Claim-1 corrected software null / reproducibility | **Yes** (audit/decision stages) | Fix confirmed exchangeability / accounting defects; no S9 positive-result search |
| Claim-2 current-data masked-measurement / pairing prediction | **Yes, candidate for R5–R6** | Protocol freezes estimand as computational; leakage/disjointness tests; no biology upgrade |
| Claim-3 descriptive programs/spectrum | **Yes, limited** | Explicit construct validity; held-out readouts; no independent-biology language |
| Claim-4 biological cell-state / maturation | **No** | Remains blocked by Q2 until orthogonal measurement exists |
| Dataset change solely because of DS null / S9 INVALID | **No** | PLAN: dataset change needs addressed measured limitation, not null alone; NeMO external-test role preserved |

## E. Objective-approval reconciliation (disease task)

| Record | What it is | What it is not |
|---|---|---|
| Jul 21 pending disease approval | Professor pause until objective/dataset approved | Endorsement of every later worker disease protocol |
| `real_data_attestation_2026-09-08.json` | User report that Fang approved continuing **existing** public-data RNA/paired plans | Independently verified dated Fang letter; `professor_approval_date` is null |
| Primary ladder DS donor BA | Worker primary under attestation + frozen protocol | Proof of cell-state biology or professor endorsement of a *changed* disease objective |
| Failure-audit claim hierarchy | Worker scientific framing aligned to MOM | Not a professor email or sent packet |

**Conclusion:** Do not state that Professor Fang endorsed a changed disease task beyond the attested existing public paired/RNA scope. Disease-vs-control remains one valid *computational* direction among others; successful DS classification is not the only routing test (PLAN / G7–G9).

## F. Acceptance checklist (R4)

| Requirement | Status |
|---|---|
| Guidance-to-claim table cites exact original MOM passages | PASS (table A) |
| Professor requests separated from worker restrictions | PASS |
| Four-level hierarchy reviewed vs existing endpoint gates | PASS (table B) |
| Prospective amendment recorded without relabeling Q2 PASS | PASS (amendment record) |
| Computational / limited descriptive paths vs blocked biology recorded | PASS (tables C–D) |
| Later objective-approval / attestation considered | PASS (section E) |
| No new universal wet-lab requirement imposed on claim 1–2 | PASS |
| Fits / downloads / vault edits | None |
| Independent reviewer on endpoint construction / overlap / interpretation | PASS (agent `f7042b9d-22ff-46c9-a8bc-99f65c5dce5a`; see INDEPENDENT_REVIEW_R4_GUIDANCE.md) |

## Verification

```bash
export PYTHONPATH="$(pwd)/src"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -c "import p22; print(p22.__file__)"
/Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python -m pytest tests/test_failure_audit_guidance_r4.py -q
shasum -a 256 "/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/2026-07-02/MOM_07-02-2026_Transcript_and_Meeting_Notes.md" "/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/2026-07-21/MOM_07-21-2026_Transcript_and_Meeting_Notes.md"
```

Expected: exit 0; disposition `GUIDANCE_CLAIMS_PASS`; MOM hashes match PREFLIGHT; Q2 remains `ENDPOINT_UNRESOLVED`; scientific S9 `INVALID` retained.
