# Intervention and provenance ledger

- User requested completion of readiness work, including a reflection draft.
- User explicitly excluded the teammate/instructor regression exercise. It is
  NOT PERFORMED, not replaced by diagnostic fault tests.
- Codex assessed the prior evidence, replaced the shell orchestration with a
  Python runner and MCP server, added loop tests, and wrote documentation and
  the reflection. These are assistant/maintainer interventions, not autonomous
  achievements of the evaluated loop.
- Original browser/audio acceptance files were left unchanged. New loop tests
  were added separately. loop/acceptance.md was written after implementation;
  no claim of pre-implementation criteria is made.
- Original dirty files and loop source were preserved in source-before/.
- First local verification hit an Emscripten cache sandbox permission error.
  verification-first.log and artifacts/runs/verification-867c826e3b85 preserve it.
  Verification was retried with normal host toolchain/browser access.
- New CLI invocations record reported cost/tokens. This assistant's own usage
  and historical loop costs are not available in these records.
- Deliberately sent SIGTERM to loop process 66114 during the first build task's
  tester invocation. Saved interrupted-state.json and resumed with the existing
  pointer and fresh contexts. The MCP file-list omission was corrected between
  runs, so source invalidation is also exercised; this is a recorded intervention,
  not a claim of uninterrupted autonomy.
- Attempted interactive verification through both browser and native Chrome
  access. Both were unavailable; see manual-gameplay.md. No playthrough or
  physical audio observation is claimed.
- Stopped the task-owned local HTTP server (PID 66546) after interactive access failed.
- After the successful five-task run, the maintainer added compiler-version
  enforcement, raw log excerpts, latest-result enforcement and baseline checks,
  then committed source as 1ba5d20. New loop tests increased from 13 to 20.
- A discovery-test failure was caused by the fixture's unresolved macOS /var
  temporary path versus the server's canonical /private/var path. Normalizing
  fixture roots fixed it; both failed and passing logs are retained.
- A new scoped integration run evaluates the final source separately from the
  historical five-task run. Diagnostic browser faults are repeated separately;
  they are not attributed to the loop as undisclosed repairs.
