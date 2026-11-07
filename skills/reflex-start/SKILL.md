---
name: reflex-start
description: Add Reflex to your iOS and Android app and get your first screen under test. It also updates Reflex in an app that has it. Use when the user asks to add, install, set up, start, upgrade or update Reflex.
license: MIT
---

# Start with Reflex

Reflex lets an agent drive and test the app’s ViewModels without a simulator, with one test file for iOS and Android. Shopify’s words: share the test, not the code. This skill gets one screen there, then stops.

Work only in the app repo and `../reflex`. Do not search home folders, other skills or other repos.

## Steps

1. **Check the repo.** You must be in the app’s repo, not in Reflex. If it has uncommitted changes, ask before you start. Never stash or discard them.
2. **Check the stack.**
   - Native Swift and Kotlin: carry on.
   - Kotlin Multiplatform or Compose Multiplatform: one Kotlin host covers the shared logic. List only `kotlin` in `tests/reflex.json`.
   - Flutter, React Native, Expo, .NET MAUI or another stack: stop with BLOCKED. Reflex has no kit for it yet.
   - Only one platform here: ask whether the app has the other one and where its repo is.
3. **Check the tools.** `git`, `python3`, `clang` or `cc`, `java -version` 17 or newer for Kotlin and `xcodebuild -version` with Swift 6.0 or newer for Swift. Swift needs macOS. Windows needs WSL 2. Missing one: stop with BLOCKED and name what to install.
4. **Get Reflex** next to the app as `../reflex`. Not there: `git clone https://github.com/ashishkharche/reflex.git ../reflex`. Never put it inside the app repo. Already there: this is an update. Note its commit, then `git -C ../reflex pull`.
5. **Read the guide with the helper, never the whole file.** First setup: `python3 ../reflex/scripts/guide.py 2 3 4 5 7`, leaving out 2 (Swift) or 3 (Kotlin) when the app lacks that platform. Update: `python3 ../reflex/scripts/guide.py update`. Read the rest of a section only when a step fails.
6. **Pick the first screen and check it is ready.** Choose the main screen and name its main action, the one the screen exists for, such as Complete, Save or Checkout.
   - Its state must live in a ViewModel or shared Core, not in the views. If it lives in the views, stop with BLOCKED and ask before any refactor.
   - Open the screen’s view file too. A value a user sees or changes that lives there (`remember`, `rememberPagerState`, `@State`, a local variable) is a readiness gap even when the main action is in the ViewModel. Name it under Needs your decision and make the Result INCOMPLETE. Do not refactor unasked.
   - Every network call that action makes needs a fixture. If one can’t be faked without changing app code, stop with BLOCKED and say which call.
7. **Branch** from the latest main branch: `git symbolic-ref --short refs/remotes/origin/HEAD`. With no remote, use the current branch. Name it `reflex/<screen>`.
8. **First setup:** one adapter per platform, one CLI per platform, `tests/reflex.json` and one journey that runs the main action.
   **Update:** read `../reflex/CHANGELOG.md` from the noted commit and apply each entry to the Reflex files the app has.
9. **Prove the main action** before you write the journey: `python3 ../reflex/runner/explore.py tests/reflex.json 'do <MainAction> {...}'`. `NETWORK denied` means a call still has no fixture. Fix that first. A journey that skips the main action is INCOMPLETE.
10. **Check** with the `reflex-check` steps. One build and one unit test run per platform is enough here.
11. **Commit** on the branch. Do not push unless the user asks.
12. **Report and stop.** Do not start another screen.

## Rules

- Keep Reflex out of the app build. Swift harness code goes in its own package, for example `ReflexHarness/`. Kotlin uses the guarded `settings.gradle.kts` block, the only app file you may edit without asking.
- Every adapter wraps the app’s real Core. Never copy its rules into an adapter or CLI.
- A CLI loads the same state the app shows. Ask before any refactor and stop after it.
- Never make one platform match the other here. That is a product change: ask, then do it on its own branch.
- Never turn the network guard off to get a run through.
- Platforms come from `tests/reflex.json`. A Kotlin Multiplatform or Compose Multiplatform app with only a Kotlin host is complete. Do not ask for a Swift harness. Write the Result as “on kotlin (shared code)”.
- Dry run or plan: change nothing. Reading and the tool check are fine. Report INCOMPLETE with the reason “dry run”.

## Report

Copy this shape. One fenced `text` block, five headings in this order, 19 lines at most counting blank lines. Count them before you send.

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
- Needs your decision is a numbered list with one short line each. Write “None” if empty. Every reason the Result is not PASS goes here.
- The Next line follows the Result word. PASS: “Next: merge reflex/<screen>, then /reflex-cover <next screen>”. Anything else: “Next: answer 1, then /reflex-check”. Never say merge before PASS.
- At most three decisions. Join related ones into one line. Nothing goes outside the block.
- Write “Safe to merge” after the Next line only on PASS. No logs unless asked.
