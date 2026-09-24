#!/usr/bin/env bash
set -eu
# Unattended batch driver for the P22-NN GNHF run.
#
# GNHF aborts after two consecutive failed iterations, so a single launch rarely
# carries N2-N23 to the end. This relaunches it until the status table has no TODO
# left, and keeps every attempt's output in a durable log (a discarded worktree
# takes gnhf.log with it; these logs live outside that).
#
# Usage: bash run_nn_batch.sh [max_attempts]   (default 12)
# Review after it finishes: git log, then reports/generated/nn_runs/<stamp>/.

WT="${P22_NN_WORKTREE:-/Users/anuragdani/Github/niw-eb1a/P22}"
MAX_ATTEMPTS="${1:-12}"
cd -- "$WT"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOGDIR="$WT/reports/generated/nn_runs/$STAMP"   # reports/generated is git-ignored
mkdir -p "$LOGDIR"

remaining() { grep -cE '^\|[[:space:]]*N[0-9]+[[:space:]]*\|.*\|[[:space:]]*TODO[[:space:]]*\|' tasks/nn/todo.md || true; }

printf 'batch start %s  attempts<=%s  remaining=%s\n' "$STAMP" "$MAX_ATTEMPTS" "$(remaining)" | tee "$LOGDIR/batch.log"

# Progress is measured in COMMITS, not in resolved tasks: with one step per
# iteration a big task stays TODO for several attempts while real work lands.
prev_commits="$(git rev-list --count HEAD)"
stalls=0
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  left="$(remaining)"
  if [ "$left" -eq 0 ]; then
    printf 'all tasks resolved; stopping after %s attempts\n' "$((attempt - 1))" | tee -a "$LOGDIR/batch.log"
    break
  fi
  if [ -n "$(git status --porcelain)" ]; then
    # Never auto-commit work this driver did not author; a dirty tree means the
    # last iteration died mid-edit and needs a human look.
    printf 'attempt %s aborted: worktree dirty, inspect before relaunching\n' "$attempt" | tee -a "$LOGDIR/batch.log"
    git status --short | tee -a "$LOGDIR/batch.log"
    exit 2
  fi

  printf '\n=== attempt %s/%s  remaining=%s  %s ===\n' \
    "$attempt" "$MAX_ATTEMPTS" "$left" "$(date -u +%H:%M:%SZ)" | tee -a "$LOGDIR/batch.log"
  rc=0
  bash gnhf/run_nn_cellstate.sh >"$LOGDIR/attempt_$attempt.log" 2>&1 || rc=$?
  printf 'attempt %s exit=%s remaining %s -> %s  commits=%s\n' \
    "$attempt" "$rc" "$left" "$(remaining)" "$(git rev-list --count HEAD)" | tee -a "$LOGDIR/batch.log"

  now_commits="$(git rev-list --count HEAD)"
  if [ "$now_commits" -le "$prev_commits" ]; then
    stalls=$((stalls + 1))
    # Three attempts that land no commit at all means every iteration is failing
    # and its work is being discarded; relaunching just burns tokens.
    if [ "$stalls" -ge 3 ]; then
      printf 'no commit across 3 attempts; stopping. see %s\n' "$LOGDIR" | tee -a "$LOGDIR/batch.log"
      exit 3
    fi
  else
    stalls=0
  fi
  prev_commits="$now_commits"
done

printf '\nbatch done. remaining=%s  head=%s\n' "$(remaining)" "$(git log --oneline -1)" | tee -a "$LOGDIR/batch.log"
