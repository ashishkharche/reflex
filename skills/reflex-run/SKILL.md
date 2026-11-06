---
name: reflex-run
description: Rebuild and rerun an app’s Reflex journeys, explain any FAIL line in plain words and update expected values only for intentional behaviour changes. Use when the user asks to run, rerun or fix Reflex tests. Also use it when the user pastes a Reflex FAIL or RESULT line.
license: MIT
---

# Run Reflex and explain the result

The Reflex clone sits next to the app, usually `../reflex`. Runner flags are in `../reflex/runner/README.md`. Result words and the report are in `../reflex/docs/add-to-your-app.md` under What you get back.

## Steps

1. Rebuild each CLI the manifest points at: the Swift executable and the Kotlin `installDist` task, as the guide shows.
2. Run `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`, with the app’s manifest path. If the app has one platform, pass just that one.
3. For each `FAIL` line, say in plain words which journey and step failed, which action was sent, what was expected and what came back.
4. Decide which of these it is and say why:
   - The app changed on purpose. Only the user can confirm this. A change they asked for in this session also counts.
   - The adapter or CLI is wrong. Fix it so it reads the real Core.
   - The app has a bug or the platforms differ. Do not change the app. Report it.
5. Update an expected value only in the first case. Never edit an expectation or pass `--allow-unguarded` just to turn a run green. Do not add `xfail` or `parity` for that either.
6. Rerun after each fix until the run passes or only decisions are left.

## Result

Use the guide’s Result words. A green runner line is not enough for PASS. `PASS-UNGUARDED`, a skipped platform or a step marked `parity` or `xfail` makes it INCOMPLETE.

## Report

Reply with the five-part report from the guide, in one fenced `text` block. Try it holds the exact runner command.
