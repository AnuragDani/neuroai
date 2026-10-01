# C2 — Research-path decision (no fits)

**Disposition:** **NO FIT** — scientific design gate fails on Lane B S8 chance-null calibration.  
**Chosen path:** **(a) bounded internal null / detectability-limit paper** (paper framing F4).  
**Rejected:** (b) prospective S8 pairing-use synthetic control; (c) external paired-cohort acquisition/preflight as this run’s next action.  
**Recorded:** 2026-09-30.  
**Integration base:** `808fa734a8dc2d89d34853204251bd9decea2a06` on `gnhf/read-users-anuragdan-b61180`.  
**Lane snapshots:** `continuation/lane_reports/` from Lane B `4d0c3b9` and Lane C `010a07f` (copied with SHA; branches not merged).

No fits, package installs, pushes, merges, vault/packet/MOM edits, or status claim that S8 was frozen. C3–C5 are **not authorized**. Proceed only to C6 truthful handoff.

Professor sources remain July 2 / July 21 vault MOM. Lane A recovery, Lane B, and Lane C are worker evidence.

---

## 1. Lane audits (against live evidence)

### 1.1 Lane B taxonomy vs bibliography and code

| Lane B claim | Check | Verdict |
|---|---|---|
| CA / Transformer multimodal citations [B5]–[B7]; InfoNCE [B3]/[B4]; MIL [B1]; GRL adversary [B2]; NMF programs [B9]; WNN-style gate precedent [B8]; attention-not-explanation [B11]; gene-activity [B13] | Matches frozen `tasks/nn/plan.md` §6 B1–B14; no invented primary papers | **PASS** (adapted, not novel) |
| Arms / `plant_covariance` / within-donor ATAC shuffle | Present in `src/p22/eval/planted_signal.py` (`plant_covariance`, `shuffle_atac_within_donor`) and S7 runner/pairing path | **PASS** |
| S7-v2 null uses mean-fold while spec says pooled | Confirmed in C1 and `s7_screen.null_check`; independent review | **PASS** (diagnosis) |
| Reject CA-advantage remake on same covariance class | Consistent with N4 zero `CA_FAVOURED`, S7-v2 ρ=1 pooled CA−best = −0.071, CONTINUATION ban on outcome-guided remakes | **PASS** (rejection) |
| Select pairing-use S8 on same S7 generator | Question shift (pairing use ≠ advantage) is articulated; **null calibration is not** | See §2 — **FAIL for adoption** |

### 1.2 Lane C cohort / power numbers vs saved JSON

| Lane C claim | Live check | Verdict |
|---|---|---|
| 30 donors, 15 DS + 15 CON | `sampling_cap1000_seed22.json` primary: 30 donors; 15 `_DS_` / 15 `_CON_` | **MATCH** |
| 248998 / 30000 cells; H5AD sha256 `08d6eff…` | Same sampling artifact | **MATCH** |
| 37 libraries | Unique `library_available` keys = 37 | **MATCH** |
| PCW 10–20 uneven (PCW12/13=6) | Counts: PCW12=6, PCW13=6; span PCW10–20 | **MATCH** (Lane C table is illustrative, not exhaustive PCW histogram) |
| Primary CA−TC 0.0267, CI [−0.0250, 0.0768], `B_NULL` | Fresh C1 `verify_ladder` + `ladder_verification.json` | **MATCH** |
| `SPECTRUM_NULL`; 9 eligible / 6 excluded | `spectrum.json` | **MATCH** |
| `DOSAGE_DOMINATED`; faithfulness `CA_PAIRING_UNUSED`; PC `N/A` | `chr21_excluded.json`; `faithfulness.json` decision tags | **MATCH** |
| `POWER_UNESTABLISHED`; `min_detectable_delta=null` | `docs/nn_v2/v6/detectability.json` | **MATCH** |
| NeMO external BLOCKED (QC / specimen / feature) | Consistent with `PAIRED_DS_MULTIOME_DATASET_OPTIONS.md` / finish feasibility (metadata only; not re-acquired) | **ACCEPT as blocked** |
| Prefer bounded internal paper | Aligns with F4 and CONTINUATION path (a) | **ACCEPT** |

Minor note: Lane C lists PCW10/14/15 = 1 each; live counts also show other uneven PCWs (e.g. PCW16=2). Does not change the age–disease imbalance conclusion.

---

## 2. Critical assessment of Lane B S8 draft (must pass before any freeze)

### 2.1 What new question would S8 answer?

