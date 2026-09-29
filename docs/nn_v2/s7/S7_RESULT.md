# S7 prospective synthetic control — result

**Scientific label:** `INVALID`
**Reason:** INVALID: frozen split_seed=0 + prospective-s7:1001 yields single-class fold-0 test (6/6 fake-label 0). Smoke recorded 14/14 single_class; screen cannot complete (fold 0 unscorable). Live check: plant_covariance matches full-cohort fake labels (0 mismatches); prior fold-subset recomputation diagnosis withdrawn. Runbook: split classes invalid → stop with blocker. No seed/setting retune. Biological primary remains B_NULL; POWER_UNESTABLISHED; STUDY_PARTIAL.
**Biological power:** `POWER_UNESTABLISHED`
**Finished primary:** `B_NULL`
**Study:** `STUDY_PARTIAL`

This batch is a prospective semisynthetic control only. It does not change the finished biological primary (`B_NULL`) and does not establish biological power or transportability.

## Protocol and provenance

- Protocol ID: `S7_covariance_20260929`
- Spec SHA256: `66225413f1cf7d5dae4f2a87af888deecce6124e4ea1514d2636d0d27b527ab1`
- Provenance fingerprint: `ad86357626740ab54a53fbf863439131c33389683a6922af0c304ee2903cfc97`
- Source hashes: `{"loop.py": "195274bf29284e17746bef20020394737d175666361c5537fb0cdac1df347c1a", "multiome_runner.py": "119f93e269eee11a27b93e29f1c85a192b25793d9fad28e546bba99c93abd0b5", "planted_signal.py": "a3a6a7f3e5e5550038a38d9e5bff15abd09486d6b238f23c0bfa182cef8e3a5e", "s7_confirm_exec.py": "45e15aa402739cd18aa6bda3c1cfbfc4680714a9763047b0be2d0cb57bb85dde", "s7_confirmation.py": "0167290a59a4f7e0a44fedc072cc64a40555e987884648c2e399303ae55ae073", "s7_handoff.py": "16d9240648d3ba5bf7b8f64845105d7f7b798d1835d0758bb71445f4213393ac", "s7_ledger.py": "e018cd03d5ea9353a10f71afd8b636576f4e0a50207b84d5624a8890a93467f7", "s7_pairing.py": "6475afd4d3d9e21ded6ce73b61e629a21ab10b8a11977cb2b56ed83652cef61e", "s7_pairing_exec.py": "75cfefc6ad0c673540c7c9676f07fa161a8ea1d97f29009b5fa2206effdc3e1b", "s7_pipeline.py": "72e701d04d9ab0ad8fc6b7a6692732cb77fbec2a12f66d052e77122c1f6d2dad", "s7_runner.py": "b86a495a66771b8b736dbd4aba61d12b2b603d73a6138f406e24e37b4679d6e9", "s7_screen.py": "96c829566877b64faba284b087253f34a8d0b91af858c2c498d24c71e8a78cb3", "s7_setup.py": "d0b5df45b17335e48116df2f38df8f92f1cddc02de4755b10fb94cd9ddb21177"}`
- Input hashes: `{"atac_tiebreak_counts": "5f13c089c0b598c45323d0afc874f96bdf7d4074307c3c01dc40129862d9f969", "h5ad": "08d6eff265db6e6a2e1c4a259153588f3dba3c51f5f754736dc63c28795fcdbb", "nn_inputs_config": "45d9b540d2a1c906879867003a488e7a54a9e4818a82f776b91643f77ae9f766", "region_sets_sha256_json": "13f630a6777a059db4ac1b5f17b397976030e0b0e29193e2bc09eab24dc46407", "tracked_union_bed": "d20d437ac96401746c20ff3645c464bc668ac7ed942bfb709a5bc667ef26bc23"}`

## Stage outcomes

- Screen: `INCOMPLETE`
- Pairing PC: `None`
- Confirmation: `CONFIRM_SKIPPED`

### Screen

