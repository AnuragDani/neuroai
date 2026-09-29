# S7-v2 T10 — Final handoff → `INVALID` (complete)

Date: 2026-09-29. Depends on T6–T8 COMPLETE; T9 skipped. Machine audit: [T10_HANDOFF_AUDIT.json](T10_HANDOFF_AUDIT.json). Versioned result: [S7_V2_RESULT.md](S7_V2_RESULT.md) / [S7_V2_RESULT.json](S7_V2_RESULT.json).

## Command

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  /Users/anuragdani/Github/niw-eb1a/P22/.venv-p22/bin/python \
  scripts/run_nn_s7_covariance.py --split-v2 --once
```

CLI action `write_handoff`, `done=true`, reason `screen/PC not eligible; skip confirmation and write handoff`. Pipeline also wrote [S7_RESULT.md](S7_RESULT.md) (writer default basename; top-level `protocol_id` defaulted to v1 string — corrected in versioned `S7_V2_RESULT.*`).

## Independent verification

| Check | Result |
|---|---|
| Ledger rows | **119** (smoke 14 + screen 105); all `status=ok`; sha256 `53920364…` |
| Re-evaluate screen | `screen_label=INVALID` (rho-0 null FAIL: `token_concat` 0.341667) |
| Pairing PC | `pc_label=PC_FAIL` (ll-drop CI lower ≤ 0; 0 new fits) |
| Finalize | **`INVALID`** (screen INVALID → design failure; T9 `CONFIRM_SKIPPED`) |
| Budget | 119 ≤ 469 planned and ≤ 480 absolute; remaining 361 |
| Provenance freeze | file sha256 `52cde0ba…` matches Checkpoint B |
| V1 immutable | ledger `5e23387a…`, provenance `d9e941d2…`, result md/json unchanged |
| Resources | free 26.617 GiB; artifacts 0.016 GiB; under caps |
| Biological boundary | `B_NULL` / `POWER_UNESTABLISHED` / `STUDY_PARTIAL`; no real-label fits |

## Checkpoint C / D

- **C:** Scientific label `INVALID` from raw coverage + gates. Not `CA_FAVOURED_CONTROL`. No biological `A_ADVANTAGE`.
- **D:** Truthful handoff complete; T9 skipped; no new jobs pending under frozen rules. GNHF stop condition met.

## Gate decision

**COMPLETE — T10 handoff done with scientific `INVALID`.** Split repair made the screen scoreable, but the fixed rho-0 null control failed and pairing-PC was insensitive. Confirmation correctly skipped. Old S7-v1 remains immutable `INVALID`. Stop.