S8’s declared primary is **pairing use** of the existing CA implementation under the known S7 covariance plant (within-donor ATAC shuffle → donor log-loss drop), not CA−comparator advantage. That is a distinct estimand from S7’s advantage screen. It **cannot** count as independent replication of S7, and Lane B correctly forbids promoting `PAIRING_POSITIVE` to `A_ADVANTAGE`.

Reusing the same covariance generator after two `INVALID` S7 batches is therefore only justifiable if every gate—especially the ρ=0 null—is scientifically rewritten for the new estimand **without** outcome-guided threshold shopping. The draft does not clear that bar (§2.2).

### 2.2 Chance-band null calibration — **REJECT**

Lane B replaces `[0.35,0.65]` with a pre-fit central 95% band from **constant-0.5 and/or Bernoulli-0.5 predictors** on frozen fake labels (≥10k draws), then gates each of seven **fitted** arms’ pooled BA inside that band.

**Why this is not a valid null for the tested statistic:**

1. **Mechanism mismatch (CONTINUATION explicit).** The gate statistic is pooled donor BA of **fitted** models (neural + logreg) under a ρ=0 plant that still leaves residual background RNA/ATAC structure. Constant/Bernoulli predictors never fit, never share parameters across folds, and never exploit residual features. Their BA distribution does **not** match the tested fitted-model mechanism.

2. **Would pass the same S7-v2 ρ=0 outcomes that failed the frozen design check.** Illustrative Bernoulli-0.5 Monte Carlo on a 16/14 label vector (10k draws, seed 0) gives central 95% BA ≈ **[0.326, 0.674]**. Under that band, every S7-v2 ρ=0 pooled BA from C1 (including `token_concat` 0.330357 and `gated_fusion` 0.325893) falls **inside**. Adopting this band after seeing those failures is functionally an outcome-guided relaxation of the null that previously invalidated the batch—even if the draft never cites those numbers as the tuning target.

3. **Seven-arm joint gate ignored.** Draft gates “each arm” separately inside a marginal chance band. Under naive independence, P(all seven pass a 95% marginal band) ≈ 0.70; arms are in fact correlated (shared splits, labels, features). No joint / family-wise calibration is specified for the fixed 30-donor split.

4. **No alternative fitted-mechanism null is supplied.** CONTINUATION required: specify a null matching the tested statistic and fitted-model mechanism, **or reject S8**. No label-permutation-of-fitted-residuals, no ρ=0 parametric reference that includes training, and no justified fixed rule other than chance predictors was provided. Therefore **reject S8**.

5. **Invalid null cannot unlock method claims.** Even a later `PAIRING_POSITIVE` under a bad null would be uninterpretable: a passing pair shuffle must show within-cell pairing sensitivity while preserving donor ATAC marginals **and** resting on a valid screen. An invalid ρ=0 gate blocks that chain.

### 2.3 Other S8 design checks (secondary)

| Requirement | Draft state | Integrator call |
|---|---|---|
| Single primary statistic (donor ll-drop CI) | Stated | OK in isolation |
| One decision ρ; fixed seeds; fair arms/budgets | Stated (ρ=1; seeds 0/1001; 3001–3032) | OK in isolation |
| Pooled BA for gates; mean-fold descriptive | Stated prospectively | OK; does not repair S7-v2 |
| Shuffle preserves within-donor ATAC marginals | Matches `shuffle_atac_within_donor` | OK mechanistically |
| No `PAIRING_POSITIVE` → `A_ADVANTAGE` | Explicit | OK |
| Independent of S7 replication claim | Explicit | OK |
| **Null calibration** | Chance predictors | **FAIL — fatal** |

### 2.4 Interpretability of shuffle ± under this generator (if null had passed)

Under `plant_covariance` at ρ=1, within-donor ATAC shuffle destroys cell-level signed RNA↔ATAC covariance while preserving each donor’s ATAC row multiset and fake labels. A positive CA ll-drop would support only that **this implementation** used the constructed pairing on this plant/budget. A negative would support `PAIRING_NEGATIVE` for that pair only. Neither yields biology, transportability, or real-label advantage. This interpretability clause is **moot** because the null gate fails review.

---

## 3. Path comparison

