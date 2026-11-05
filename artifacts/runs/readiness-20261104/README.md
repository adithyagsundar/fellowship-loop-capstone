# Submission evidence — November 4, 2026 readiness work

Status: automated readiness work completed; full assignment acceptance remains
INCOMPLETE. The user explicitly omitted the two teammate/instructor blind
regression repairs. Interactive door/switch, real focus and physical speaker
checks could not be performed because browser access and native Computer Use
permissions were unavailable. Do not turn the loop's scoped SUCCESS into full
capstone acceptance.

## Deliverables

- [Loop design, setup and resume instructions](../../../loop/README.md)
- [Acceptance scope and chronology](../../../loop/acceptance.md)
- [Completed reflection draft](reflection.md)
- [Manual interventions and provenance](interventions.md)
- [Interactive verification blocker and remaining procedure](manual-gameplay.md)
- [Original readiness assessment](../../submission-readiness-20261104.md)

The reflection is fully written, with assistance disclosed. It contains no invented
playthrough, hidden-regression exercise, historical resource totals or claim that
later criteria existed before implementation.

## Evidence map

| Requirement | Evidence and result |
| --- | --- |
| Working browser port | Fresh build and original behavioral checks pass; verification-retry.log links the first new successful verification |
| Protected checks | authority-probe-final.json records a real MCP coder write denial against tests/browser.mjs; protected-checks.json shows the original acceptance files unchanged |
| Loop invariants | loop-tests-final-retry.log: 20 tests pass; fixtures are explicitly separate from live agent claims |
| Separate live roles | ../loop-20261105T005309Z-73a58c79/ contains independent coder/reviewer/tester CLI results, MCP tool logs and immutable handoffs |
| All configured tasks | completed-five-task-state.json records SUCCESS for build, rendering, input, wad and integration |
| Live interruption/resumption | live-loop.log, interrupted-state.json, resumed-loop.log; incomplete attempt preserved, fresh contexts resumed, all tasks subsequently completed |
| Review disagreement | Build attempt 2 reviewer withheld PASS for lack of execution; tester produced matching evidence; build attempt 3 reviewer approved |
| Resource accounting | Each live run state.json records actual reported cost/tokens, elapsed time and reserved unknown interrupted usage; aggregate in final-summary.json |
| Fault detection | All three final diagnostic faults fail at their intended assertions; see final-faults.json |
| Final source | final-summary.json and the final live/verification source manifests identify Git revisions, hashes and dirty state |
| Blind autonomous repair | NOT PERFORMED at user's request; diagnostic faults do not satisfy this requirement |
| Manual gameplay | BLOCKED; see manual-gameplay.md |
| Acceptance chronology | Consolidated contract is explicitly post-implementation; original chronology is not reconstructed |

## Reproduce

With Emscripten 4.0.18, Python 3, Node 22+ and Chrome installed:

```sh
source ~/Developer/emsdk/emsdk_env.sh
bash loop/loop.sh --verify-only
bash loop/loop.sh --new
# After interruption:
bash loop/loop.sh
```

The live loop also requires authenticated Claude Code. Each new default run has
an explicit $30 cap and $2 per invocation; CLI-reported actual cost can exceed a
cap by an in-flight call, and unknown usage is reserved rather than guessed.
`--new --tasks integration` evaluates the whole port in one scoped role cycle.
Serve dist/ with a local HTTP server to play; all five generated files must stay
together. Deployment is not required by the assignment and was not performed.

## Preserved failures and interpretation

The first build attempt was denied access to the Emscripten cache; its log remains
in ../verification-867c826e3b85/. The first live run was deliberately interrupted.
The initial MCP file list omitted readable root documents; it was fixed by the
maintainer and the changed source invalidated stale state. The first new discovery
test exposed macOS /var versus /private/var fixture-path normalization; that test
failure is preserved in loop-tests-final.log and fixed in the subsequent pass.
These interventions are not represented as autonomous repairs by the evaluated
loop. Older submission-20261104/ records remain historical; their former claims
that assistant loop work was prohibited describe the earlier policy, not current
user authorization.

## Final measured result

Source commit: `1ba5d20a7c5fcf51fde2a6edfaa1d586ad38bd38`.
Source digest: `db7ae64a828f0aacdb7a7e34d5e5faa4d0b3dd9acb832b52d556950250c9ba25`.
The final scoped integration run is
[loop-20261105T010516Z-98b10905](../loop-20261105T010516Z-98b10905/state.json):
SUCCESS on its first attempt. Its independent tester passed all 22 Python tests,
including 20 loop tests, 16 browser behavior checks within the browser test, and
13 music scores within the audio test. Emscripten 4.0.18 was explicitly checked.
The final browser source/build hashes match the delivered files.

The earlier five-task run establishes live continuation after interruption on
its recorded working-tree digest; the final integration run evaluates the later
committed version with reporting/baseline refinements. These distinct revisions
are preserved in [final-summary.json](final-summary.json), not conflated.
A no-op resume of the completed final run exits successfully without spending
more model budget (completed-resume.log).

Total reported actual model cost across these two runs is **$1.91712950**. One
interrupted invocation has unknown actual cost and a separate **$2 reserve**.
This is not a complete historical or assistant-wide billing total. See the JSON
summary for token categories, elapsed time and per-run usage.

[Acceptance change log](acceptance-changes.md) and [final handoff](handoff.md)
record chronology, remaining requirements and the next action. The evidence-only
packaging commit changes artifacts, not the verified source.
