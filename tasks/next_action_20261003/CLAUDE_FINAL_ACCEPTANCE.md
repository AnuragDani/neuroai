# FINAL_REVIEW — P22 final narrowed PLAN.md

**Reviewer:** claude · **Date:** 2026-10-03 · **Verdict:** PASS_WITH_CHANGES · **Blockers:** none

## Numerical verification against supplied leaves

Every pinned number reproduces. `ladder_verification.json`: CA−TC `+0.026666…`, CI `[-0.0250, +0.07679]`, margin `0.07`, `advantage: false`; R3_ca 0.4000/0.3582, R3_tc 0.3733/0.3316, R4_ca 0.5267/0.5147, R4_tc 0.5000/0.4427, pseudobulk 0.5133/0.5573, chr21_dosage 1.0/1.0; majority BA and AUROC both 0.300 with the fold-wise-threshold note. Labels match sources: E5 `NO_GO`, M9 `NOT_AUTHORIZED`, M10 diagnostic, S7/S9/S10 `INVALID`, S8 `NO FIT`, Q2 `ENDPOINT_UNRESOLVED`, `POWER_UNESTABLISHED`, primary `B_NULL`. Task 3 facts match `external_feasibility.json`: 1,540,753,269 bytes, MD5 pinned, payload not downloaded, QC 117,532 vs 113,801 (3,731 `class!='Unk'`, QC unreproduced), empty donor-ID overlap as no-overlap evidence only, PCW 13–20 at 8 control / 10 Ts21.

The peak-interval argument is scientifically sound: study-specific peak calling means a MEX matrix on different intervals cannot reconstitute counts on the fixed 465-region union without identical interval/count semantics or fragment-level data. Refusing to zero-fill unmeasured regions is correct. The 0.0625 / 0.05 per-flip BA arithmetic is right for 8/10 per-class recalls, and the plan correctly declines to call it power or impossibility.

## Material changes required

1. **Primary estimate is arm-ambiguous.** Both R3 (0.4000−0.3733) and R4 (0.5267−0.5000) equal +0.02667. Name the rung and record ID carrying the primary contrast; absolute level differs (0.40 vs 0.53) and the paper's limits claim depends on which.
2. **Concat baseline omitted.** G7 makes concatenation a required comparator, and `logreg_concat` (BA 0.4133, AUROC 0.3822) exists in the same leaf but is absent from the accepted table that does report CA arms. Include it.
3. **256 MiB ceiling uncited.** The supplied Q5 record declares only 64 MiB / 10 requests. Cite the ledger leaf or mark the figure unverified here.

Minor: report `parameter_count` beside BA/AUROC — R4 arms are ~30k parameters versus ~384k at R3, so "absolute performance" otherwise reads as capacity-confounded.

Chance-level results are not evidence of absent signal; the plan's wording on this is correct and retained.
