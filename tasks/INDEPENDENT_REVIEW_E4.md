# E4 — Independent full-path no-fit review (execution repair)

**Reviewer identity:** Antigravity CLI (`agy`) Gemini 3.1 Pro — independent of E0–E3 authoring / Checkpoint A–B handoff writer  
**Conversation IDs:** primary review `a225d6ef-c027-4e11-9e1c-44412e5455fd`; provenance addendum `0a78e893-964f-4c54-9e50-d8a256e56942`  
**Date:** 2026-10-02  
**Scope:** execution-repair E4 independent no-fit review of the committed complete real-data execution path  
**Reviewed commit:** `3eb7f74279d5f27bfee1dc0d7c59a9a8996b8aed`  
**Correction cycle:** 0 of max 2 (addendum completed the 17th lock key without source change)  
**Self-certification:** false  

Worker self-assertion was not used for the scientific path audit. This record accepts the external AGy PASS only after recomputing live SHA-256 for all 17 immutable lock keys against `configs/execution_repair_full_executor_lock_2026-10-02.json` and `live_hashes.txt`, confirming HEAD equals the reviewed commit, and re-running the E0–E3+M9 integration refusal suite (**24 PASS**, exit 0). No research fits. Reviewed execution source was not modified.

Machine record: [NO_FIT_REVIEW_E4.json](NO_FIT_REVIEW_E4.json). External lock rematch: [E4_REVIEWED_HASHES.json](E4_REVIEWED_HASHES.json). Raw transcript + live hashes preserved: [execution_repair_e4/AGY_REVIEW.txt](execution_repair_e4/AGY_REVIEW.txt), [execution_repair_e4/live_hashes.txt](execution_repair_e4/live_hashes.txt) (copies of ignored `reports/generated/execution_repair_20261002/` originals; SHA-256 identical).

---

## Overall verdict

**PASS**

Exact commit `3eb7f74279d5f27bfee1dc0d7c59a9a8996b8aed` matches HEAD. All **17/17** immutable full-executor lock digests rematch live working-tree files and preserved `live_hashes.txt`. Integration refusal suite **24 PASS**. Historical M9 remains **NOT_AUTHORIZED**; primary **B_NULL**; prior S10/S9/S7 **INVALID**; S8 **NO FIT**; `scientific_fits_authorized=false`. This review does **not** authorize research fits, mark Checkpoint C, or decide E5 GO/NO_GO. Any reviewed-path source change invalidates approval.

---

## Addendum (provenance key)

Primary AGy narrative listed 16 path bullets and omitted naming `src/p22/eval/execution_repair_provenance.py` in the hash bullet list even though the lock and live rematch include it. Separate addendum conversation inspected that module and its `resolve_portable_path` / `default_atac_path` callers in `masked_atac_pilot.py`, confirmed digest `975a21850cdc53b5a6a1a20ade2deab1d0545d56ff4b33df637a6f82a8c8ec59`, and restated complete **17-file PASS**. No source edits.

---

## Exact hashes recomputed (SHA-256)

