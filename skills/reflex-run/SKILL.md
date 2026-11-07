---
name: reflex-run
description: Rebuild and rerun an app’s Reflex journeys, build the apps and run their unit tests, explain any FAIL line in plain words and update expected values only for intentional behaviour changes. Use when the user asks to run, rerun or fix Reflex tests. Also use it when the user pastes a Reflex FAIL or RESULT line.
license: MIT
---

# Run Reflex and explain the result

The Reflex clone sits next to the app, usually `../reflex`. Runner flags are in `../reflex/runner/README.md`. The app checks are in `../reflex/docs/add-to-your-app.md` under 9. Check the app still works. Result words and the report are under What you get back.

## Steps

1. Rebuild each CLI the manifest points at: the Swift executable and the Kotlin `installDist` task, as the guide shows.
2. Run `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`, with the app’s manifest path. If the app has one platform or a Kotlin Multiplatform host, pass just that one.
3. For each `FAIL` line, say in plain words which journey and step failed, which action was sent, what was expected and what came back.
4. Decide which of these it is and say why:
   - The app changed on purpose. Only the user can confirm this. A change they asked for in this session also counts.
   - The adapter or CLI is wrong. Fix it so it reads the real Core.
   - The app has a bug or the platforms differ. Do not change the app. Report it.
5. Update an expected value only in the first case. Never edit an expectation or pass `--allow-unguarded` just to turn a run green. Do not add `xfail` or `parity` for that either.
6. Rerun after each fix until the run passes or only decisions are left.
7. Build each app and run its existing unit tests, for example `xcodebuild test` and `./gradlew test`. Do not start an emulator for instrumented tests unless the user asks.
8. Check that the app’s own build files never name `../reflex`, apart from the guarded Kotlin block. Use the `git grep` lines in the guide.
9. Run `git fetch` and count the commits behind the main branch for Where it is. The main branch is whatever `git symbolic-ref --short refs/remotes/origin/HEAD` names, not always `main`.

## Result

Use the guide’s Result words. A green runner line is not enough for PASS.

| Case | Result |
| --- | --- |
| An app fails to build or a unit test fails | FAIL |
| An app build or its unit tests could not run | INCOMPLETE |
| A screen’s view still does the real work | INCOMPLETE |
| `PASS-UNGUARDED`, a skipped platform or a step marked `parity` or `xfail` | INCOMPLETE |
| A CLI starts from an empty or made-up state the app fills in elsewhere | INCOMPLETE |
| A tool the run needs is missing, such as Xcode, a JDK or Python 3 | BLOCKED |

## Report

Reply with the report from the guide, in one fenced `text` block, with exactly these five headings in this order: Result, Needs your decision, What I added, Where it is, Try it. Never rename one. If you added nothing, write “Nothing” under What I added. Try it holds the exact runner command.
