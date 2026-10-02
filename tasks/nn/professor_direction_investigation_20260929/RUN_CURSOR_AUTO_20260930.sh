#!/usr/bin/env bash
set -euo pipefail

task_dir=/Users/anuragdani/Github/niw-eb1a/P22/tasks/nn/professor_direction_investigation_20260929
base=/Users/anuragdani/Github/niw-eb1a/P22/.worktrees/finish-engineering-20260928-gnhf-worktrees/read-tasks-nn-finish-ee2202
expected_base=808fa734a8dc2d89d34853204251bd9decea2a06
session=p22-investigation-continuation

[[ "$(git -C "$base" rev-parse HEAD)" == "$expected_base" ]] || { echo 'Base commit changed; review runbook.' >&2; exit 1; }
git -C "$base" cat-file -e '4d0c3b9^{commit}'
git -C "$base" cat-file -e '010a07f^{commit}'
command -v gnhf >/dev/null
command -v tmux >/dev/null
if tmux has-session -t "$session" 2>/dev/null; then
  if [[ -t 0 && -t 1 ]]; then
    exec tmux attach -t "$session"
  fi
  echo "Session already exists: $session"
  exit 0
fi

log="$task_dir/CURSOR_AUTO_20260930.log"
: > "$log"
tmux new-session -d -s "$session" -c "$base" \
  "sleep 1; exec gnhf --agent cursor --model auto --worktree --max-iterations 45 --max-tokens 1600000 --max-rate-limit-wait 2h --prevent-sleep on --meteor-frequency 0 --stop-when 'Stop after C0-C6 truthful handoff, including NO FIT, INVALID, INCOMPLETE, PAIRING_NEGATIVE or PAIRING_POSITIVE; or stop at a precise blocker with no independent safe task left. Never continue to search for positive results.' \"\$(cat '$task_dir/CURSOR_AUTO_PROMPT_20260930.md')\""
tmux pipe-pane -o -t "$session" "cat >> '$log'"
echo "Started $session. Log: $task_dir/CURSOR_AUTO_20260930.log"
if [[ -t 0 && -t 1 ]]; then
  tmux attach -t "$session"
fi
