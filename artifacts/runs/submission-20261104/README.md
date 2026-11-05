# Submission evidence index

Status: port submission material prepared; full capstone acceptance remains
incomplete. Do not interpret a completion marker as assignment acceptance.
Source baseline: e500c440656622db5ab3f8fb7df73d8b5998eeb3 plus the working tree.
See manifest-before.json and verification.json for exact evidence.

## Reproduce the port

From the repository root, with Emscripten 4.0.18, Python 3, Node 22+, and Chrome:

```sh
source ~/Developer/emsdk/emsdk_env.sh
bash build.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Open http://localhost:8000. Build/run details and controls are in the root
README; check coverage and diagnostic-fault commands are in tests/README.md.
Serve all five dist files together. Deployment has not been performed.

## Evidence map

| Requirement | Evidence / status |
| --- | --- |
| Browser port and music parsing | This run's build-retry.log, tests-committed.log and verification.json |
| Behavioral browser results and screenshots | Browser run paths recorded in verification.json |
| Fault detection | This run's fault logs and verification.json; earlier ../evaluation-20261105T000431Z/fault-checks.json |
| Independent role records | ../../loop-state/integration/attempt-1-review.txt and attempt-1-test.txt; tester acknowledged relying on existing evidence |
| Interrupt/resume | ../evaluation-20261105T000431Z/interruption.json, interrupted-loop.log, resumed-loop.log |
| Source attribution | manifest-before.json, manifest-final.json, source snapshot and browser hashes |
| Manual interventions and unresolved findings | ../evaluation-20261105T000431Z/evaluation.json and handoff.md |
| Reflection | reflection.md is an evidence-based draft requiring student review and personal rationale |

## Remaining acceptance blockers

- Two teammate/instructor-introduced undisclosed regressions with autonomous
  detection, repair, and successful re-verification have not been demonstrated.
- The existing evaluation reports premature completion while tasks remained.
  This student-owned issue remains unresolved.
- MCP-enforced authority boundaries and acceptance-check protection are not
  established by the available evidence.
- Actual resource usage/cost accounting is missing. Historical values are unknown.
- The student's design rationale and reflection must be finalized by the student.
- Port and acceptance checks are committed in `800cf53`. Student-owned
  changes in loop/ remain uncommitted and require the student’s review.

The repository forbids this assistant from modifying or designing the loop.
No loop, engine, asset, or acceptance-check implementation was changed here.
No new acceptance criteria are presented as having existed before implementation.

## Gameplay limits

Actual door/switch activation, physical audio output, and real focus changes
still need verification. Save persistence and mouse aiming are unavailable
in the reviewed port. These limits are disclosed rather than silently treated
as passing. A manual playthrough should record level, browser version,
observed behavior and any failures under artifacts/.
