# Prospective path — one hypothesis and frozen criteria (2026-09-28)

Hypothesis freeze only. Bounded S7 synthetic fits may follow the September 29 manual execution runbook; no real-label fits, gate changes, downloads, external validation, email, or push.
Depends on [DIAGNOSIS.md](DIAGNOSIS.md). Finished primary (`ladder_v3` `B_NULL`) and gates stay unchanged.
Feasibility / power design and ordered execution tasks: [FEASIBILITY.md](FEASIBILITY.md) (PLAN item 3 COMPLETE).

## Choice (one path)

**Selected path: method-advantage (attention over fair matched/simple baselines).**

Not selected now: a new beyond-dosage biological estimand. Saved evidence shows disease discrimination is dosage-dominated and learnable by simple controls; there is no positive internal beyond-dosage CA result to extend. That path stays deferred unless a separate biological question and cohort design are declared later.

## Hypothesis

**H1 (prospective).** Under a redesigned planted interaction that is pairing-sensitive and not solved by matched non-attention fusion/concat arms, cross-attention (CA) recovers the label with a `CA_FAVOURED` regime and shows I3 pairing-use sensitivity on a saved positive-control (PC) model; only after that control passes may a new real-label CA−matched-baseline contrast be considered under frozen A_ADVANTAGE rules.

**Scientific reading of H1.** This tests whether the architecture/protocol can isolate an attention-specific advantage at all. It does **not** claim the finished primary was underpowered alone, and it does **not** authorize searching finished-primary variants until a control succeeds.

## Estimand

| Layer | Estimand | Unit | Contrast |
|---|---|---|---|
| Gate 0 (required first) | Planted regime label under `CA_FAVOURED` rule from decision tree N4 | Predeclared S7 rho=1.0 cell | CA mean donor BA − best non-attention arm ≥0.07 (and regime labeled `CA_FAVOURED`) |
| Gate 0b (required with Gate 0) | Pairing PC sensitivity | Held-out within-donor ATAC shuffle on retained S7 rho=1.0 CA fold models | Predeclared donor log-loss drop CI lower >0; checkpoint reload and identity checks pass; `pc_status` must not remain `N/A` |
| Primary (only if Gate 0 + 0b PASS) | Same finished rule, new protocol instance | Donor | CA − matched TC (and vs best fair simple baseline declared in protocol) donor balanced accuracy |
| Explicit non-estimands | Finished `ladder_v3` primary; chr21-forced ladder_v4 pooled; dosage AUROC; gene-activity secondary | — | Do not re-label or replace |

## Frozen comparison set (prospective; not a new run)

Declared before any authorized fit:

1. **CA arm:** existing N4 architecture and hyperparameters, frozen in [BENCHMARK_SPEC.json](BENCHMARK_SPEC.json). This synthetic control is not a new R3 biological primary.
2. **Matched neural baseline:** token-concat / TC twin with parameter match within 10% (finished rule).
3. **Fair simple baselines (must beat best of these for `CA_FAVOURED`):** at least `logreg_concat`, `rna_atac_concat` (feature-concat MLP), and `gated_fusion` — the arms that already solve S4/S5/S6 in saved evidence.
4. **Synthetic marginal controls:** `logreg_rna` and `logreg_atac` detect single-view shortcuts. Real-disease/dosage analyses remain outside this batch; no beyond-dosage claim.
5. **Representation:** default remains protocol freeze (RNA HVG + ATAC TF-IDF tie-break). Any chr21-forced or gene-matched representation change is a named secondary sensitivity, not a silent primary swap (ladder_v4 precedent).

## Positive-result criteria (frozen for this prospective path)

Reuse finished internal endpoint semantics; do not weaken.

### Gate 0 — pairing-sensitive CA-favoured control

- Fixed S7 rho=1.0 screen cell labeled **`CA_FAVOURED`** under the existing N4 rule, with complete five-fold coverage for all seven declared arms. CA beats **best** non-attention baseline by ≥0.07. Rho=0 and 0.5 are controls, not alternate candidate cells.
- That cell must be **pairing-sensitive by design** (within-donor shuffle removes planted cross-view covariance while preserving labels and marginal values; fusion-only solve without CA does **not** count as CA-unique).
- Saved fold models retained so PC is runnable (addresses finished `pc_status=N/A`).

### Gate 0b — PC / I3 sensitivity

- On saved Gate-0 CA models at S7 rho=1.0: within-donor ATAC pairing shuffle yields positive donor log-loss drop with 95% donor-bootstrap CI lower >0. Report BA drop as secondary. Checkpoint reload and identity intervention must reproduce original predictions.
- If Gate 0 fails or Gate 0b stays `N/A` / unused: **stop the method-advantage path**; retain finished internal null; do not proceed to new real-label fits for attention advantage.

### Primary positive (only after Gate 0 + 0b)

Identical to finished plan wording:

- **A_ADVANTAGE:** CA − matched TC donor balanced-accuracy **estimate ≥ 0.07** AND **95% donor-bootstrap CI lower bound > 0**, with all scientific validity gates PASS.
- Does **not** require CI lower bound ≥ 0.07.
- Method-paper framing further requires decision-tree robustness (**≥4/5** initialization seeds meet margin, else `A_FRAGILE`) and valid **`CA_USES_PAIRING`** including sensitive pairing control.
- Independent external replication remains a separate later phase; not part of this internal endpoint.

### Null / stop outcomes (honest)

| Outcome | Meaning |
|---|---|
| Gate 0 FAIL | No CA-unique planted control → method-advantage path closed; finished `B_NULL` stands |
| Gate 0b FAIL / N/A | Pairing-use unproven → no attention-mechanism claim; path stops |
| Primary B_NULL after gates | Advantage not demonstrated (not equivalence) |
| Blocked | Cohort/access/power design unavailable → record blocker; complete bounded paper without new fits |

## Declarations required before any new real-label fit

Copied from PLAN item 2; now instantiated in [FEASIBILITY.md](FEASIBILITY.md) (P0–P3, T1–T7):

1. **Pairing intervention + PC sensitivity** — Gate 0 / 0b above; model retention required.
2. **Donor-level uncertainty** — precision rules P0–P3; current X4 grid does **not** set donor n (`min_detectable_delta=null` at n=30 up to δ=1.0).
3. **Confound checks** — dosage / chr21-excluded / library nuisance reporting as in finished decision tree; no silent primary redefinition.
4. **Representation** — freeze file or named amendment; secondary vs primary labeled.
5. **Practical margin** — remains **0.07** on donor BA for A_ADVANTAGE unless a separate protocol amendment explicitly changes it (not authorized here).

## Explicit non-claims

- H1 is not supported by saved planted evidence today (`CA_FAVOURED` count = 0).
- Finished primary estimate 0.0267, CI [−0.0250, 0.0768] remains `B_NULL`.
- Chr21-forced 0.060 [0.011, 0.113] remains secondary only.
- Bounded S7 synthetic execution is specified by [EXECUTION_RUNBOOK.md](EXECUTION_RUNBOOK.md); launching it manually authorizes only that scope. Real-label fits require a separate design and authorization.

## Status of planning deliverables

| Deliverable | Status |
|---|---|
| Evidence-linked diagnosis | COMPLETE — [DIAGNOSIS.md](DIAGNOSIS.md) |
| One proposed hypothesis + estimand | **This file — COMPLETE** |
| Frozen comparison / positive-result criteria | **This file — COMPLETE** |
| Feasibility + ordered execution tasks | COMPLETE — [FEASIBILITY.md](FEASIBILITY.md) |

Finished primary endpoint and gates remain unchanged.
