---
name: reflex-start
description: Add Reflex to your iOS and Android app and get your first screen under test. It also updates Reflex in an app that has it. Use when the user asks to add, install, set up, start, upgrade or update Reflex.
license: MIT
---

# Start with Reflex

Reflex lets an agent drive and test the app’s ViewModels without a simulator, with one test file for iOS and Android. Shopify’s words: share the test, not the code. This skill gets one screen there, then stops.

Work only in the app repo and `../reflex`. Do not search home folders, other skills or other repos.

Guarded macOS CLIs get process-local UserDefaults automatically. Keep the app’s real defaults binding, not an in-memory subclass added for isolation. A failed storage sandbox blocks the run. These journeys do not test real persistence between processes. Run Swift package unit tests with `python3 ../reflex/runner/swift_tests.py <package>`; plain `swift test` is not guarded.

## Steps

1. **Handle a failure first.** If a Reflex step has failed, run `python3 ../reflex/runner/explore.py tests/reflex.json ls` before reading any app or helper code. For an action failure, include its preceding actions and failing step in that call. Read STDERR, then diagnose. Return here immediately when a later step fails.
2. **Check the repo.** You must be in the app’s repo, not in Reflex. If it has uncommitted changes, ask before you start. Never stash or discard them.
3. **Check the stack.**
   - Native Swift and Kotlin: carry on.
   - Kotlin Multiplatform or Compose Multiplatform: one Kotlin host covers the shared logic. List only `kotlin` in `tests/reflex.json`.
   - Flutter, React Native, Expo, .NET MAUI or another stack: stop with BLOCKED. Reflex has no kit for it yet.
   - Only one platform here: ask whether the app has the other one and where its repo is.
4. **Check the tools.** `git`, `python3`, `clang` or `cc`, `java -version` 17 or newer for Kotlin and `xcodebuild -version` with Swift 6.0 or newer for Swift. Swift needs macOS. Windows needs WSL 2. A missing native app build or test tool makes that app INCOMPLETE. So does a Gradle toolchain the build asks for that is not installed, such as JDK 17: name the version to install. Other missing tools: stop with BLOCKED and name what to install.
5. **Get Reflex** next to the app as `../reflex`. Not there: `git clone https://github.com/ashishkharche/reflex.git ../reflex`. Never put it inside the app repo. Already there: this is an update. Note its commit, then `git -C ../reflex pull`.
6. **Read the guide with the helper, never the whole file.** First setup: `python3 ../reflex/scripts/guide.py 2 3 4 5 7`, leaving out 2 (Swift) or 3 (Kotlin) when the app lacks that platform. Update: `python3 ../reflex/scripts/guide.py update`. Read the rest of a section only when a step fails.
7. **Pick the first screen and check it is ready.** Choose the main screen and name its main action, the one the screen exists for, such as Complete, Save or Checkout.
   - Its state must live in a ViewModel or shared Core, not in the views. If it lives in the views, stop with BLOCKED and ask before any refactor.
   - Open the screen’s view file too. A value a user sees or changes that lives there (`remember`, `rememberPagerState`, `@State`, a local variable) is a readiness gap even when the main action is in the ViewModel. Name it under Needs your decision and make the Result INCOMPLETE. Do not refactor unasked.
   - Every network call that action makes needs a fixture. If one can’t be faked without changing app code, stop with BLOCKED and say which call.
8. **Branch** from the latest main branch: `git symbolic-ref --short refs/remotes/origin/HEAD`. With no remote, use the current branch. Name it `reflex/<screen>`.
9. **First setup:** one adapter per platform, one CLI per platform, `tests/reflex.json` and one journey that runs the main action.
   **Update:** read `../reflex/CHANGELOG.md` from the noted commit and apply each entry to the Reflex files the app has.
10. **Prove the main action** before you write the journey: `python3 ../reflex/runner/explore.py tests/reflex.json 'do <MainAction> {...}'`. `NETWORK denied` means a call still has no fixture. Fix that first. A journey that skips the main action is INCOMPLETE.
11. **Check** with the `reflex-check` steps. One build and one test run per native app is enough here, including iOS in KMP projects.
12. **Commit** on the branch. Do not push unless the user asks.
13. **Report and stop.** Do not start another screen.

## Rules

- Keep Reflex out of the app build. Swift harness code goes in its own package, for example `ReflexHarness/`. Kotlin uses the guarded `settings.gradle.kts` block, the only app file you may edit without asking.
- Every adapter wraps the app’s real Core. Never copy its rules into an adapter or CLI.
- A CLI loads the same state the app shows. Ask before any refactor and stop after it.
- Never make one platform match the other here. That is a product change: ask, then do it on its own branch.
- Never turn the network guard off to get a run through.
- Platforms come from `tests/reflex.json`. One Kotlin host covers Kotlin Multiplatform or Compose Multiplatform shared logic, not the native app build and test checks. Do not ask for a Swift harness. Write the Result as “on kotlin (shared code)”.
- Dry run or plan: change nothing. Reading and the tool check are fine. Report INCOMPLETE with the reason “dry run”.
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
- tests/reflex.json and tests/journeys/home.json
- HomeNode and home-cli (Swift and Kotlin)

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
- No extra merge claim or logs. The Next line is the last line.