```json
{
  "blocker": {
    "biological_power": "POWER_UNESTABLISHED",
    "biological_primary_unchanged": "B_NULL",
    "corrected_root_cause": "Outer StratifiedGroupKFold under frozen split_seed=0 with prospective-s7:1001 fake labels (16 vs 14 donor balance) assigns all six fold-0 test donors fake label 0. Smoke is fold-0-only, so all 14 smoke fits are single_class. Screen fold 0 would also be unscorable.",
    "diagnosis_revision": "iteration_16",
    "donor_level_fake_balance": {
      "0": 16,
      "1": 14
    },
    "fold0_test_donors": [
      "PCW11_CON_17833",
      "PCW12_CON_14427",
      "PCW13_CON_15044",
      "PCW13_DS_16427",
      "PCW17_CON_14559",
      "PCW20_CON_15167"
    ],
    "fold0_test_fake_label_classes": {
      "0": 6
    },
    "fold_test_class_counts_seed_1001": {
      "0": {
        "0": 6
      },
      "1": {
        "0": 2,
        "1": 4
      },
      "2": {
        "0": 2,
        "1": 4
      },
      "3": {
        "0": 3,
        "1": 3
      },
      "4": {
        "0": 3,
        "1": 3
      }
    },
    "n_smoke_fits": 14,
    "plant_vs_full_cohort_mismatches": 0,
    "prior_diagnosis_withdrawn": "plant_covariance fold-subset fake-label recomputation (smoke_stage_evidence.json root_cause)",
    "retune_forbidden": true,
    "runbook_rule": "If split classes invalid, stop with blocker",
    "scientific_label": "INVALID",
    "smoke_ledger_statuses": {
      "single_class": 14
    },
    "study": "STUDY_PARTIAL"
  },
  "coverage": {
    "complete": false,
    "missing": [
      {
        "fold": 0,
        "model": "cross_attention",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "token_concat",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "rna_atac_concat",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "gated_fusion",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "logreg_concat",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "logreg_rna",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "logreg_atac",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "cross_attention",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "token_concat",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "rna_atac_concat",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "gated_fusion",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "logreg_concat",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "logreg_rna",
        "rho": 0.0
      },
      {
        "fold": 1,
        "model": "logreg_atac",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "cross_attention",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "token_concat",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "rna_atac_concat",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "gated_fusion",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "logreg_concat",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "logreg_rna",
        "rho": 0.0
      },
      {
        "fold": 2,
        "model": "logreg_atac",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "cross_attention",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "token_concat",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "rna_atac_concat",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "gated_fusion",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "logreg_concat",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "logreg_rna",
        "rho": 0.0
      },
      {
        "fold": 3,
        "model": "logreg_atac",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "cross_attention",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "token_concat",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "rna_atac_concat",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "gated_fusion",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "logreg_concat",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "logreg_rna",
        "rho": 0.0
      },
      {
        "fold": 4,
        "model": "logreg_atac",
        "rho": 0.0
      },
      {
        "fold": 0,
        "model": "cross_attention",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "token_concat",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "rna_atac_concat",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "gated_fusion",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "logreg_concat",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "logreg_rna",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "logreg_atac",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "cross_attention",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "token_concat",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "rna_atac_concat",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "gated_fusion",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "logreg_concat",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "logreg_rna",
        "rho": 0.5
      },
      {
        "fold": 1,
        "model": "logreg_atac",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "cross_attention",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "token_concat",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "rna_atac_concat",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "gated_fusion",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "logreg_concat",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "logreg_rna",
        "rho": 0.5
      },
      {
        "fold": 2,
        "model": "logreg_atac",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "cross_attention",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "token_concat",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "rna_atac_concat",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "gated_fusion",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "logreg_concat",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "logreg_rna",
        "rho": 0.5
      },
      {
        "fold": 3,
        "model": "logreg_atac",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "cross_attention",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "token_concat",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "rna_atac_concat",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "gated_fusion",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "logreg_concat",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "logreg_rna",
        "rho": 0.5
      },
      {
        "fold": 4,
        "model": "logreg_atac",
        "rho": 0.5
      },
      {
        "fold": 0,
        "model": "cross_attention",
        "rho": 1.0
      },
      {
        "fold": 0,
        "model": "token_concat",
        "rho": 1.0
      },
      {
        "fold": 0,
        "model": "rna_atac_concat",
        "rho": 1.0
      },
      {
        "fold": 0,
        "model": "gated_fusion",
        "rho": 1.0
      },
      {
        "fold": 0,
        "model": "logreg_concat",
        "rho": 1.0
      },
      {
        "fold": 0,
        "model": "logreg_rna",
        "rho": 1.0
      },
      {
        "fold": 0,
        "model": "logreg_atac",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "cross_attention",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "token_concat",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "rna_atac_concat",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "gated_fusion",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "logreg_concat",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "logreg_rna",
        "rho": 1.0
      },
      {
        "fold": 1,
        "model": "logreg_atac",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "cross_attention",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "token_concat",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "rna_atac_concat",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "gated_fusion",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "logreg_concat",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "logreg_rna",
        "rho": 1.0
      },
      {
        "fold": 2,
        "model": "logreg_atac",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "cross_attention",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "token_concat",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "rna_atac_concat",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "gated_fusion",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "logreg_concat",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "logreg_rna",
        "rho": 1.0
      },
      {
        "fold": 3,
        "model": "logreg_atac",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "cross_attention",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "token_concat",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "rna_atac_concat",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "gated_fusion",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "logreg_concat",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "logreg_rna",
        "rho": 1.0
      },
      {
        "fold": 4,
        "model": "logreg_atac",
        "rho": 1.0
      }
    ],
    "n_expected": 105,
    "n_ok": 0
  },
  "eligible_for_pairing_pc": false,
  "marginal_check": null,
  "null_check": null,
  "rho1_regime": null,
  "screen_label": "INCOMPLETE"
}
```

### Pairing PC

```json
{}
```

### Confirmation

```json
{
  "all_baseline_successes": null,
  "all_baseline_wilson": null,
  "ca_tc_successes": null,
  "ca_tc_wilson": null,
  "confirm_label": "CONFIRM_SKIPPED",
  "reason": "screen/pairing not eligible; confirmation not run",
  "trials": []
}
```

## Resources

```json
{
  "artifacts_gib": 0.003,
  "free_gib": 28.357,
  "max_artifacts_gib": 2.0,
  "min_free_gib": 11.0,
  "ok": true
}
```

## Artifact paths

- Ledger: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/ledger/fit_ledger.jsonl`
- Checkpoints: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_s7_covariance_20260929/checkpoints`

## Claims boundary

- Biological advantage claimed: no
- Canonical scientific JSON/gates edited: no
- Real-disease-label fits: no
