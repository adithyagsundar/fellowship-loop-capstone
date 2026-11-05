# DOOM agent loop

The loop coordinates separate fresh Claude Code coder, reviewer and tester
processes. Python 3 orchestrates them; a repository-local MCP stdio server supplies
all agent tools. Emscripten is pinned to 4.0.18; the validated local tools are
Claude Code 2.1.317, Python 3.13.5 and Node 22.15.0. Chrome version is recorded by
each browser test. No pip/npm dependencies are needed by the loop.

## Setup, start and resume

Install/authenticate Claude Code outside the repository. Keep credentials out of
source and artifacts. Install Emscripten 4.0.18, Node 22+ and Chrome as described
in the root README. In each build/loop shell:

```sh
source ~/Developer/emsdk/emsdk_env.sh
bash loop/loop.sh --verify-only       # build and tests without model charges
bash loop/loop.sh --new               # all five tasks, new evidence/budget
bash loop/loop.sh                     # resume artifacts/state.json
```

Use `--new --tasks integration` for a scoped whole-port evaluation. To resume a
specific run, use `--run artifacts/runs/loop-<id>`. Ctrl-C or SIGTERM preserves the
incomplete attempt; the next invocation uses fresh contexts and reads handoffs
from disk. An interrupted attempt counts toward the task limit, and its unknown
cost remains reserved. Terminal STALLED/EXHAUSTED runs require `--new`; old evidence
is never deleted. Old `artifacts/loop-state/*.done` files are historical and ignored.

Configuration is `loop/agents.yaml`, stored in JSON syntax (a YAML subset) so the
runner needs no YAML dependency. It supplies bounded task descriptions, model,
20 turns per agent, $2 per invocation, $30 per run, 600 seconds per invocation,
3600 active seconds per run and three attempts per task. The monetary cap is
passed to Claude; reported actual cost and token usage are retained. A missing
usage result is unknown, charged conservatively at the invocation cap. CLI limits
can overshoot by an in-flight API call; actual reported overshoot is recorded and
prevents further launches. This is not a billing guarantee. Historical usage is
not guessed. Downtime while interrupted does not consume active runtime budget.

## Work, context and decisions

The configured tasks cover build, framebuffer, input, WAD/audio and integration.
Each task runs coder → reviewer → tester. The coder receives bounded work and
prior findings, can inspect source and current-run evidence, and changes only
necessary port code. The reviewer independently inspects implementation and
handoffs. The tester executes the protected build/test command through MCP.
All roles start without a continued chat session. Prompts live in `loop/prompts/`.

A cycle passes only when all three CLI invocations succeed, immutable structured
handoffs identify the current source digest, reviewer/tester return PASS, and the
tester has a fresh passing verification. A prose PASS cannot override a failed
CLI result. Reviewer/tester source mutations fail the cycle. Failures and their
paths go to the next coder context. Tests take precedence over unsupported claims;
reviewer FAIL still blocks acceptance even if tests pass. The default integration
task reviews the whole final port. A selected-task run proves only its scope.

Every configured task must finish before SUCCESS. Two unsuccessful cycles without
source changes produce STALLED; retry/time/cost limits produce EXHAUSTED. Tool or
agent failures retain evidence and consume a bounded attempt; there is no hidden
unbounded retry. Other runner errors produce ERROR; interruption produces
INTERRUPTED. SUCCESS applies only to the automated scope in acceptance.md, never
to the full capstone. Source changes invalidate saved completion. After a terminal
success, use --new for a separately budgeted final evaluation.

## Authority and MCP

`loop/mcp/server.py` implements initialize, ping, tools/list and tools/call over
newline-delimited JSON-RPC stdio, following the [MCP transport specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)
and [tool specification](https://modelcontextprotocol.io/specification/2025-03-26/server/tools).
The runner saves each role's exact MCP launch config in its invocation directory.

| Role | MCP tools | Writes |
| --- | --- | --- |
| Coder | list_files, read_file, write_file, handoff | .c/.h/.js/.html/.css in platform/ and web/ only |
| Reviewer | list_files, read_file, handoff | Own one-time handoff only |
| Tester | list_files, read_file, verify, handoff | Own handoff and server-generated verification evidence |

Native tools are disabled with `--tools ''`; strict MCP config excludes unrelated
servers. Settings sources and slash commands are disabled. No Bash, arbitrary
command, arbitrary path, external browsing or delegation tool is supplied. Server
checks enforce capabilities even if a caller requests a hidden tool. Absolute,
hidden, traversal, symlink and hard-link write paths are rejected. Read access is
limited to documented source directories, selected root docs, and the current run.
Credentials, unrelated home files and previous run injection notes are not exposed.

Tests, loop, engine, assets and executable build scripts are human-owned. This
narrows the old prompt-only build-script permission: a coder must report a needed
build change for maintainer intervention. A writable build script would defeat a
fixed verification command by allowing arbitrary execution. MCP handoff files are
immutable, and a tester PASS is refused without a matching fresh verification.

This is a tool authority boundary, not an OS sandbox against malicious generated
C/JavaScript, compromised tooling or concurrent human filesystem edits. Build and
test code executes locally with the operator's OS privileges. The loop assumes
trusted engine/tests/toolchain and reviewed source. No network firewall is claimed:
Claude uses its provider connection; build/browser tests use local files and
loopback HTTP, but OS egress is not blocked. A hostile-code deployment should add
an isolated credential-free container and restricted network policy before use.

## Durable evidence and recovery

`artifacts/state.json` points to a unique run. Each run stores configuration,
source hashes/snapshot, Git revision and patch, append-only invocation directories,
prompts, MCP tool results, structured handoffs, CLI JSON usage, verification logs
and state. State writes use atomic replacement; a repository lock prevents two
runners from editing/testing concurrently. Child stdin is closed, so the CLI cannot
consume the task iterator (a suspected cause of the previous shell-loop defect).
Timeouts/interruption terminate the subprocess group. Unknown interrupted cost is
reserved before launch. Attempt numbers are persisted before work starts, avoiding
old-log overwrites on resume.

## Acceptance and evaluation

See acceptance.md and tests/README.md. The existing port checks are unchanged.
`tests/test_loop.py` adds authority, protocol and orchestration fixtures. Fixture
PASS is not a claim of live multi-agent repair. Real invocations and resource
records are indexed under artifacts/runs/readiness-20261104/.

The original acceptance-before-implementation requirement cannot be established
retroactively. This implementation and documentation were assisted by Codex at the
user's request, which must be included as an intervention. The user elected not to
perform the two teammate/instructor blind regressions; full capstone acceptance
therefore remains incomplete. Physical audio and manual gameplay observations
must likewise never be inferred from automated sample or input checks.
