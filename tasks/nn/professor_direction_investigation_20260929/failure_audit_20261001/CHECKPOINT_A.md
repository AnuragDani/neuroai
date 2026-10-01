# Checkpoint A — after R1/R2

**Disposition:** `PASS`  
**Date:** 2026-10-01  
**Branch:** `gnhf/execute-p22-s-failur-d8f02c`

## Checks

| Requirement | Evidence | Status |
|---|---|---|
| Saved-result S9 replay independently checked | [S9_AUDIT.md](S9_AUDIT.md); 49/49; INVALID retained; shared raw unchanged | PASS |
| Null-contract / exchangeability reasoning checked | [NULL_AUDIT.md](NULL_AUDIT.md); 81 generator-only draws; 0 fits | PASS |
| Old INVALID not changed | Scientific label `INVALID` in both audits | PASS |
| Failures yield precise findings without redesigning old results | Exact orthogonality breaks shuffle exchangeability; candidate diagnostic null only | PASS |

## Continue

R3 (execution/RNG), R4 (guidance/claims), and R5 (task/data) may proceed independently after their prerequisites. No model fitting concurrent with protocol edits. No authorization to replace or rerun frozen S9 from this checkpoint alone.
