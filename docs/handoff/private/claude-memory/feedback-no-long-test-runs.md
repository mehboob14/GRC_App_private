---
name: feedback-no-long-test-runs
description: Never run long checks (the full backend suite takes about an hour) or sit waiting on them; run short targeted checks and ask the user to run anything longer
metadata:
  node_type: memory
  type: feedback
  originSessionId: 37ba6ded-4a2f-415c-80dc-7faaa8c93b1b
  modified: 2026-10-07T17:30:25.719Z
---

Do not run long verification yourself. The full Verity backend suite is 1,500+ tests and takes about an hour; waiting on it (and polling it) burned tokens and made the user wait, and on 2026-10-07 they interrupted it ("been a while since running", "don't run these type of long checks in future, ask me to run if longer, for token optimization").

**Why:** token cost and the user's time. They would rather run a long check themselves, or accept a short targeted one, than watch me poll for an hour.

**How to apply:**
- Use short checks I can finish in a few minutes: ruff, mypy, import-linter, `tsc -p tsconfig.app.json`, eslint, and targeted pytest files or `-k` selections for the code I touched (unit tests are about 15 seconds; one integration file is 1 to 3 minutes).
- If something longer is warranted (the whole suite, an isolation sweep, a long browser run), do not start it in the background and wait. Say what the command is and ask the user to run it, then carry on with the rest.
- Say plainly what was and was not run, so the user can decide whether to run the long one before deploying.

Related: [[feedback-speed-and-standout-copy]], [[verity-tests-wipe-database]].
