# Reflection: evidence matters more than a completion message

My main lesson from this project is that getting DOOM to run in a browser and
building a trustworthy agent loop are different achievements. The port has useful
behavioral evidence: it loads the supplied WAD and WebAssembly, renders a running
level, responds to movement and turning, consumes ammunition when firing, and
produces measurable sound and music samples. Those results are substantially
stronger than a successful compile or a screenshot. They still do not prove that
the system can independently recover from an unfamiliar regression.

The strongest part of the verification approach was testing consequences of
input rather than accepting descriptions of intended behavior. Movement checks
observe changes in world position; shooting checks observe ammunition; audio
checks measure nonzero samples. Deliberately suppressing input, blanking the
framebuffer and silencing effects produced the expected failures in the saved
evaluation. This gives concrete reasons to trust those particular checks. It
does not justify treating the test suite as complete.

The most instructive failure was in the orchestration itself. The earlier loop
printed its automated completion message while later tasks were still unfinished.
Manual restarts were required to complete the remaining work. That means the
original completion marker could not be treated as evidence of end-to-end
autonomy. It also illustrates why the loop needs its own tests: a working game can
hide a broken coordinator. The replacement runner enumerates tasks in Python,
closes child stdin, stores unique attempt directories, checks structured handoffs,
and distinguishes success, exhaustion, stalling and interruption. Closing stdin
addresses a plausible explanation for the shell-loop failure; the historical
logs alone do not prove that explanation was the sole cause.

The three roles have different reasons to exist. The coder proposes changes and
explains them. The reviewer asks whether those changes are correct and whether
the task's requirements have been overlooked. The tester supplies execution
evidence independent of the coder's account. A reviewer disagreement should not
be erased by passing tests, because tests cover only what their assertions
observe. Conversely, a persuasive report should not erase a reproducible failure.
The replacement loop requires both review approval and fresh verification. The live readiness run produced a concrete evidence disagreement: the build
reviewer withheld PASS because no successful execution was available, while the
following tester generated a source-matched passing build and test result. The
next review accepted that evidence. The loop did not erase the earlier FAIL or
let the tester overrule it within the same cycle. This was a useful gate, though
it also exposed the cost of asking for build approval before the first tester
result exists. A future design could run a baseline verification before review.

Authority was another weakness in the earlier design. A YAML list of forbidden
paths is documentation, not enforcement. The new MCP interface narrows the
coder's writes to port source and protects tests, orchestration, assets and build
scripts. The tester gets a fixed verification tool and cannot submit PASS without
fresh matching evidence. Build scripts remain human-owned because allowing an
agent to replace a script that the verifier executes would undermine the boundary.
This is a deliberate tradeoff: some build repairs now require an explicitly
recorded maintainer intervention. These tool restrictions are not a substitute
for an operating-system sandbox against deliberately malicious generated code.

Durable evidence also changes the meaning of resumption. Restarting should not
mean reconstructing the story from a chat or overwriting a failed attempt. The
runner stores the task, prior findings, source hashes, usage and stopping status
under artifacts/. Incomplete attempts remain visible, and source changes
invalidate stale completion. Unknown interrupted usage is conservatively reserved
rather than silently counted as zero. The original run's historical costs remain
unknown; new instrumentation cannot recover them retrospectively.

There are clear limits to this submission. Use-key delivery does not prove that
a door opens. Synthetic blur does not establish real operating-system focus
behavior, and Web Audio samples do not prove what a listener hears. Simplified
music synthesis is not a fidelity claim. The two required teammate/instructor
blind regression repairs were intentionally omitted at the user's direction.
The diagnostic faults must not be relabeled as that exercise, and the submission
must remain marked incomplete against the full assignment rubric. I also cannot
establish that the later consolidated acceptance document existed before the port.

The design choice I would change earliest in a repeat of this project is to make
the evidence contract and authority boundary executable before asking agents to
implement the game. I would first test that the coder cannot change acceptance
checks, that stale evidence cannot pass a task, and that an interrupted failing
run resumes without losing its history. Then I would plan the independent blind
regression exercise while there is still time to perform it. That order would
make the evaluation part of the system's design instead of a final documentation
step after a convincing demo already exists.
