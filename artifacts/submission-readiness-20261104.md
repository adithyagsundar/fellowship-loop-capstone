# Submission readiness review — November 4, 2026

Task: assess remaining submission work against README.md. Read-only code review; no build, tests, or agent loop executed. Source HEAD: 2a71a8008f2ab757087e227c03337a67c8201110. Existing uncommitted changes: AGENTS.md, loop/README.md, loop/agents.yaml, loop/loop.sh. No implementation changes made by this review.

## Existing evidence

- artifacts/runs/submission-20261104/verification.json records build and two unittest passes, 16 browser checks, and three expected diagnostic-fault failures at revision 800cf53f004843d2aed87eac883752d5abd49551. This is historical evidence, not fresh verification of HEAD plus current changes.
- artifacts/runs/evaluation-20261105T000431Z/evaluation.json records separate role invocations, task-level interruption/resumption, manual restarts, premature completion, and missing authority/cost evidence.
- artifacts/runs/submission-20261104/reflection.md is an explicit draft.

## Prioritized remaining work

1. Implement and demonstrate MCP tool access/handoffs and enforce role permissions. Current loop/ contains only README.md, agents.yaml, and loop.sh. The script gives coder unrestricted Write/Edit/Bash tool types; YAML writable/forbidden paths are not consulted to enforce file access. Preserve a denied test-modification attempt as evidence. Give the tester a protected way to execute verification (currently only Read/Glob/Grep are available; the orchestrator runs checks).
2. Fix and verify orchestration correctness. Historical premature completion remains unresolved in the evidence. Inspect shared stdin between the task-reading loop and child CLI as a possible cause, not a proven diagnosis. Current completion markers are not tied to revision/check hashes; retries restart from attempt 1 and overwrite reports; verdict parsing accepts any PASS line rather than only a validated final verdict. Demonstrate all tasks run, failures block success, stale completion is invalidated, interruption retains evidence, and exhausted/stalled/success outcomes are distinct.
3. Enforce resource budgets and capture actual usage. The YAML dollar limit is not consumed by loop.sh. Record tokens/cost when available, elapsed time, retries, interventions, and stopping reason per invocation/run. Historical unknown usage must remain unknown.
4. Run the required two teammate/instructor-introduced undisclosed regressions after initial success. Preserve injection provenance separately from repair-agent context; retain failing checks, handoffs, autonomous repair diffs, review, and passing reruns. Existing diagnostic faults establish detection only.
5. Close gameplay verification gaps: record actual door/switch interaction, real focus changes, and audible sound in a manual playthrough, with browser/version and source identification. Document unsupported mouse aiming/save persistence and simplified music; do not automatically treat those as mandatory new features.
6. Finalize acceptance/design documentation and personal reflection. Locate dated pre-implementation criteria if available; do not retroactively claim new criteria predated implementation. Log later criterion changes separately. Reconcile intended architecture in loop/README.md with implemented behavior, explain each role/handoff, missed faults, disagreements, and a proposed design change. Older submission docs claim assistant loop edits were forbidden; current AGENTS.md no longer contains that restriction, so clarify the historical wording.
7. Package the final revision: review and commit intended changes, rerun build and protected verification on the final source, repeat interrupt/resume after loop fixes, and update the evidence index with exact source/build hashes, failing and passing evidence, usage and stop status. Verify fresh setup/start/resume instructions. Deployment is not explicitly required by the assignment.

## Handoff

Status: assessment complete; full capstone not submission-ready. Next action: address loop authority and orchestration issues, then execute evaluation with protected checks and teammate/instructor blind injections. No new runtime results or resource/cost claims were produced by this review.
