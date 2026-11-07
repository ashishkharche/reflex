---
name: reflex-check
description: Check that iOS and Android still match and fix what doesn’t. Runs the Reflex journeys on both platforms, builds both apps, runs their unit tests and explains each failure in plain words. Use before a merge, after a change or when the user pastes a Reflex FAIL line.
license: MIT
---

# Check iOS and Android match

Run this before every merge. Runner flags: `../reflex/runner/README.md`. Result words: `../reflex/docs/add-to-your-app.md` under What you get back. Read nothing else unless a step fails.

## Steps

1. **Rebuild** each CLI the manifest points at, for example `swift build` in the harness package and the Kotlin `installDist` task.
2. **Run** `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`. One platform or Kotlin Multiplatform: pass just that one.
3. **Explain** each `FAIL` in one plain line: the screen, the action, what each platform showed. For example “Cart: Android shows 2 items, iOS shows 3, after RemoveItem.”
4. **Find the cause** and say which one it is. Label a guess as a guess.
   - The app changed on purpose. Only the user can confirm this. Then update the expected value.
   - The adapter or CLI is wrong. Fix it so it reads the real Core.
   - The app has a bug or the platforms differ. Do not change the app. Report it.
5. **Rerun** after each fix until it passes or only decisions are left. Never edit an expectation, add `parity` or `xfail` or pass `--allow-unguarded` just to go green.
6. **Build both apps and run their unit tests**, for example `xcodebuild test` and `./gradlew test`. No emulator unless asked.
7. **Check** the app’s own build files never name `../reflex`, apart from the guarded Kotlin block.
8. **Count** commits behind the main branch after `git fetch`.

## Result

| Case | Result |
| --- | --- |
| An app fails to build or a unit test fails | FAIL |
| A tool is missing or the run needs the user | BLOCKED |
| A build or unit tests could not run | INCOMPLETE |
| `PASS-UNGUARDED`, a skipped platform or a `parity` or `xfail` step | INCOMPLETE |
| A view still does the real work or a CLI starts from a made-up state | INCOMPLETE |
| Everything above passed | PASS |

## Report

One fenced `text` block with exactly these headings: Result, Needs your decision, What I added, Where it is, Try it. Result is one plain line, for example “iOS and Android match on 6 of 7 journeys.” No logs unless asked. Write “Nothing” under What I added if you added nothing. Try it holds the runner command and one next step. Write “Safe to merge” only on PASS.