| Path | Decision | Reason |
|---|---|---|
| **(a) Bounded internal null / detectability paper** | **CHOOSE** | Primary `B_NULL`; spectrum null; dosage-dominated; faithfulness pairing unused; S7-v1/v2 `INVALID`; power unestablished; framing F4 already chosen; keeps null paper viable without new fits |
| **(b) One prospective S8 pairing-use control** | **REJECT (NO FIT)** | Critical null-calibration gate fails (§2.2); cannot freeze or fit under CONTINUATION C2/C3 |
| **(c) External paired-cohort preflight/acquisition now** | **REJECT for this run** | Lane C: NeMO BLOCKED on QC gap, specimen independence, feature contract; CONTINUATION forbids new acquisition; remains later T13, not a fix for internal null |
| New real-label CA advantage on same 30 donors | **REJECT** | CONTINUATION + Lane C: between-model Δ̂ ≪ 0.07; `POWER_UNESTABLISHED`; not justified |

---

## 4. Integration gates I0–I5

| Gate | Result | Evidence |
|---|---|---|
| **I0 provenance** | **PASS** | Same base `808fa734`; C0/C1/C2 distinguish July MOM vs worker lanes; Lane B/C copied with SHAs; S7/ladder roots immutable |
| **I1 reproducibility** | **PASS** | C1 recomputed ladder CA−TC and S7-v2 pooled/mean-fold tables; mismatches have concrete causes; old labels retained |
| **I2 control design** | **FAIL** | No candidate with a non-circular, scientifically valid null for the fitted seven-arm pooled-BA gate; S8 chance band rejected; CA-advantage remake already rejected |
| **I3 design adequacy** | **PASS for chosen path** | Power explicitly `POWER_UNESTABLISHED`; no synthetic CI called biological power; S8 budget math is moot because I2 failed |
| **I4 biology** | **FAIL for mechanism/spectrum claims** | No adequate beyond-dosage / regulatory claim path on internal cohort; external blocked; **does not block** bounded null paper |
| **I5 independent review** | **N/A → stop** | No protocol freeze attempted; therefore no fit-authorization review. If S8 were revised later, I5 would be mandatory before any fit (`NO_FIT_REVIEW_PENDING` would apply until signed) |

**Critical-gate rule:** I2 **FAIL** ⇒ overall scientific decision **NO FIT** ⇒ do not mark review PASS by assertion; do not enter C3–C5.

---

## 5. Accepted and rejected claims

### Accepted (for the bounded paper / closeout)

- NN-v2 primary: verifier PASS, estimate 0.0267, CI includes 0 → advantage **not demonstrated** (`B_NULL`).
- S7-v1 and S7-v2 remain **`INVALID`** (immutable).
- N13 `CA_PAIRING_UNUSED` with PC `N/A`; N16 `SPECTRUM_NULL`; N11 `DOSAGE_DOMINATED`.
- Biological joint `A_ADVANTAGE` power: **`POWER_UNESTABLISHED`**.
- Study remains **`STUDY_PARTIAL`**; external validation deferred.
- Honest bounded internal detectability-limit / null paper (F4) is the justified writing path.

### Rejected / not authorized

- Freezing or fitting `S8_pairing_use_DRAFT_20260929`.
- Any claim that chance-predictor bands validate fitted-model ρ=0 screens.
- Relabeling S7 by switching mean-fold→pooled or widening null after outcomes.
- Real-label CA advantage refit on the same 30 donors.
- External NeMO acquisition or “external success” without cleared preflight.
- Promoting any synthetic pairing result (even hypothetical) to biological mechanism or `A_ADVANTAGE`.

---

## 6. Limits and remaining blockers (for C6)

1. **NO FIT on S8** until a future protocol (new ID) supplies a null that matches fitted pooled-BA under ρ=0 **and** accounts for seven-arm dependence without inspecting new fit outcomes — out of scope for this continuation’s fit authorization.
2. NeMO T13 blockers unchanged (QC 3731, specimen independence, feature contract).
3. No dated professor reply to the September 29 package in inspected records.
4. C3–C5 skipped by design after I2 FAIL; C6 must record this NO FIT truthfully and stop GNHF.

---

## 7. C2 acceptance self-check

| Required | Met? |
|---|---|
| Lane B taxonomy checked vs papers/code | Yes |
| Lane C numbers checked vs saved JSON | Yes |
| Null paper kept viable | Yes — path (a) |
| Decision among (a)/(b)/(c) with rejects | Yes |
| S8 chance calibration critically assessed | Yes — **rejected** |
| I0–I5 recorded PASS/FAIL/N/A | Yes |
| Critical fail → **NO FIT** + bounded-paper stop | Yes |
| No fits / no protocol freeze | Honored |

**Exact stop for C2:** scientific path closed at **NO FIT**; next continuation unit is **C6 HANDOFF only**.
