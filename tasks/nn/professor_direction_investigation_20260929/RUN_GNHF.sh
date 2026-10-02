#!/usr/bin/env bash
set -euo pipefail

plan_dir=/Users/anuragdani/Github/niw-eb1a/P22/tasks/nn/professor_direction_investigation_20260929
base=/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202
expected_base=808fa734a8dc2d89d34853204251bd9decea2a06

if [[ "$(git -C "$base" rev-parse HEAD)" != "$expected_base" ]]; then
  echo "Base commit changed. Review PLAN.md before launch." >&2
  exit 1
fi

case "${1:-}" in
  A|B|C)
    lane=$1
    cd "$base"
    exec gnhf --agent cursor --model auto --worktree \
      --max-iterations 20 --max-tokens 800000 --max-rate-limit-wait 1h \
      --meteor-frequency 0 \
      --stop-when 'Stop after the assigned lane report is committed with evidence, or after a precise blocker is recorded. Do not run model fits, acquire data, push, or merge.' \
      "$(cat "$plan_dir/LANE_${lane}_PROMPT.md")" \
      > "$plan_dir/LANE_${lane}.log" 2>&1
    ;;
  '')
    command -v tmux >/dev/null
    command -v gnhf >/dev/null
    for lane in A B C; do
      session="p22-investigation-${lane}"
      if tmux has-session -t "$session" 2>/dev/null; then
        echo "Session already exists: $session" >&2
        exit 1
      fi
    done
    for lane in A B C; do
      tmux new-session -d -s "p22-investigation-${lane}" -c "$base" \
        "$plan_dir/RUN_GNHF.sh $lane"
      echo "Started p22-investigation-${lane}: $plan_dir/LANE_${lane}.log"
    done
    ;;
  *)
    echo 'Usage: RUN_GNHF.sh [A|B|C]' >&2
    exit 2
    ;;
esac
