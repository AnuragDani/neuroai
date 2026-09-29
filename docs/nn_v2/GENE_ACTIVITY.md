# Gene-activity secondary ladder (N21)

Outcome: **GA_B_NULL** (secondary only; primary remains N10 `B_NULL`).
Primary GA_ca−GA_tc estimate 0.0533, CI [-0.0527, 0.1572].

Never claim this as independent external validation.

| Arm | mean BA | n folds |
|---|---|---|
| GA_ca | 0.5200 | 25 |
| GA_tc | 0.4667 | 25 |
| R3_ca | 0.4733 | 25 |
| R3_tc | 0.4133 | 25 |
| logreg_concat | 0.6200 | 25 |

Run directory: `/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/nn_20260923/gene_activity_v2`
Token selection: top 500 / 548 by label-free dispersion_z.
Source hashes: counts `8cce7bd7c5e424c430db11101501417770886936dc58d34c270b388ead633deb`, bed `946fd00023079d5f39ac8cb14d77a74ac25ec1167a1b24adc45f40ffb3635282`.

## Faithfulness on GA_ca (I1/I3/I4)

Tags: GA_ATAC_UNUSED_OR_NULL, GA_CA_PAIRING_UNUSED, GA_ATTENTION_NOT_SHOWN_USED. NC exact zero on all 25 folds.
Secondary only; does not alter primary N13 tags.

- I1 Δlogloss=0.0000 CI [-0.0000, 0.0000]
- I3 Δlogloss=-0.0000 CI [-0.0000, 0.0000]
- I4 Δlogloss=0.0000 CI [-0.0000, 0.0000]

