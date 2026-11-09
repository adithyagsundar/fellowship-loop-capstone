# DOOM in the Browser: an Evidence-Driven Agent Loop

A WebAssembly port of DOOM and a three-role agent system for implementing, reviewing, and testing it. Built by **Adithya Gnanasundar** for the fellowship capstone, using the supplied Doom engine and shareware game data.

**[Play the live game](https://adithyagsundar.github.io/fellowship-loop-capstone/)** · [Loop documentation](loop/README.md) · [Verification guide](tests/README.md) · [Project reflection](artifacts/runs/readiness-20261104/reflection.md)

The project has two deliverables: a playable browser port and an agent loop whose decisions can be checked against saved evidence. The game runs in a desktop browser without installing the engine. The loop coordinates separate Claude Code coder, reviewer, and tester processes, restricts their tools through MCP, and preserves enough state to resume after interruption.

The browser port is deployed and its automated checks pass. Full capstone evaluation remains incomplete: the two independent blind-regression repair exercises were not performed, and several manual gameplay checks remain unverified. Those distinctions are recorded throughout the evidence rather than hidden behind a single success label.

## What we are trying to do—and why use agents?

The goal is to explore how to give AI agents a substantial software task and make their progress verifiable. DOOM is the workload: taking an existing C engine into the browser requires rendering, timing, input, file loading, and audio to work together. That gives the agent system concrete problems to solve and observable behavior to test.

If we ported DOOM ourselves, we would inspect the code, choose the next change, debug failures, and decide when the result was good enough. In this project, those decisions also become part of the system we are building. The loop assigns bounded work, gives each role specific tools, sends findings between separate agents, and decides whether to retry, stop, or accept a result based on recorded evidence. Our responsibility is to design those rules and evaluate whether they work.

That changes what counts as success. A playable game shows that the port works within its tested scope. To trust the agent loop, we also need evidence that it catches mistakes, protects its tests, preserves disagreements, resumes after interruption, and stays within explicit resource limits. A game that works only because we repeatedly step in and repair it would not, by itself, demonstrate an effective autonomous workflow. Human interventions therefore need to remain visible in the record.

The broader aim is to learn which parts of software development can be delegated reliably and what checks that delegation requires. The same questions apply to other engineering tasks: can a reviewer challenge a coder's claim, can a tester supply independent evidence, and can the system continue from saved state without a person reconstructing the history? This project demonstrates parts of that workflow through live role runs, protected verification, and resumption. Its ability to repair independently introduced unknown regressions remains unevaluated because the blind-regression exercises were not performed.

## What I built

The starting repository provided the C engine, the Episode 1 shareware WAD, platform and HTML stubs, and assignment documentation. This project added the browser integration, build script, sound and music backend, verification suite, and executable agent orchestration.

| Component | Implementation |
| --- | --- |
| Browser port | C platform callbacks in `platform/doomgeneric_wasm.c`, compiled to WebAssembly with Emscripten |
| Rendering and timing | Framebuffer conversion for the browser canvas, clock/sleep integration, and a continuing game simulation |
| Input | Keyboard press/release handling, movement, turning, firing, menus, automap, and pause controls |
| Game data | The supplied `doom1.wad`, packaged into the module's virtual filesystem |
| Audio | C audio integration in `platform/doom_audio.c` and Web Audio playback/sequencing in `web/audio.js` |
| Browser interface | Canvas, sound activation, menu, pause/resume, mute, and volume controls in `web/index.html` |
| Agent loop | Python orchestration, separate role prompts, MCP tools, structured handoffs, budgets, and resumable state |
| Verification | Browser behavior checks, music-data validation, loop authority tests, and saved run evidence |
| Deployment | A compiled static build published from `gh-pages` on this fork |

The supplied engine remains the foundation of the game. Music uses simplified synthesized instruments; it does not reproduce the original OPL synthesis faithfully.

## Play

Open **https://adithyagsundar.github.io/fellowship-loop-capstone/** in a desktop browser. Click **Enable sound** or focus the canvas and press a game key, then use the menu to start a game.

| Action | Key |
| --- | --- |
| Move / turn | Arrow keys |
| Move forward / backward | W / S |
| Strafe left / right | A / D |
| Fire | Ctrl |
| Use | Space |
| Run | Shift |
| Select available weapon | 1–7 |
| Automap | Tab |
| Menu / confirm | Esc / Enter |
| Pause / resume | P |

The page also provides Menu, Pause/Resume, Mute, and Volume controls. Mouse aiming and persistent saves across reloads are not supported by the reviewed port.

## How the agent loop works

The loop divides work into five tasks: **build, rendering, input, WAD/audio, and integration**. Each task runs through a coder, reviewer, and tester with fresh contexts. The agents exchange structured handoffs and refer to repository files and saved evidence instead of relying on a shared chat history.

A baseline verification runs before the role cycle. The coder receives the bounded task and previous findings, the reviewer independently inspects the result, and the tester executes the protected verification command. Failed checks and review findings are carried into the next attempt.

| Role | Responsibility | Allowed writes |
| --- | --- | --- |
| Coder | Implement or repair the browser port and explain the change | Permitted C, header, JavaScript, HTML, and CSS files inside `platform/` and `web/` |
| Reviewer | Inspect correctness, identify missing requirements, and submit PASS or FAIL | Its own immutable handoff |
| Tester | Run the fixed build/test verification and report source-matched results | Its handoff and server-generated verification evidence |

The repository-local [MCP server](loop/mcp/server.py) enforces these permissions. Native agent tools are disabled, and the agents do not receive a general shell or arbitrary file-write tool. Tests, build scripts, orchestration, engine code, and game assets are protected from coder edits.

A task passes only when all role invocations succeed, the handoffs refer to the current source digest, the reviewer approves, and the tester has fresh passing verification. Passing tests do not erase a reviewer FAIL, and a written PASS cannot override a failed command.

This is a tool-access boundary. It is not an operating-system sandbox for hostile generated code: builds and tests still execute with the operator's local privileges. The full authority model is documented in [loop/README.md](loop/README.md).

## Recovery, budgets, and stopping

Each run stores its configuration, source revision and hashes, task state, attempts, handoffs, verification logs, and reported usage under `artifacts/`. Failed and interrupted attempts remain available. Source changes invalidate stale completion, and resumption starts fresh agent contexts using the saved state.

The default configuration in [loop/agents.yaml](loop/agents.yaml) uses the `sonnet` model alias and these limits:

| Limit | Default |
| --- | --- |
| Attempts per task | 3 |
| Turns per agent invocation | 20 |
| Budget per invocation | $2 |
| Budget per run | $30 |
| Time per invocation | 600 seconds |
| Active runtime per run | 3,600 seconds |

The runner distinguishes `SUCCESS`, `STALLED`, `EXHAUSTED`, `INTERRUPTED`, and `ERROR`. Two unsuccessful cycles without source changes produce a stalled result. Budget or retry exhaustion stops further work. Interrupted usage that cannot be measured is reserved conservatively rather than counted as zero. Provider calls can overshoot a CLI budget by an in-flight request, so these controls are not a billing guarantee.

## What the evaluation demonstrated

The [readiness evidence index](artifacts/runs/readiness-20261104/README.md) links the live agent runs, authority checks, interrupted state, resumed execution, and resource records. The [deployment evidence](artifacts/runs/pages-20261109/README.md) records the later build and publication.

| Result | Evidence and interpretation |
| --- | --- |
| Browser build and tests pass | The November 9 deployment run passed all 22 Python tests, including the browser acceptance and audio-data tests |
| Behavioral checks go beyond a screenshot | The browser suite checks simulation, position changes, turning, ammunition consumption, rendered pixels, and audio samples, among other behaviors |
| Audio data is validated | All 13 bundled MUS scores are checked, along with malformed/truncated input rejection and deferred audio initialization |
| Checks detect deliberate faults | Ignored input, a blank canvas, and silent effects each produced the intended failing assertion in the saved evaluation |
| Coder permissions are enforced | A live MCP probe denied a coder attempt to write a protected browser test |
| Separate roles run in practice | Saved CLI results, tool logs, and handoffs identify independent coder, reviewer, and tester invocations |
| Interruption and resumption work | A live interrupted run preserved its incomplete attempt, resumed with fresh contexts, and subsequently completed all five tasks |
| Review disagreement is retained | A build reviewer withheld approval for missing execution evidence; later source-matched verification supported approval in a subsequent cycle |
| Public deployment is verified | All five game files returned HTTP 200 and matched the local tested build byte-for-byte; WebAssembly was served with the correct MIME type |

The 22 Python tests include 20 loop tests, one browser test containing 16 behavior checks, and one audio test covering the music data. Fixture-based loop tests are distinct from the saved live role runs.

Across the two documented readiness runs, reported actual model cost totaled **$1.91712950**, with a separate **$2 reserve** for one interrupted invocation whose actual cost was unknown. This is not the total cost of the project or all assistant work. See [final-summary.json](artifacts/runs/readiness-20261104/final-summary.json) for the recorded usage and source identities.

## What changed during development

An earlier shell-based loop printed a completion message while later tasks were still unfinished, and manual restarts were needed. That exposed a problem in the coordinator even though the game itself worked.

The replacement Python runner tracks every task and attempt explicitly, closes child stdin, validates structured handoffs, ties results to source hashes, and preserves distinct stopping states. Shared stdin was a suspected cause of the earlier failure; the historical logs do not establish it as the sole cause.

The authority model also moved from documented forbidden paths to enforced MCP permissions. Protecting tests alone was insufficient if a coder could change the build script that verification executes, so executable build configuration became maintainer-owned as well.

My main takeaway was that a convincing demo is only one piece of evidence. A useful agent system also needs to show why it accepted a change, retain disagreements and failures, and continue without reconstructing its history by hand. The [reflection](artifacts/runs/readiness-20261104/reflection.md) discusses these tradeoffs and what I would change in a repeat of the project.

## Build and run locally

Prerequisites: Git, **Emscripten 4.0.18**, Python 3, **Node.js 22 or newer**, and Google Chrome for browser verification. The loop itself requires an installed and authenticated Claude Code CLI. Playing or building the game does not require Claude Code.

Clone the fork:

```sh
git clone https://github.com/adithyagsundar/fellowship-loop-capstone.git
cd fellowship-loop-capstone
```

If Emscripten is not installed, install the pinned SDK version. On macOS, install the Xcode command-line tools first with `xcode-select --install` if needed.

```sh
mkdir -p ~/Developer
git clone https://github.com/emscripten-core/emsdk.git ~/Developer/emsdk
cd ~/Developer/emsdk
./emsdk install 4.0.18
./emsdk activate 4.0.18
```

Return to this project directory, then build and verify:

```sh
source ~/Developer/emsdk/emsdk_env.sh
bash build.sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Open **http://localhost:8000**. Serve the build over HTTP rather than opening the HTML file directly. Set `CHROME_BIN` if Chrome is installed outside the locations detected by the tests.

The build creates `index.html`, `audio.js`, `doom.js`, `doom.wasm`, and `doom.data` in `dist/`. Keep all five files together when serving or deploying the game. The shareware WAD is packaged into `doom.data`.

## Run or resume the agents

After installing and authenticating Claude Code, run from the repository root:

```sh
source ~/Developer/emsdk/emsdk_env.sh
bash loop/loop.sh --verify-only       # Build and test without model calls
bash loop/loop.sh --new               # Start a new five-task run
bash loop/loop.sh                     # Resume the run in artifacts/state.json
```

For a scoped whole-port evaluation or an explicit saved run:

```sh
bash loop/loop.sh --new --tasks integration
bash loop/loop.sh --run artifacts/runs/loop-<id>
```

Live agent runs use your authenticated model account and may incur charges. Keep credentials outside the repository. See the [loop guide](loop/README.md) for recovery behavior and configuration.

## Deployment

The live site is hosted on GitHub Pages from the root of the fork's **`gh-pages`** branch. The deployed game was built from source commit `a8c8c71`; its deployment commit is `911c437`. Later documentation commits do not change those game binaries.

Deployment is manual: changes pushed to `main` do not automatically rebuild the website. To update it, build and verify the source, then publish the five `dist/` files to `gh-pages` alongside `.nojekyll`, `LICENSE`, and a `source-revision.txt` identifying the build. The November 9 [publication record](artifacts/runs/pages-20261109/README.md) includes build hashes, test output, and public asset verification.

## Repository guide

| Path | Purpose |
| --- | --- |
| `platform/` | C browser platform and audio integration |
| `web/` | Browser page and Web Audio implementation |
| `loop/` | Runner, role prompts, MCP server, configuration, and acceptance contract |
| `tests/` | Protected browser, audio, and loop verification code |
| `artifacts/` | Durable run state, handoffs, failures, results, screenshots, and reflections |
| `assets/` | Supplied shareware `doom1.wad` |
| `third_party/doomgeneric/` | Supplied Doom engine and its notices |
| `build/`, `dist/` | Generated output, excluded from the source branch |

Some folder READMEs retain the original starter instructions. The loop and verification READMEs document the implemented project. Historical source snapshots and run reports remain unchanged so their evidence can be interpreted against the revision they describe.

## Evaluation limits and provenance

The automated results establish the scope in [loop/acceptance.md](loop/acceptance.md), not every requirement of the original assignment. The two teammate/instructor-introduced blind regressions were intentionally omitted. Diagnostic fault detection is not a substitute for demonstrating autonomous repair of unknown regressions.

Manual door/switch activation, real operating-system focus transitions, and physical speaker output were not established by the saved checks. The consolidated acceptance contract was written after implementation; it does not establish that criteria existed beforehand.

The implementation and documentation include Codex-assisted work and maintainer interventions, recorded in the [intervention history](artifacts/runs/readiness-20261104/interventions.md). The evaluated loop's live role invocations used Claude Code. Manual repairs, documentation, and deployment are separate from the loop's autonomous results.

This project began from [bse-at-ucla/fellowship-loop-capstone](https://github.com/bse-at-ucla/fellowship-loop-capstone). The original assignment remains available in that repository and this fork's Git history. Preserve the engine's license notices; see [LICENSE](LICENSE) and [the engine README](third_party/doomgeneric/README.TXT). Only the supplied shareware Episode 1 WAD is included; no commercial WADs are added.
