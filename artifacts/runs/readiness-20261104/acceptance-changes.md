# Acceptance changes and chronology

Date: November 4, 2026 (user timezone). Authorization: the user requested the
readiness implementation and evaluation work, excluding the teammate exercise.

The three original browser/audio acceptance files are unchanged; see
protected-checks.json. No existing port assertion was weakened or removed.

Added loop/acceptance.md to consolidate the existing automated port scope and
separate full-assignment requirements. This was written after the port existed.
The repository evidence does not establish pre-implementation timing for this
new document. It must not be backdated or represented as satisfying that timing
requirement retroactively.

Added 20 tests in tests/test_loop.py for the new authority and orchestration
implementation. They cover real stdio protocol requests in fixture repositories,
role capability denials, traversal/link protection, stale/latest verification,
immutable handoffs, evidence discovery, all-task completion, failure blocking,
cost/time/retry limits, closed child stdin, and interrupted-run preservation.
Mocked role invocations are explicitly fixtures, not a blind repair exercise.

Verification now checks emcc's reported version against the already documented
Emscripten 4.0.18 pin and records the command and version. Tester PASS requires
the latest verification to pass on the same source. These changes improve
attribution and prevent stale or selectively chosen evidence from accepting work.

The automated scope still does not establish doors/switches, OS focus changes,
physical audio, fidelity, save persistence or mouse aiming. These limits are
not silently converted into passing criteria. The omitted teammate/instructor
exercise remains an unmet assignment requirement, not a relaxed requirement.
