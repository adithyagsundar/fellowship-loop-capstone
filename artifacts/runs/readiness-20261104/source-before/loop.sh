#!/usr/bin/env bash
set -uo pipefail

# Run from repository root, regardless of current directory.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONFIG="loop/agents.yaml"
STATE="artifacts/loop-state"
mkdir -p "$STATE"

if ! command -v claude >/dev/null 2>&1; then
  echo "Error: Claude Code CLI is not installed."
  echo "Install it and run 'claude' to sign in."
  exit 1
fi

# Read tasks and retry count from agents.yaml.
mapfile_tasks() {
  sed -n 's/^  - id: //p' "$CONFIG"
}

MAX_RETRIES="$(sed -n 's/^  max_retries: //p' "$CONFIG" | head -1)"
MAX_RETRIES="${MAX_RETRIES:-3}"
MAX_TURNS="$(sed -n 's/^  max_turns_per_agent: //p' "$CONFIG" | head -1)"
MAX_TURNS="${MAX_TURNS:-15}"


run_agent() {
  local role="$1"
  local prompt="$2"
  local output="$3"

  local tools

  if [[ "$role" == "coder" ]]; then
    tools="Read,Write,Edit,Glob,Grep,Bash"
  else
    tools="Read,Glob,Grep"
  fi

  claude -p "$prompt" \
    --model sonnet \
    --tools "$tools" \
    --allowedTools "$tools" \
    --permission-mode dontAsk \
    --max-turns "$MAX_TURNS" \
    --output-format text > "$output" 2>&1

  return $?
}


run_checks() {
  local output="$1"
  local checks=0
  local failed=0

  : > "$output"

  if [[ -f build.sh ]]; then
    checks=$((checks + 1))
    echo "=== Emscripten build ===" >> "$output"
    bash build.sh >> "$output" 2>&1 || failed=1
  elif [[ -f Makefile ]]; then
    checks=$((checks + 1))
    echo "=== Make build ===" >> "$output"
    make >> "$output" 2>&1 || failed=1
  else
    echo "No build script found." >> "$output"
  fi

  if find tests -name 'test_*.py' -print -quit 2>/dev/null | grep -q .; then
    checks=$((checks + 1))
    echo "=== Python acceptance tests ===" >> "$output"
    python3 -m unittest discover -s tests -p 'test_*.py' \
      >> "$output" 2>&1 || failed=1
  fi

  if [[ "$checks" -eq 0 ]]; then
    echo "NO_CHECKS: Cannot verify implementation." >> "$output"
    return 1
  fi

  if [[ "$failed" -ne 0 ]]; then
    echo "CHECKS_FAILED" >> "$output"
    return 1
  fi

  echo "AUTOMATED_CHECKS_PASSED" >> "$output"
  return 0
}

echo "Starting DOOM multi-agent loop"

# Each task gets independent coder, reviewer and tester runs.
while IFS= read -r task; do
  [[ -z "$task" ]] && continue

  done_file="$STATE/${task}.done"
  if [[ -f "$done_file" ]]; then
    echo "Skipping completed task: $task"
    continue
  fi

  echo "===================================="
  echo "Task: $task"
  echo "===================================="

  task_dir="$STATE/$task"
  mkdir -p "$task_dir"

  success=0

  for ((attempt=1; attempt<=MAX_RETRIES; attempt++)); do
    echo "Attempt $attempt / $MAX_RETRIES"

    prefix="$task_dir/attempt-$attempt"
    revision_before="$(git rev-parse HEAD 2>/dev/null || echo unknown)"

    previous=""
    if (( attempt > 1 )); then
      prev=$((attempt - 1))
      previous="
Read the previous review, test, and check reports:
$task_dir/attempt-$prev-review.txt
$task_dir/attempt-$prev-test.txt
$task_dir/attempt-$prev-checks.txt
Fix the identified issues."
    fi

    echo "[1/3] Running Coder"

    coder_prompt="
You are the CODER for the DOOM WebAssembly capstone.

Current task: $task

Read AGENTS.md, platform/README.md, and relevant source files.
Use the supplied DOOM engine, Emscripten, and shareware WAD.

Implement this task with actual repository changes.
Do not alter protected acceptance tests or loop configuration.
Only edit implementation files in platform/, web/,
and shared build scripts.

$previous

Summarize:
1. Files changed
2. What you implemented
3. What remains incomplete
"

    if ! run_agent coder "$coder_prompt" "$prefix-coder.txt"; then
      echo "Coder execution failed." >> "$prefix-coder.txt"
    fi

    git diff -- platform web build.sh Makefile \
      > "$prefix-diff.patch" 2>/dev/null || true

    echo "[2/3] Running Reviewer"

    reviewer_prompt="
You are the independent REVIEWER for the DOOM port.

Task: $task
Original revision: $revision_before

Read the implementation and the coder report:
$prefix-coder.txt

Examine source code and the current Git diff.
Check correctness, integration, and missing functionality.
Do not modify any files.

Your response MUST end with exactly one of:
VERDICT: PASS
VERDICT: FAIL

Use FAIL if there are material unresolved defects.
Provide specific findings and file references.
"

    if ! run_agent reviewer "$reviewer_prompt" "$prefix-review.txt"; then
      echo "VERDICT: FAIL" >> "$prefix-review.txt"
    fi

    echo "[3/3] Running automated checks"

    checks_ok=0
    if run_checks "$prefix-checks.txt"; then
      checks_ok=1
    fi

    echo "Running Tester"

    tester_prompt="
You are the independent TESTER for the DOOM port.

Task: $task

Read:
$prefix-coder.txt
$prefix-review.txt
$prefix-checks.txt

Inspect implementation files and acceptance tests.
Do not modify files.

Evaluate whether available evidence supports the task.
A successful compile alone does not prove browser playability.
Do not claim to have interacted with a browser unless
the evidence actually demonstrates that interaction.

Your response MUST end with exactly one of:
VERDICT: PASS
VERDICT: FAIL

Use FAIL if checks are missing or evidence is insufficient.
Describe the specific checks needed for verification.
"

    if ! run_agent tester "$tester_prompt" "$prefix-test.txt"; then
      echo "VERDICT: FAIL" >> "$prefix-test.txt"
    fi

    reviewer_pass=0
    tester_pass=0

    grep -q '^VERDICT: PASS$' "$prefix-review.txt" && reviewer_pass=1
    grep -q '^VERDICT: PASS$' "$prefix-test.txt" && tester_pass=1

    revision_after="$(git rev-parse HEAD 2>/dev/null || echo unknown)"

    {
      echo "task=$task"
      echo "attempt=$attempt"
      echo "revision_before=$revision_before"
      echo "revision_after=$revision_after"
      echo "reviewer_pass=$reviewer_pass"
      echo "tester_pass=$tester_pass"
      echo "checks_ok=$checks_ok"
    } > "$prefix-status.txt"

    if [[ "$reviewer_pass" -eq 1 &&
          "$tester_pass" -eq 1 &&
          "$checks_ok" -eq 1 ]]; then
      echo "Task passed: $task"
      touch "$done_file"
      success=1
      break
    fi

    echo "Verification failed; preparing repair attempt."
  done

  if [[ "$success" -ne 1 ]]; then
    echo "Task exhausted retry budget: $task"
    echo "BLOCKED: $task" | tee "$STATE/final-status.txt"
    exit 1
  fi

done < <(mapfile_tasks)

echo "All task cycles passed their available automated checks."
echo "Browser gameplay verification is still required."
echo "AUTOMATED_PHASE_COMPLETE" | tee "$STATE/final-status.txt"
