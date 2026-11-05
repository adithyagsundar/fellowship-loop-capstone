# Acceptance contract and provenance

This document was added during the November 4, 2026 readiness work, after the
port existed. It consolidates existing checks and adds loop verification; it
is not evidence that criteria were specified before implementation. Existing
browser/audio acceptance checks are unchanged. Changes to those checks remain
human-owned and must be separately justified in artifacts/.

## Automated port scope

Emscripten 4.0.18 must build the supplied engine and shareware WAD. The existing
`tests/test_browser.py`, `tests/browser.mjs`, and `tests/test_audio.py` must pass:
WAD/Wasm loading, visible framebuffer, new-game/menu navigation, ongoing
simulation, movement, turning, ammunition consumed by firing, nonzero effects
and music samples, volume/mute, use-key delivery/release, synthetic blur release,
alternate movement keys, weapons, automap and pause/resume. Fatal browser/network
errors fail the run. The music parser must accept all 13 scores, reject malformed
or truncated data and defer audio initialization until a gesture.

A role PASS concerns this automated scope, not the whole assignment. Actual
door/switch activation, OS focus transitions, physical speakers, musical fidelity,
save persistence and mouse aiming are not established by these checks. A manual
playthrough remains separate evidence. Do not invent it.

## Loop scope

Separate fresh coder, reviewer and tester processes exchange immutable MCP
handoffs. Only coder port-source writes are exposed. Protected tests, loop,
engine, WAD and executable build scripts cannot be edited through agent tools.
Tester must execute a fresh fixed verification and tie PASS to its source hash.
Every configured task must pass; stale completion is invalidated by source changes.
Interruptions preserve attempts and reserve unknown cost. Budgets and failure
statuses must be explicit. `tests/test_loop.py` exercises these invariants with
fixtures; it is not evidence of real autonomous repair or live resumption.

## Full assignment scope

Independent verification, fault detection, actual autonomous repair of two blind
teammate/instructor regressions, resumption, accountability, design rationale and
reflection are separate requirements. The user explicitly requested omission of
the teammate exercise. Mark it NOT PERFORMED; never convert scoped SUCCESS into
full capstone acceptance. Historical token/cost usage remains unknown.
