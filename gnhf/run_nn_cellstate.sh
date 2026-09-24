#!/usr/bin/env bash
set -eu
# Launch the P22-NN GNHF run (tasks/nn/plan.md) in the main P22 checkout, branch gnhf/p22-nn-cellstate.
# Usage: bash run_nn_cellstate.sh [--check]
#   --check  build the patched runtime, verify it, print the exact invocation, run nothing.
WT="${P22_NN_WORKTREE:-/Users/anuragdani/Github/niw-eb1a/P22}"
P27_TOOLS='/Users/anuragdani/Github/niw-eb1a/P27/gnhf'
OPENCODE_BIN='/Users/anuragdani/Github/niw-eb1a/P22/reports/generated/gnhf_runtime_20260921/node_modules/opencode-darwin-arm64/bin'
MODEL='openrouter/deepseek/deepseek-v4.1-flash'

test "$#" -eq 0 || { test "$#" -eq 1 && test "$1" = '--check'; } || {
  printf '%s\n' 'Usage: bash run_nn_cellstate.sh [--check]' >&2; exit 1; }
test -f "$WT/.git" -o -d "$WT/.git"
test -f "$WT/tasks/nn/plan.md" -a -f "$WT/tasks/nn/todo.md"
test -x "$OPENCODE_BIN/opencode"
cd -- "$WT"
BRANCH="${NN_BRANCH:-gnhf/p22-nn-cellstate}"
PROMPT_FILE="${NN_PROMPT:-tasks/nn/plan.md}"
test -f "$PROMPT_FILE"
test "$(git branch --show-current)" = "$BRANCH"

# Stock GNHF throws "OpenCode produced no final answer" on DeepSeek output (6x in prior
# P22 logs). Reuse the P27 compatibility builder; it only reads P27_WORKTREE as its target.
P27_WORKTREE="$WT" python3 "$P27_TOOLS/runtime/prepare_gnhf.py"
RUNTIME="$WT/.gnhf/p27-deepseek/gnhf-runtime/dist/cli.mjs"
test -f "$RUNTIME"
# ponytail: the replay fixture lives in the P27 worktree; replay there, then require byte-identical copies.
P27_COPY='/Users/anuragdani/Obsidian Vault/Personal Pet Projects/niw-eb1a/papers/P27_ CompliantLLM/gnhf-deepseek-review/.gnhf/p27-deepseek/gnhf-runtime/dist/cli.mjs'
if [ -f "$P27_COPY" ]; then
  cmp -s "$RUNTIME" "$P27_COPY" || { echo 'Patched runtime differs from the replay-tested P27 copy' >&2; exit 1; }
  node "$P27_TOOLS/runtime/test_gnhf_replay.mjs"
else
  echo 'WARN: P27 replay fixture absent; patched runtime built but not replay-tested.' >&2
fi

export PATH="$P27_TOOLS/runtime:$OPENCODE_BIN:$PATH"
unset OPENCODE_CONFIG
export XDG_CONFIG_HOME="$WT/.gnhf/p22-nn/config-home"
export OPENCODE_CONFIG_DIR="$WT/.gnhf/p22-nn/config-dir"
export OPENCODE_DISABLE_PROJECT_CONFIG=true
export OPENCODE_ENABLE_EXA=false
export GNHF_TELEMETRY=0
AGENT_TASK='You execute tasks/nn/plan.md for P22. Each iteration: read the status table at the top of tasks/nn/todo.md, pick the first runnable TODO task, read only that task section with sed, then read section G and that task section of tasks/nn/decision_tree.md and follow its IF/ELSE rules. ONE STEP PER ITERATION: do only the next unfinished numbered Step of that task, never the whole task. Finish that single Step, run focused pytest and ruff on what you touched, append one Run-log line naming the task and the Step you completed (for example "N2 Step 3/7 done: fold preprocessing writer, tests pass"), and leave the task status TODO until its last Step is done, then set DONE:<evidence>. A small committed step beats an ambitious lost one: the orchestrator DISCARDS the work of any iteration that fails, so keep each iteration small enough to finish. Before reading data, check size first; never print or dump an array, list, dataframe, dict of folds or any structure over 20 elements, print only its length and one element; never cat files over 200 lines, use sed ranges; write code files in parts of at most 250 lines. Never ask the user; if a Step cannot work, record BLOCKED:<reason> with evidence and move to the next task. Reuse existing helpers before writing new code (plan rule 13). Use no subagents.'
CONTRACT='Final status contract, including after compaction: return only one JSON object with exactly these five keys and their shown types; no extra fields, fences, or prose. Set both booleans from the saved work, never infer success from this example: {"success":true,"summary":"Finished N1 sampler; N2 next.","key_changes_made":["Added src/p22/data/nn_sampling.py"],"key_learnings":["Seven donors span two libraries."],"should_fully_stop":false}'
# Swarm lanes replace the task part (gnhf/swarm.py sets NN_AGENT_TASK); the JSON contract is fixed.
AGENT_PROMPT="${NN_AGENT_TASK:-$AGENT_TASK} $CONTRACT"
export OPENCODE_CONFIG_CONTENT="$(python3 - "$MODEL" "$AGENT_PROMPT" <<'EOF'
import json, sys
model, prompt = sys.argv[1], sys.argv[2]
short = model.split('/', 1)[1]
print(json.dumps({
    "model": model, "small_model": model, "enabled_providers": ["openrouter"],
    "autoupdate": False, "default_agent": "build",
    "compaction": {"auto": True, "prune": True, "reserved": 16384},
    "provider": {"openrouter": {"models": {short: {"limit": {"context": 65536, "output": 16384}}}}},
    "agent": {"build": {"model": model, "steps": 100, "prompt": prompt}},
    "permission": {"task": "deny"},
}))
EOF
)"

STOP_WHEN='Every task N0-N34 in tasks/nn/todo.md is DONE, BLOCKED:<reason> or NOT_NEEDED:<evidence>; docs/nn_v2/NN_V2_RESULTS_2026-09-23.md exists with the primary cross-attention minus token-concat contrast and its CI; paper/draft.md carries DRAFT_V1_COMPLETE or DRAFT_V1_PARTIAL; N34 verification passed. A BLOCKED Phase 5 does not prevent completion. Null results are valid; never tune toward a win.'
STOP_WHEN="${NN_STOP_WHEN:-$STOP_WHEN}"
CMD=(node "$RUNTIME" --current-branch --agent opencode --model "$MODEL"
  --max-iterations "${NN_MAX_ITER:-80}" --max-tokens 120000000 --max-rate-limit-wait 15m
  --meteor-frequency 0 --prevent-sleep on --stop-when "$STOP_WHEN")

if [ "${1:-}" = '--check' ]; then
  printf 'Runtime ready. Would run in %s:\n' "$WT"
  printf ' %q' "${CMD[@]}"; printf ' < %s\n' "$PROMPT_FILE"
  exit 0
fi

test -z "$(git status --porcelain)" || { echo 'Worktree has uncommitted changes; examine them first.' >&2; exit 1; }
# ponytail: --max-tokens counts cached reads too; it is not a dollar cap. Provider key limit still applies.
exec "${CMD[@]}" < "$PROMPT_FILE"
