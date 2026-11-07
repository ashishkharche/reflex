---
name: reflex-check
description: Check that iOS and Android still match and fix what doesn’t. Runs the Reflex journeys on both platforms, builds both apps, runs their unit tests and explains each failure in plain words. Use before a merge, after a change or when the user pastes a Reflex FAIL line.
license: MIT
---

# Check iOS and Android match

Run this before every merge. Everything you need is here. Only if a step fails, read `../reflex/runner/README.md` for runner flags or `python3 ../reflex/scripts/guide.py results` for the Result words.

Work only in the app repo and `../reflex`. Do not search home folders, other skills or other repos.

## Steps

1. **Rebuild** each CLI the manifest points at, for example `swift build` in the harness package and the Kotlin `installDist` task.
2. **Run** `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`. One platform or Kotlin Multiplatform: pass just that one.
3. **Explain** each `FAIL` in one plain line: the screen, the action, what each platform showed. For example “Cart: Android shows 2 items, iOS shows 3, after RemoveItem.”
4. **Find the cause** and say which one it is. Label a guess as a guess.
   - The app changed on purpose. Only the user can confirm this. Then update the expected value.
   - The adapter or CLI is wrong. Fix it so it reads the real Core.
   - The app has a bug or the platforms differ. Do not change the app. Report it.
5. **Rerun** after each fix until it passes or only decisions are left. Never edit an expectation, add `parity` or `xfail`, pass `--no-guard` or `--allow-unguarded` just to go green.
6. **Build both apps and run their unit tests**, for example `xcodebuild test` and `./gradlew test`. No emulator unless asked.
7. **Check** the app’s own build files never name `../reflex`, apart from the guarded Kotlin block.
8. **Check each journey runs its screen’s main action.** One that only touches a minor control makes that screen INCOMPLETE.
9. **Count** commits behind the main branch after `git fetch`.

## Result

| Case | Result |
| --- | --- |
| An app fails to build or a unit test fails | FAIL |
| A tool is missing or the run needs the user | BLOCKED |
| A build or unit tests could not run | INCOMPLETE |
| `PASS-UNGUARDED`, a skipped platform or a `parity` or `xfail` step | INCOMPLETE |
| A view still does the real work or a CLI starts from a made-up state | INCOMPLETE |
| A journey skips its screen’s main action | INCOMPLETE |
| Everything above passed | PASS |

## Report

Copy this shape. One fenced `text` block, five headings in this order, under 20 lines. Count them before you send.

```text
Result
PASS on swift and kotlin. Both apps build and pass unit tests.

Needs your decision
None

What I added
- Nothing

Where it is
reflex/home at abc1234, not pushed, 0 behind main

Try it
python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both
Next: merge reflex/home, then /reflex-cover <next screen>
```

- Result is one line: the Result word, the platforms and the build and unit test outcome.
- Needs your decision is a numbered list with one short line each. Write “None” if empty. Every reason the Result is not PASS goes here.
- Fixes count as added files. Write “Safe to merge” after the Next line only on PASS. No logs unless asked.