| Path | Recomputed SHA-256 |
|---|---|
| `scripts/run_masked_atac_m9.py` | `f31374774d609c7ac62ebfbdffb5f0e506590d6654cdb81f44711b23b565c281` |
| `src/p22/eval/masked_atac_pilot.py` | `41105254cb56c304ba98ffafdc968e78b1455af843ffa1cf924f8be4189c42a0` |
| `src/p22/eval/execution_repair_authorization.py` | `19329f4ad116f547f0d6f8c894bb8884fa0a39372c165dbd0abbe4b668691b4f` |
| `src/p22/eval/execution_repair_provenance.py` | `975a21850cdc53b5a6a1a20ade2deab1d0545d56ff4b33df637a6f82a8c8ec59` |
| `src/p22/eval/execution_repair_runtime_mask.py` | `f9939ffae2a963c3b2230181c784bcf19ad53cfb4749cf55fe9eff48797ee114` |
| `src/p22/eval/execution_repair_checkpoint.py` | `7c32784d7811caa1b0c8835c2149da7f96c65a9874952b6b342cd10f78b9a4fb` |
| `src/p22/eval/masked_atac_execute.py` | `a9798c008689489ac913563a978726e2011a3e10cdb08f77d42df954a93987aa` |
| `src/p22/eval/masked_atac_adapter.py` | `cda024a4e0812c7ba76cb435b6e4cfd66de2879d408413f4a6a2d5f19068aae6` |
| `src/p22/eval/masked_atac_protocol.py` | `1ad3fdb97a470573254569195e712a7376ce1f1e581722c7aa3eb5939d22fb5d` |
| `src/p22/eval/masked_atac_metrics.py` | `64553c501ac3a0619d97fcdc547d7fb98a96555ab3d3f8ccea9cee2fc019a9c5` |
| `src/p22/eval/masked_atac_splits.py` | `9c54324234cd3cffd5f622604bda00aee966b1147e205179b83cf182f1e8f415` |
| `src/p22/eval/masked_atac_target.py` | `c771f1069a9a6d40c3107efd65131f762af4285799eb01ef07e395b555d0cd02` |
| `src/p22/eval/multiome_runner.py` | `119f93e269eee11a27b93e29f1c85a192b25793d9fad28e546bba99c93abd0b5` |
| `src/p22/eval/s7_runner.py` | `290b5e2769629d139691be52c2be292bc03c5af986c3c33bf8a1feefe8d84790` |
| `src/p22/training/loop.py` | `195274bf29284e17746bef20020394737d175666361c5537fb0cdac1df347c1a` |
| `src/p22/training/mil_loop.py` | `6956d20037f81205f86302940005cbc17659ad40497bf3117d76fd7bb8d428e0` |
| `src/p22/data/transforms.py` | `16cb590ec6943a98b8a1363bbc42c31f250d8cb913ff9f91c6e28e84a453488a` |

Lock file SHA-256 (unchanged): `6a7dee7e1253478034db145f2269b4c209232a7fd206e9e6363c9deab83ce571`.  
Preserved `live_hashes.txt` SHA-256: `f845b9e8ca5cd2548b29d5c7b0893855cd22a4803d9157db7181a7578b605d0c`.  
Raw `AGY_REVIEW.txt` SHA-256: `cfa48c0600d1f0c47ba7e727bcff59a91086b2737ef3431436870de287022545`.

Mutable attempt counter remains excluded (used=30; SHA `2b4bd43c81460a7945bd5374ab2822d6bbf3440031f00639313387170857112a`).

---

## Checklist (plan E4)

1. **Separate reviewer traced data-to-result path — PASS.** AGy inspected chromosome exclusion, training-only transforms, donor metrics, checkpoints, reload identity, interrupted writes, resume counters, full-source hash authorization, artifact accounting.
2. **Exact reviewed hashes recorded — PASS.** 17/17 immutable keys; addendum covers provenance module.
3. **Replay reviewer lock against committed source — PASS.** Live rematch + HEAD == reviewed commit.
4. **Refusal tests — PASS.** Integration suite 24 passed, exit 0.
5. **No self-certification — PASS.** Verdict from AGy; this file only rematches and records.
6. **Historical scientific labels unchanged — PASS.** M9 NOT_AUTHORIZED; B_NULL; INVALID / NO FIT retained; `scientific_fits_authorized=false`.
7. **Zero research fits — PASS.**

---

## Evidence commands (worker rematch)

```bash
git rev-parse HEAD   # 3eb7f74279d5f27bfee1dc0d7c59a9a8996b8aed
# recompute SHA-256 of all 17 lock paths; compare to lock + live_hashes.txt
PYTHONPATH=src .venv-p22/bin/python -m pytest \
  tests/test_execution_repair_provenance_e0.py \
  tests/test_execution_repair_runtime_mask_e1.py \
  tests/test_execution_repair_checkpoint_e2.py \
  tests/test_execution_repair_authorization_e3.py \
  tests/test_masked_atac_pilot_m9.py -q
```

Exit 0; **24 passed**.

---

## What this does / does not authorize

**Authorizes:** Recording E4 `PASS` on exact commit + 17 hashes; E5 decision work may proceed under a separately scoped future pilot proposal (decision only).

**Does not authorize:** Research fits; scientific re-acceptance of M9; Checkpoint C closeout; E5 GO as fit dispatch; counter resets; downloads; push; professor messages; changes to reviewed execution source.
