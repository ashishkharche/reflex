---
name: reflex-check
description: Check that iOS and Android still match and fix what doesn’t. Runs the Reflex journeys on both platforms, builds both apps, runs their unit tests and explains each failure in plain words. Use before a merge, after a change or when the user pastes a Reflex FAIL line.
license: MIT
---

# Check iOS and Android match

Run this before every merge. Everything you need is here. Only if a step fails, read `../reflex/runner/README.md` for runner flags or `python3 ../reflex/scripts/guide.py results` for the Result words.

Work only in the app repo and `../reflex`. Do not search home folders, other skills or other repos.

Guarded macOS CLIs get process-local UserDefaults automatically. Keep the app’s real defaults binding, not an in-memory subclass added for isolation. A failed storage sandbox blocks the run. These journeys do not test real persistence between processes. Run Swift package unit tests with `python3 ../reflex/runner/swift_tests.py <package>`; plain `swift test` is not guarded.

## Steps

1. **Handle a failure first.** If a Reflex step has failed, run `python3 ../reflex/runner/explore.py tests/reflex.json ls` before reading any app or helper code. For an action failure, include its preceding actions and failing step in that call. Read STDERR, then diagnose. Return here immediately when a later step fails.
2. **Rebuild** each CLI the manifest points at, for example `swift build` in the harness package and the Kotlin `installDist` task.
3. **Run** `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`. Platforms come from `tests/reflex.json`. One Kotlin host covers Kotlin Multiplatform or Compose Multiplatform shared logic, not the native app build and test checks. Do not ask for a Swift harness. Write the Result as “on kotlin (shared code)”.
4. **Explain** each `FAIL` in one plain line: the screen, the action, what each platform showed. For example “Cart: Android shows 2 items, iOS shows 3, after RemoveItem.”
5. **Find the cause** and say which one it is. Label a guess as a guess.
   - The app changed on purpose. Only the user can confirm this. Then update the expected value.
   - The adapter or CLI is wrong. Fix it so it reads the real Core.
   - The app has a bug or the platforms differ. Do not change the app. Report it.
6. **Rerun** after each fix until it passes or only decisions are left. Never edit an expectation, add `parity` or `xfail`, pass `--no-guard` or `--allow-unguarded` just to go green.
7. **Build each native app and run its tests**, including the iOS app in KMP projects. List the native app targets first. These checks are part of this skill even when the user only names one failure. Attempt them without asking whether to run them. Record each app’s build and test commands, exit codes and log paths in `.build/` for this session. Read suite headers with your own tools and total the counts yourself. Keep executed, skipped and failed cases separate; never run code to count results. A Kotlin shared-code suite does not count as iOS. No emulator unless asked.
8. **Check** the app’s own build files never name `../reflex`, apart from the guarded Kotlin block.
9. **Recheck coverage gaps.** Reopen each covered screen’s view and adapter. Carry forward known view-state and navigation gaps until real code and a journey prove them resolved. Recording a navigation callback does not prove the destination loaded. Check each journey runs its screen’s main action. Unresolved gaps or a journey that only touches a minor control make the screen INCOMPLETE. Name them under Needs your decision. Do not refactor unasked.
10. **Count** commits behind the main branch after `git fetch`.
11. **Commit** any fixes on the Reflex branch before reporting. Do not push unless asked.

## Rules

- Debug a CLI only through `explore.py`, which prints its error output when something fails. Never launch the CLI, `java` or a probe script yourself. Never read or write the user’s own settings (Java Preferences, UserDefaults or anything in `~/Library`). Write nothing outside the app repo and `../reflex`. No custom scripts of any kind, including inline `python -c` and heredocs. Read and search files with your own tools instead of inline Python or heredocs. Write commit messages with `git commit -m`. Keep build and test logs in the app repo’s gitignored `.build/`, never `/tmp`. Find build output there or at the repo-local path the build prints, never by searching `~/Library`. Pass `-derivedDataPath .build/ios` to every `xcodebuild` build or test command. Do not use `mdfind` or stop shared build daemons. Keep SDK diagnostics to repo files and SDK list commands. Select `JAVA_HOME` for the command and use `--no-daemon` if needed.

## Result

| Case | Result |
| --- | --- |
| An app fails to build or a unit test fails | FAIL |
| A runner tool is missing or the run needs the user for another reason | BLOCKED |
| Any native app build or tests could not run, including iOS in a KMP project | INCOMPLETE |
| `PASS-UNGUARDED`, a `parity` or `xfail` step or a listed platform the run skipped | INCOMPLETE |
| A view does the real work or holds state a user sees. Or a CLI starts from a made-up state | INCOMPLETE |
| A journey skips its screen’s main action | INCOMPLETE |
| Everything above passed | PASS |

## Report

Copy this shape. One fenced `text` block, five headings in this order, 19 lines at most counting blank lines. Count them before you send. Use curly apostrophes. No Oxford commas or em dashes.

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
- PASS requires current-session evidence that every platform in `tests/reflex.json` passed and each native app separately built and passed its tests, with no uncommitted changes. This includes the iOS app in KMP projects. A Kotlin shared-code suite is not iOS evidence. Tests must execute in this session. `FROM-CACHE`, `UP-TO-DATE`, `NO-SOURCE` or `SKIPPED` test tasks do not count. Use `--rerun --no-build-cache` on each Gradle test task and verify fresh test counts and timestamps. A missing native app build or test run makes the Result INCOMPLETE: name the app under Needs your decision and never say merge in Next.
- Commit changed code on `reflex/<screen>` before reporting. Never include unrelated changes or push unless asked. Where it is names the committed work, never “uncommitted”. If the commit cannot be made, report BLOCKED and say why under Needs your decision.
- Needs your decision is a numbered list with one short line each. Write “None” if empty. Every reason the Result is not PASS goes here.
- The Next line follows the Result word. PASS: “Next: merge reflex/<screen>, then /reflex-cover <next screen>”. Anything else: “Next: answer 1, then /reflex-check”. Never say merge before PASS.
- At most three decisions. Join related ones into one line. Nothing goes outside the block.
- Fixes count as added files. No extra merge claim or logs. The Next line is the last line.
