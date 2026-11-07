---
name: reflex-start
description: Add Reflex to your iOS and Android app and get your first screen under test. It also updates Reflex in an app that has it. Use when the user asks to add, install, set up, start, upgrade or update Reflex.
license: MIT
---

# Start with Reflex

Reflex lets an agent drive and test the app’s ViewModels without a simulator, with one test file for iOS and Android. Shopify’s words: share the test, not the code. This skill gets one screen there, then stops.

## Steps

1. **Check the repo.** You must be in the app’s repo, not in Reflex. If it has uncommitted changes, ask before you start. Never stash or discard them.
2. **Check the stack.**
   - Native Swift and Kotlin: carry on.
   - Kotlin Multiplatform or Compose Multiplatform: one Kotlin host covers the shared logic. Use `--platform kotlin`.
   - Flutter, React Native, Expo, .NET MAUI or another stack: stop with BLOCKED. Reflex has no kit for it yet. A host that speaks protocol v1 is needed.
   - Only one platform here: ask whether the app has the other one and where its repo is.
3. **Check the tools.** `git`, `python3`, `clang` or `cc`, `java -version` 17 or newer for Kotlin and `xcodebuild -version` with Swift 6.0 or newer for Swift. Swift needs macOS. Windows needs WSL 2. Missing one: stop with BLOCKED and name what to install.
4. **Get Reflex** next to the app, for example `../reflex`. Not there: `git clone https://github.com/ashishkharche/reflex.git ../reflex`. Never put it inside the app repo. Already there: this is an update. Note its commit, then `git -C ../reflex pull`.
5. **Read only what you need** from `../reflex/docs/add-to-your-app.md`: For AI assistants, then 2 or 3 for each platform the app has, then 4, 5 and 7. Skip the rest.
6. **Branch** from the latest main branch. Find it with `git symbolic-ref --short refs/remotes/origin/HEAD`. With no remote, use the current branch. Name it `reflex/<screen>`.
7. **First setup:** cover the main screen only. One adapter per platform, one CLI per platform, `tests/reflex.json` and one journey.
   **Update:** read `../reflex/CHANGELOG.md` from the noted commit and apply each entry to the Reflex files the app has.
8. **Check** with the `reflex-check` steps: the journeys, both app builds and their unit tests.
9. **Commit** on the branch. Do not push unless the user asks.
10. **Report and stop.** Do not start another screen.

## Rules

- Keep Reflex out of the app build. Swift harness code goes in its own package, for example `ReflexHarness/`. Kotlin uses the guarded `settings.gradle.kts` block, the only app file you may edit without asking.
- Every adapter wraps the app’s real Core. Never copy its rules into an adapter or CLI.
- A CLI loads the same state the app shows. Ask before any refactor and stop after it.
- Never make one platform match the other here. That is a product change: ask, then do it on its own branch.
- Dry run or plan: change nothing. Reading and the tool check are fine. Report INCOMPLETE with the reason “dry run”.

## Report

One fenced `text` block, under 20 lines, with exactly these headings: Result, Needs your decision, What I added, Where it is, Try it. The format and the Result words are in the guide under What you get back. Try it ends with one next step, for example `Next: /reflex-cover for the next screen`.
