# P22 interrupted-run recovery — 21 September 2026

The Mac booted at 16:44:32 PDT. No GNHF/OpenCode or experiment process was found
in this results worktree during the recovery check. The last run started at
14:06:10 PDT; it committed iteration 3 at 14:22:53 and was interrupted during
iteration 4. The old end-state.json from 14:01 predates that restart and does
not describe the interrupted attempt. Reboot is observed; its cause is unknown.

Saved ATAC repair commit: `24297c860ecc6f5f45c13ddec7945a06a512edcd`.
This checkpoint preserves five interrupted RNA edits exactly as found. It is a
WIP preservation commit, not a validated repair or new experimental result.
No tests or scientific runs were executed to approve these partial edits.

Before resuming implementation, inspect this checkpoint's diff and finish the
RNA repair. In particular:

- Verify the raw axis reader rejects absent, malformed or mismatched identifiers;
  dimension equality and an empty gene-ID hash are not acceptance evidence.
- Trace every caller affected by changing load_cell_matrix's default. Preserve
  explicitly processed workflows where intended; fix the paired input path.
- Review the changes to configs/rna_donor_influence.json and the CONFIG_SHA256 pin
  in src/p22/eval/rna_donor_influence.py. These are unvalidated edits left by the
  interrupted worker. Do not rerun or alter the completed RNA donor-influence
  diagnostic. A necessary code-provenance amendment must preserve historical
  results and must not claim a new successful replay without executing one.
- Run the new regression tests and applicable required checks before calling the
  RNA repair complete. Continue acceptance validation, corrected matrix generation,
  comparison/interventions and notebook work from the existing repair prompt.

An external copy of all five pre-checkpoint files, their hashes and a binary Git
patch was saved at:

`/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/gnhf_crash_recovery_20260921T170747`

Resume using the unchanged saved prompt at
`.gnhf/runs/p22-correct-the-meas-69ea60/prompt.md` and `--current-branch` in this
worktree. GNHF should resume after logged iteration 3; an iteration number does
not imply that the interrupted fourth iteration was completed. Do not reset,
discard the checkpoint, overwrite prior results, or start another copy.
