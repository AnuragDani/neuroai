# NULL_AUDIT — R2 null exchangeability and marginal diagnosis

**Disposition:** `NULL_AUDIT_PASS`
**Date:** 2026-10-01
**Generator-only draws this run:** 81 (cumulative 81 ≤ 256)
**Research / diagnostic fits:** 0 / 0
**Shared S9 raw unchanged:** `True`

## Seed schedule (committed before simulation)

```json
{
  "committed_before_simulation": true,
  "decision_generator_seed": 9001,
  "shuffle_seeds_reproduce_prior": [
    4001,
    4002,
    4003,
    4004,
    4005,
    4006,
    4007,
    4008,
    4009,
    4010,
    4011,
    4012,
    4013,
    4014,
    4015,
    4016
  ],
  "independent_gaussian_generator_seeds": [
    5101,
    5102,
    5103,
    5104,
    5105,
    5106,
    5107,
    5108,
    5109,
    5110,
    5111,
    5112,
    5113,
    5114,
    5115,
    5116,
    5117,
    5118,
    5119,
    5120,
    5121,
    5122,
    5123,
    5124,
    5125,
    5126,
    5127,
    5128,
    5129,
    5130,
    5131,
    5132,
    5133,
    5134,
    5135,
    5136,
    5137,
    5138,
    5139,
    5140,
    5141,
    5142,
    5143,
    5144,
    5145,
    5146,
    5147,
    5148,
    5149,
    5150,
    5151,
    5152,
    5153,
    5154,
    5155,
    5156,
    5157,
    5158,
    5159,
    5160,
    5161,
    5162,
    5163,
    5164
  ],
  "orthogonal_rho0_generator_seeds": [
    5201,
    5202,
    5203,
    5204,
    5205,
    5206,
    5207,
    5208,
    5209,
    5210,
    5211,
    5212,
    5213,
    5214,
    5215,
    5216
  ],
  "max_generator_array_draws": 256,
  "fit_attempts_allowed": 0
}
```

## 1. Reproduce exact-orthogonality / shuffle finding

- Original max |donor×channel product mean|: `1.734723475976807e-16`
- Shuffled mean |product mean| (seeds 4001–4016): `0.1465336998807442`
- Shuffled max |product mean|: `0.576881076114585`
- Matches prior NULL_INVARIANCE_DIAGNOSTIC: `True`

## 2. Exchangeability: what is preserved vs broken

**Pairing statistic tests:** Whether fitted predictions depend on within-donor cell pairing of RNA and ATAC rows (cell-pair exchangeability under the intervention).

**Mixture caveat:** If the generative null is not exchangeable under the same shuffle, a PAIRING_POSITIVE at ρ=0 can reflect broken exchangeability (exact orthogonality) rather than planted pairing or label leak.

### Preserved under within-donor ATAC shuffle

- Within-donor ATAC row multiset (exact marginals)
- Donor identity and labels
- RNA matrix unchanged
- Cross-donor isolation

### Broken

- Exact planted-channel orthogonality (z ⊥ w cell pairing)
- Any learned dependence on the original cell alignment

**Exchangeability verdict:** Under true conditional independence of RNA/ATAC given donor, within-donor ATAC permutation leaves the joint law invariant. The frozen ρ=0 construction places (z,w) on the measure-zero set {w⊥z}, which permutation leaves; therefore original and shuffled joints are not exchangeable under this generator.

**Implication:** Observed ρ=0 PAIRING_POSITIVE is consistent with a broken exchangeability null (models can exploit exact orthogonality that shuffle destroys). It does not by itself prove a neural leak of label information, nor does one positive 95% CI prove systematic error without a valid exchangeable reference.

## 3. Orthogonal vs independent-Gaussian panels

- Orthogonal ρ=0 panel (16 seeds): all original near machine zero = `True`; all shuffled far from zero = `True`
- Independent-Gaussian diagnostic panel (64 seeds): mean |product| original=`0.144887` shuffled=`0.144464` ratio=`1.0027` (near one = `True`)

## 4. Marginal BA uncertainty (saved ρ=1 predictions; no refit)

- logreg_rna pooled BA: `0.75`
- logreg_atac pooled BA: `0.7083333333333334`
- Gate threshold: `0.6` (INVALID retained; not overturned)

### Independent-draw chance reference (Hypergeometric, n=24 balanced)

- `P_BA_ge_0.5` = `0.657864`
- `P_BA_ge_0.6` = `0.110173`
- `P_BA_ge_0.7083333333333334` = `0.019563`
- `P_BA_ge_0.75` = `0.019563`

### Donor-cluster bootstrap of the fixed saved prediction vectors

- RNA BA bootstrap mean / 95% CI: `0.7497377797512086` / `[0.5625, 0.9166666666666666]`
- ATAC BA bootstrap mean / 95% CI: `0.7075237592000362` / `[0.5251917200446611, 0.8785714285714286]`

**Distinction:** Observed RNA BA=0.75 / ATAC≈0.708 can occur under chance for n=24 balanced donors with non-negligible probability; finite-sample nuisance association is plausible. This does not overturn INVALID (gate failed), nor prove a structural unimodal leak without a prospective chance-calibrated marginal rule.

## 5. Candidate null

**Status:** `CANDIDATE_DIAGNOSTIC_NULL`

- ID: `independent_gaussian_rho0_within_donor_shuffle_20261001`
- Statement: For a future software pairing-use control, generate planted channels as independent centre-scaled Gaussians at ρ_plant=0 (no exact orthogonalization). The fitted-mechanism null remains: within-donor ATAC shuffle must not yield PAIRING_POSITIVE for CA. Under this generator the product-mean statistic is approximately exchangeable under the same shuffle (ratio near 1 in the preregistered panel).
- Role: Diagnostic alternative generator for exchangeability — not a successful replacement of frozen S9 and not authorization to rerun S9.

Not authorized: S9 replacement, threshold retune, or research fits.

## Invariants

- Frozen S9 scientific label remains **`INVALID`**.
- Primary `B_NULL`; S7 `INVALID`; prior S8 `NO FIT`.
- Zero model fits in R2; no writes through shared S9 raw.

## Next

Checkpoint A (R1+R2); then independent R3/R4/R5 as scheduled.

