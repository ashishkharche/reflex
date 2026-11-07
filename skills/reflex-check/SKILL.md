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
2. **Run** `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`. Platforms come from `tests/reflex.json`. A Kotlin Multiplatform or Compose Multiplatform app with only a Kotlin host is complete. Do not ask for a Swift harness. Write the Result as “on kotlin (shared code)”.
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
10. **Commit** any fixes on the Reflex branch before reporting. Do not push unless asked.

## Rules

- When a step fails, run `python3 ../reflex/runner/explore.py tests/reflex.json` with the failing step first and read its STDERR before reading code.
- Debug a CLI only through `explore.py`, which prints its error output when something fails. Never launch the CLI, `java` or a probe script yourself. Never read or write the user’s own settings (Java Preferences, UserDefaults or anything in `~/Library`). Write nothing outside the app repo and `../reflex`. No custom scripts of any kind, including inline `python -c` and heredocs. Use your own read and search tools. Keep build and test logs in the app repo’s `.build/` and ensure it is gitignored, never `/tmp`.

## Result

| Case | Result |
| --- | --- |
| An app fails to build or a unit test fails | FAIL |
| A tool is missing or the run needs the user | BLOCKED |
| A build or unit tests could not run | INCOMPLETE |
| `PASS-UNGUARDED`, a `parity` or `xfail` step or a listed platform the run skipped | INCOMPLETE |
| A view does the real work or holds state a user sees. Or a CLI starts from a made-up state | INCOMPLETE |
| A journey skips its screen’s main action | INCOMPLETE |
| Everything above passed | PASS |

## Report

Copy this shape. One fenced `text` block, five headings in this order, 19 lines at most counting blank lines. Count them before you send.

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
- PASS requires every platform in `tests/reflex.json` to pass in this session, every app to build and pass its unit tests in this session and no uncommitted changes. Otherwise report INCOMPLETE and name each platform or check that did not run.
- Commit changed code on `reflex/<screen>` before reporting. Never include unrelated changes or push unless asked. Where it is names the committed work, never “uncommitted”. If the commit cannot be made, report BLOCKED and say why under Needs your decision.
- Needs your decision is a numbered list with one short line each. Write “None” if empty. Every reason the Result is not PASS goes here.
- The Next line follows the Result word. PASS: “Next: merge reflex/<screen>, then /reflex-cover <next screen>”. Anything else: “Next: answer 1, then /reflex-check”. Never say merge before PASS.
- At most three decisions. Join related ones into one line. Nothing goes outside the block.
- Fixes count as added files. No extra merge claim or logs. The Next line is the last line.
