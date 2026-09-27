# P22 current status

Updated: 2026-09-27 15:23 PDT. Read this first, then [document index](docs/INDEX.md). This is a snapshot, not permission to run an experiment or change a scientific gate. For live work, recheck the linked status and verifier files before acting.

Companion research vault: [vault status](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/status.md>) and [vault MOM index](<../../../Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P22/MOM/README.md>).

## Current work: NN v2

| Item | State | Evidence |
|---|---|---|
| Professor guidance | About 60% implemented, ~45% supported by completed evidence. Spectrum now `SPECTRUM_NULL`. These are task-based estimates, not scientific metrics. | [Direction-to-task map](tasks/nn/plan.md#1-what-the-professor-asked-and-how-this-plan-answers-it), [July meeting records](MOM/README.md) |
| Main real-data ladder | 450/450 expected fold outputs produced. Training run complete; **S6 gate accepted**. | [Run record](reports/generated/nn_20260923/ladder_v2/run.json), [verifier](docs/nn_v2/ladder_verification.json) |
| Ladder gate | **PASS**. Outcome `B_NULL`: primary R3_ca−R3_tc estimate −0.0067, CI includes 0 (summary ≈ [−0.0533, 0.0348]; verifier recomputed ≈ [−0.0528, 0.0348]). No complex-model superiority claim. Model-free chr21 dosage AUROC ≈ 0.998; majority pooled-BA caveat remains. | [Saved summary](docs/nn_v2/ladder_summary.json), [verifier](docs/nn_v2/ladder_verification.json), [LADDER.md](docs/nn_v2/LADDER.md) |
| Downstream NN work | **N11** `DOSAGE_DOMINATED`; **N12** `SPREAD_ONLY`; **N13** accepted (`CA_PAIRING_UNUSED`, `ATAC_USED`; NC exact zero; PC N/A); **N14** `R2_REJECTED` (`PROBE_DROP_INSUFFICIENT`); **N15** OOF cell scores (120k); **N16** `SPECTRUM_NULL` on ladder_v2 R3_ca (9 eligible). N17/N21 and paper stages remain. | [chr21_excluded.json](docs/nn_v2/chr21_excluded.json), [seed_sensitivity.json](docs/nn_v2/seed_sensitivity.json), [faithfulness.json](docs/nn_v2/faithfulness.json), [nuisance_probe.json](docs/nn_v2/nuisance_probe.json), [cell_scores_export.json](docs/nn_v2/cell_scores_export.json), [spectrum.json](docs/nn_v2/spectrum.json), [SPECTRUM.md](docs/nn_v2/SPECTRUM.md), [Main task status](tasks/nn/todo.md) |
| Paper | [Draft](paper/draft.md) still says real-data ladder never ran; rewrite after remaining S7–S8. `paper/check_paper.py` currently fails number/claims checks. | [Draft](paper/draft.md), [paper task list](tasks/nn/todo.md) |
| Old swarm | `p22agy4` kept hitting Gemini quota limits. Stopped at 13:44 PDT; tmux session and Python driver no longer running. Saved lane branches/outputs remain for verification. | [Swarm log](reports/generated/nn_agy/latest/swarm.log), [lane status](reports/generated/nn_agy/latest/status.json) |
| Manual GNHF finish | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md) active on `codex/p22-nn-finish-base`. S6 done; S7 N11–N15 accepted; S8 N16 `SPECTRUM_NULL`; next N17/N21 then N22–N23. | [Runbook](tasks/nn/GNHF_FINISH_RUNBOOK.md), [saved gate](docs/nn_v2/ladder_verification.json) |

**Resolved conflict:** N10 task label previously said DONE while the S6 hard gate said FAIL. Gate now `PASS` with rebuilt summary from all 450 fold files; N10 scientific result accepted as `B_NULL`.

## Other study tracks

- Earlier paired multiome study: corrected internal comparison is an accepted null within its own protocol; external paired validation remains unperformed. It is **not** the NN-v2 ladder. See [corrected handoff](MOM/2026-09-21/GNHF_P22_CORRECTED_RESULTS_AND_HANDOFF.md).
- Professor meeting records stay in [MOM](MOM/README.md), separate from plans and experiment outputs. June and July transcripts live in the linked Obsidian vault; September execution handoffs live here.
- Historical July [HANDOFF.md](HANDOFF.md) and September [session handoff](docs/P22_SESSION_HANDOFF_2026-09-23.md) are dated snapshots, not current status.

## Next verified milestones

1. Finish remaining S7 optional N21 (geneact results empty; run or BLOCKED) and S8 N17.
2. Complete N22–N23 and S9 paper from verified numbers; pass paper checker and evidence gate before vault copy.

## Status maintenance

Update this file after an accepted gate, material blocker, or final result. Include date, direct evidence links, and any disagreement between task labels and checks. Avoid updates for every quota retry. For scientific claims, verified raw evidence and gates outrank task labels; task labels outrank narrative handoffs.
