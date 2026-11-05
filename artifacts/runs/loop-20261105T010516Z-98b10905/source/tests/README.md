# Verification

Build with Emscripten 4.0.18, then run the existing checks with Python 3,
Node.js 22 or newer, and Google Chrome:

```sh
source ~/Developer/emsdk/emsdk_env.sh
bash build.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Set `CHROME_BIN` to the browser executable if automatic detection fails.
`test_browser.py` launches `browser.mjs`, which serves `dist/` locally and
drives headless Chrome through the DevTools protocol. `test_audio.py`
validates all 13 bundled MUS scores, truncated/invalid score rejection,
and deferred audio initialization.

Browser checks cover WAD/module loading, rendered pixels, menu/new-game input,
simulation timing, movement, turning, firing/ammunition, audio waveforms,
mute/volume, use-key state, synthetic blur, movement aliases, weapon selection,
automap, and pause/resume. Browser errors and failed requests cause failure.

## Fault detection

Run each command separately; each is expected to exit nonzero:

```sh
DOOM_TEST_FAULT=ignore-input node tests/browser.mjs
DOOM_TEST_FAULT=blank-canvas node tests/browser.mjs
DOOM_TEST_FAULT=silent-effects node tests/browser.mjs
```

Check the reported assertion, not just the exit code: expected failures are
menu input, blank canvas, and missing firing audio respectively. These are
browser-only diagnostic faults. They are not teammate-introduced blind
regressions and do not demonstrate autonomous repair.

## Evidence and limits

Each browser invocation saves `results.json`, source/build hashes, the Git
revision and working-tree status, browser logs, a tracked-source patch, and
available screenshots in a unique `artifacts/runs/browser-*` directory.
Untracked source contents are not included in `git diff`; preserve the
source separately or commit it for reproducibility.

These checks do not prove successful door/switch activation, actual operating
system focus changes, physical speaker output, or musical fidelity. Save
persistence across reloads and mouse aiming are not supported by the reviewed
port. Music uses simplified synthesis. The timing sample is three seconds
with a 28–42 simulation-tics/second tolerance.

This documents the existing checks; it does not establish that acceptance
criteria were recorded before implementation. Protection against coder edits
requires permission-enforcement evidence; a tests directory alone is not
proof. Existing acceptance-check code was not changed during submission prep.

## Loop verification

`test_loop.py` adds controlled authority, protocol, stale-evidence, budget,
interruption/resumption and completion tests. Run it without a browser or model
charges with `python3 -m unittest discover -s tests -p test_loop.py -v`.
Fixtures use temporary repositories and mocked role invocations; they do not
claim real autonomous repair. The readiness evidence separately records real
Claude role invocations, a real MCP protected-file denial and live resumption.
The original browser/audio acceptance files were not modified by this work.
