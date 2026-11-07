---
name: reflex-cover
description: Cover a screen or feature with one Reflex test that runs on iOS and Android. Use when the user asks to test a screen, add a screen or feature to Reflex, cover the whole app or asks which screens Reflex can test.
license: MIT
---

# Cover a screen

One screen per run, one branch per screen. The app needs `tests/reflex.json` first. No manifest: use `reflex-start` instead. Merge the last Reflex branch before you start a new one.

Work only in the app repo and `../reflex`. Do not search home folders, other skills or other repos.

## Steps

1. **Pick the screen.** If the user named one, use it. Otherwise list the screens with their ViewModel on iOS and Android side by side. Mark one-platform screens and screens that keep state in their views. Ask which to do. “The whole app” means this list, one screen at a time.
2. **Check it is ready.** Name its main action, the one the screen exists for.
   - State in the views or no ViewModel: stop and ask. Do not refactor unasked.
   - Open the screen’s view file too. A value a user sees or changes that lives there (`remember`, `rememberPagerState`, `@State`, a local variable) is a readiness gap even when the main action is in the ViewModel. Name it under Needs your decision and make the Result INCOMPLETE. Do not refactor unasked.
   - Every network call that action makes needs a fixture. If one can’t be faked without changing app code, stop with BLOCKED and say which call.
3. **Branch** from the latest main branch (`git symbolic-ref --short refs/remotes/origin/HEAD`), for example `reflex/settings`.
4. **Read** `python3 ../reflex/scripts/guide.py 4 5 7`, never the whole guide. Copy the shape of the adapters the app already has.
5. **Add** an adapter on each platform with the same node name, state keys and action names. Wire it into each CLI.
6. **Prove the main action:** `python3 ../reflex/runner/explore.py tests/reflex.json 'do <MainAction> {...}'`. `NETWORK denied` means a call still has no fixture. Fix that first.
7. **Add one journey** in the existing journeys folder that runs the main action. Fold the steps of one user journey into one test. Keep a separate journey only when it needs different fixtures.
8. **Check** with the `reflex-check` steps.
9. **Commit** on the branch. Do not push unless asked.
10. **Report and stop.** Wait for a yes before the next screen.

## Rules

- When a step fails, run `python3 ../reflex/runner/explore.py tests/reflex.json` with the failing step first and read its STDERR before reading code.
- Same rules as `reflex-start`: wrap the real Core, keep Reflex out of the app build, ask before editing other app files, never hide a platform difference and never make one platform match the other here.
- If a user can see it, it is in state. If a user can do it, it is an action. The node lists every action every time, with no conditionals.
- A CLI loads the same state the app shows. An empty or made-up start state makes the screen INCOMPLETE.
- A journey that skips the main action makes the screen INCOMPLETE.
- Platforms come from `tests/reflex.json`. A Kotlin Multiplatform or Compose Multiplatform app with only a Kotlin host is complete. Do not ask for a Swift harness. Write the Result as “on kotlin (shared code)”.
- Debug a CLI only through `explore.py`, which prints its error output when something fails. Never launch the CLI, `java` or a probe script yourself. Never read or write the user’s own settings (Java Preferences, UserDefaults or anything in `~/Library`). Write nothing outside the app repo and `../reflex`. No custom scripts of any kind, including inline `python -c` and heredocs. Use your own read and search tools. Keep build and test logs in the app repo’s `.build/` and ensure it is gitignored, never `/tmp`.

## Report

Copy this shape. One fenced `text` block, five headings in this order, 19 lines at most counting blank lines. Count them before you send.

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
- PASS requires every platform in `tests/reflex.json` to pass in this session, every app to build and pass its unit tests in this session and no uncommitted changes. Otherwise report INCOMPLETE and name each platform or check that did not run.
- Commit changed code on `reflex/<screen>` before reporting. Never include unrelated changes or push unless asked. Where it is names the committed work, never “uncommitted”. If the commit cannot be made, report BLOCKED and say why under Needs your decision.
- Needs your decision is a numbered list with one short line each. Write “None” if empty. Every reason the Result is not PASS goes here.
- The Next line follows the Result word. PASS: “Next: merge reflex/<screen>, then /reflex-cover <next screen>”. Anything else: “Next: answer 1, then /reflex-check”. Never say merge before PASS.
- At most three decisions. Join related ones into one line. Nothing goes outside the block.
- No extra merge claim or logs. The Next line is the last line.
