# Evidence-based reflection

Prepared from repository evidence by the submission-preparation assistant.
The student should review this factual account and add their own rationale
and proposed design change before handing it in. This is not a claim of
student authorship or a completed architecture reflection.

The strongest evidence is behavioral. Browser checks exercise menu input,
movement, turning, ammunition consumption, and Web Audio output, rather than
accepting compilation or a screenshot alone. Three diagnostic faults were
caught: suppressed keyboard input, a blank framebuffer, and silent effects.
See ../evaluation-20261105T000431Z/fault-checks.json. These experiments show
that those checks can detect particular failures; they do not demonstrate
repair of undisclosed regressions.

Separate review and tester reports exist, but the integration tester
explicitly relied on saved results and code inspection. Fresh execution is
recorded separately in this submission-preparation run and must not be
attributed to that earlier tester invocation. Likewise, unchanged tests do
not prove that coder permissions prevented test edits.

Interruption/resumption evidence shows completed tasks being skipped and an
unfinished task restarting with fresh context. The evaluation also records
premature completion messages and manual restarts to finish subsequent tasks.
That limits any claim of end-to-end autonomy. See
../evaluation-20261105T000431Z/evaluation.json and its linked logs.

The port checks leave real gaps: use-key delivery is not proof that a door
opens; synthetic blur is not a real OS focus change; nonzero audio samples do
not prove speaker output or fidelity. Save persistence and mouse aiming are
not available in the reviewed port. Music uses simplified instruments.

Manual interventions in the previous evaluation included launching and
restarting the existing process, deliberately interrupting it, preserving
snapshots, updating documentation, and running diagnostic faults. This
submission-preparation pass adds documentation, direct build/test execution,
and evidence packaging. Neither pass supplies the required two blind
teammate/instructor regressions. Actual historical token/cost totals are
unknown and are not reconstructed from guesses.

Student-owned reflection still required: explain the rationale for the
chosen roles and authority boundaries; discuss any observed disagreements;
and identify a design choice you would change based on the evidence.
