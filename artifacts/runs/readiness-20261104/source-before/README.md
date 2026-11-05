
# DOOM WebAssembly Agent Loop

## Overview

This project implements a multi-agent loop to port the
supplied DOOM engine from C to WebAssembly using Emscripten.

The system consists of three independently invoked agents:

- Coder: Implements the DOOM port and fixes bugs.
- Reviewer: Reviews code for correctness and identifies defects.
- Tester: Independently verifies the implementation.

A central orchestrator coordinates the agents, manages
retries, saves state, and decides when tasks are complete.

## Work

The orchestrator divides the DOOM port into bounded tasks:

1. Configure the Emscripten build system.
2. Implement framebuffer rendering in the browser.
3. Implement keyboard input and game timing.
4. Package and load the DOOM shareware WAD.
5. Integrate everything into a playable browser game.

Each task follows this workflow:

Coder -> Reviewer -> Tester -> Orchestrator

The Coder implements the task. The Reviewer examines the
changes, and the Tester evaluates whether the implementation
meets its acceptance criteria.

If either agent finds a problem, the orchestrator sends
the findings back to the Coder for another attempt.

When agents disagree, reproducible test evidence takes
priority over unverified claims.

If repeated attempts fail, the orchestrator stops the task
and records the blocker.

## Context

Each agent starts with a fresh context and receives only
the information relevant to its responsibilities.

Coder:
- Current task description
- Relevant repository files
- Previous review and test failures

Reviewer:
- Task requirements
- Source code and Git changes
- Coder implementation summary

Tester:
- Acceptance criteria
- Relevant test scripts
- Source revision
- Build and runtime evidence

Persistent state is stored in artifacts/.

This includes task progress, handoffs, review findings,
test results, errors, Git revision identifiers, and
retry history.

On restart, the orchestrator reads these artifacts to
reconstruct the current state without relying on
previous agent conversations.

## Authority

The Coder may modify implementation files in:

- platform/
- web/
- Shared build scripts

The Reviewer may inspect source code and produce
review findings but cannot modify implementation files.

The Tester may inspect source code and execute verification
checks but cannot modify implementation files.

Protected acceptance tests live in tests/.

The Coder cannot modify these tests. Changes to acceptance
criteria require explicit human approval and must be logged
with a justification.

Role boundaries are intended to be enforced through
role-specific MCP tools and filesystem permissions,
not only through agent prompts.

## Evidence

The DOOM port is considered successful only when:

1. The engine compiles using Emscripten.
2. The browser loads the generated WebAssembly module.
3. The shareware doom1.wad loads successfully.
4. The game renders continuously.
5. Keyboard controls support movement, turning, and shooting.
6. The player can interact with the game world.
7. The browser runs without fatal errors.

A successful compilation or screenshot alone is not
sufficient evidence.

The Tester must independently execute checks and preserve
build logs, browser results, and the corresponding Git revision.

To evaluate the tests themselves, deliberately introduced
faults must cause relevant checks to fail.

## Recovery

The loop handles failures as follows:

- Tool errors: Retry transient failures up to two times.
- Failed review: Return specific findings to the Coder.
- Failed test: Return reproducible failure evidence.
- Interrupted run: Reload saved state from artifacts/.
- Repeated failure: Stop after three unsuccessful repairs.

After each repair, the Tester reruns relevant checks to
ensure the fix works and does not introduce regressions.

The evaluation will also include two undisclosed regressions
introduced after initial success. The agents must detect and
repair them without being told their causes.

## Limits

The system uses the following initial budgets:

- Maximum repair attempts per task: 3
- Maximum agent turns per invocation: 15
- Proposed cost budget per agent invocation: $2
- Total project duration: 7 days

The orchestrator records attempts and resource usage.

There are three possible stopping decisions:

SUCCESS:
All required acceptance checks pass, the Reviewer approves,
and browser functionality is independently verified.

EXHAUSTED:
The system reaches its retry, time, or cost limit.
It stops and records remaining issues.

STALLED:
Repeated attempts do not produce meaningful progress.
The orchestrator records the blocker and stops or
restructures the task.

## Repository Structure

loop/
    README.md       Design documentation
    agents.yaml     Agent roles and task configuration
    loop.sh         Orchestrator
    prompts/        Reusable agent instructions
    mcp/            MCP server and tool configuration

artifacts/
    Persistent state, handoffs, logs, and evidence

tests/
    Acceptance tests and loop verification

platform/
    DOOM engine platform integration

web/
    Browser page and JavaScript integration

assets/
    Shareware DOOM WAD

build/ and dist/
    Generated build artifacts

## Running the Loop

From the repository root:

    chmod +x loop/loop.sh
    ./loop/loop.sh

## Resuming the Loop

Run the same command again:

    ./loop/loop.sh

The orchestrator uses saved state in artifacts/ to
identify completed tasks and continue unfinished work.

## Evaluation

The completed project will demonstrate:

1. Independent verification of the final DOOM port.
2. Tests that detect intentionally broken behavior.
3. Autonomous repair of at least two undisclosed regressions.
4. Resumption after an interrupted run.
5. Traceable findings, repairs, resource use, and decisions.

All passing and failing evidence will be preserved.

## Implementation Status

This README describes the intended architecture.

The starter orchestration script provides separate agent
invocations, basic retries, and artifact persistence.

MCP-enforced permissions, protected browser acceptance
tests, comprehensive resource tracking, and regression
evaluation must be implemented and validated before
the complete design can be claimed as working.
