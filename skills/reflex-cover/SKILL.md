---
name: reflex-cover
description: Cover a screen or feature with one Reflex test that runs on iOS and Android. Use when the user asks to test a screen, add a screen or feature to Reflex, cover the whole app or asks which screens Reflex can test.
license: MIT
---

# Cover a screen

One screen per run, one branch per screen. The app needs `tests/reflex.json` first. No manifest: use `reflex-start` instead. The last Reflex branch must already be merged. This skill does not merge branches.

Work only in the app repo and `../reflex`. Do not search home folders, other skills or other repos.

Guarded macOS CLIs get process-local UserDefaults automatically. Keep the app’s real defaults binding, not an in-memory subclass added for isolation. A failed storage sandbox blocks the run. These journeys do not test real persistence between processes. Run Swift package unit tests with `python3 ../reflex/runner/swift_tests.py <package>`; plain `swift test` is not guarded.

## Steps

1. **Handle a failure first.** If a Reflex step has failed, run `python3 ../reflex/runner/explore.py tests/reflex.json ls` before reading any app or helper code. For an action failure, include its preceding actions and failing step in that call. Read STDERR, then diagnose. Return here immediately when a later step fails.
2. **Check setup and pick the screen.** Confirm the last Reflex branch is already merged into main. If not, stop with INCOMPLETE and name that prerequisite. A cover request is not merge approval. Never merge an INCOMPLETE branch. If the user named a screen, use it. Otherwise list the screens with their ViewModel on iOS and Android side by side. Mark one-platform screens and screens that keep state in their views. Ask which to do. “The whole app” means this list, one screen at a time.
3. **Check it is ready.** Name its main action, the one the screen exists for.
   - State in the views or no ViewModel: stop and ask. Do not refactor unasked. A harness-owned copy of view state, even a second instance of a real helper, does not make it ready.
   - Open the screen’s view file too. A value a user sees or changes that lives there (`remember`, `rememberPagerState`, `@State`, a local variable) is a readiness gap even when the main action is in the ViewModel. Name it under Needs your decision and make the Result INCOMPLETE. Do not refactor unasked.
   - Every network call that action makes needs a fixture. If one can’t be faked without changing app code, stop with BLOCKED and say which call.
4. **Branch** from the latest main branch (`git symbolic-ref --short refs/remotes/origin/HEAD`), for example `reflex/settings`.
5. **Read** `python3 ../reflex/scripts/guide.py 4 5 7`, never the whole guide. Copy the shape of the adapters the app already has.
6. **Add** an adapter on each platform with the same node name and action names. Use the same state keys when the code allows. If the apps name a fact differently, such as `isRunning` and `started`, keep the real names and add a `stateKeys` map to `tests/reflex.json` (guide section 7). List a key only one app has under `only`. Wire the adapter into each CLI.
7. **Prove the main action:** `python3 ../reflex/runner/explore.py tests/reflex.json 'do <MainAction> {...}'`. `NETWORK denied` means a call still has no fixture. Fix that first.
8. **Add one journey** in the existing journeys folder that runs the main action. Fold the steps of one user journey into one test. Keep a separate journey only when it needs different fixtures.
9. **Check** with the `reflex-check` steps.
10. **Commit** on the branch. Do not push unless asked.
11. **Report and stop.** Wait for a yes before the next screen.

## Rules

- Same rules as `reflex-start`: wrap the real Core, keep Reflex out of the app build, ask before editing other app files, never hide a platform difference and never make one platform match the other here.
- If a user can see it, it is in state. If a user can do it, it is an action. The node lists every action every time, with no conditionals.
- A CLI loads the same state the app shows. An empty or made-up start state makes the screen INCOMPLETE.
- A journey that skips the main action makes the screen INCOMPLETE.
- Platforms come from `tests/reflex.json`. One Kotlin host covers Kotlin Multiplatform or Compose Multiplatform shared logic, not the native app build and test checks. Do not ask for a Swift harness. Write the Result as “on kotlin (shared code)”.
- Run every build and test in the foreground and wait for it to finish. Give each one a long enough wait, such as 20 minutes, so it can’t move to the background. If one moves there anyway, wait on it and do nothing else until it ends. Never start a background job or task. Run one native app build at a time, Android first, then iOS. The report is your final message: send nothing after it, not even a status line.
- Debug a CLI only through `explore.py`, which prints its error output when something fails. Never launch the CLI, `java` or a probe script yourself. Never read or write the user’s own settings (Java Preferences, UserDefaults or anything in `~/Library`). Write nothing outside the app repo and `../reflex`. No custom scripts of any kind, including inline `python -c` and heredocs. Read and search files with your own tools instead of inline Python or heredocs. Write commit messages with `git commit -m`. Keep build and test logs in the app repo’s gitignored `.build/`, never `/tmp`. Find build output there or at the repo-local path the build prints, never by searching `~/Library`. Pass `-derivedDataPath .build/ios` to every `xcodebuild` command, including `-list` and `-showBuildSettings`, which resolve packages too. Do not use `mdfind` or stop shared build daemons. Keep SDK diagnostics to repo files and SDK list commands. Select `JAVA_HOME` for the command (on macOS `/usr/libexec/java_home -v <version>`) and use `--no-daemon` if needed. In Kotlin Multiplatform apps, run `xcodebuild` with `GRADLE_OPTS=-Dorg.gradle.daemon=false` so its Gradle step leaves no daemon running.

## Report

Copy this shape. One fenced `text` block, five headings in this order, 19 lines at most counting blank lines. Count them before you send. Use curly apostrophes. No Oxford commas or em dashes.

```text
Result
PASS on swift and kotlin. Both apps build and pass unit tests.

Needs your decision
None

What I added
- tests/reflex.json and tests/journeys/settings.json
- SettingsNode, wired into both CLIs (Swift and Kotlin)

Where it is
reflex/settings at abc1234, not pushed, 0 behind main

Try it
python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both
Next: merge reflex/settings, then /reflex-cover <next screen>
```

- Result is one line: the Result word, the platforms and the build and unit test outcome.
- PASS requires current-session evidence that every platform in `tests/reflex.json` passed and each native app separately built and passed its tests, with no uncommitted changes. This includes the iOS app in KMP projects. A Kotlin shared-code suite is not iOS evidence. Tests must execute in this session. `FROM-CACHE`, `UP-TO-DATE`, `NO-SOURCE` or `SKIPPED` test tasks do not count. Use `--rerun --no-build-cache` on each Gradle test task and verify fresh test counts and timestamps. A missing native app build or test run makes the Result INCOMPLETE: name the app under Needs your decision and never say merge in Next.
- Commit changed code on `reflex/<screen>` before reporting. Never include unrelated changes or push unless asked. Where it is names the committed work, never “uncommitted”. If the commit cannot be made, report BLOCKED and say why under Needs your decision.
- Needs your decision is a numbered list with one short line each. Write “None” if empty. Every reason the Result is not PASS goes here.
- The Next line follows the Result word. PASS: “Next: merge reflex/<screen>, then /reflex-cover <next screen>”. Anything else: “Next: answer 1, then /reflex-check”. Never say merge before PASS.
- At most three decisions. Join related ones into one line. Nothing goes outside the block.
- No extra merge claim or logs. The Next line is the last line.
