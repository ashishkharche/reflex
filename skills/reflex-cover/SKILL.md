---
name: reflex-cover
description: Cover a screen or feature with one Reflex test that runs on iOS and Android. Use when the user asks to test a screen, add a screen or feature to Reflex, cover the whole app or asks which screens Reflex can test.
license: MIT
---

# Cover a screen

One screen per run, one branch per screen. The app needs `tests/reflex.json` first. No manifest: use `reflex-start` instead.

## Steps

1. **Pick the screen.** If the user named one, use it. Otherwise list the screens with their ViewModel on iOS and Android side by side. Mark one-platform screens and screens that keep state in their views. Ask which to do. “The whole app” means this list, one screen at a time.
2. **Needs a refactor?** If the view does the real work or there is no ViewModel, stop and ask. Do not refactor unasked.
3. **Branch** from the latest main branch (`git symbolic-ref --short refs/remotes/origin/HEAD`), for example `reflex/settings`.
4. **Read only** sections 4, 5 and 7 of `../reflex/docs/add-to-your-app.md`. Copy the shape of the adapters the app already has.
5. **Add** an adapter on each platform with the same node name, state keys and action names, wire it into each CLI and add one journey in the existing journeys folder. Fold the steps of one user journey into one test. Keep a separate journey only when it needs different fixtures.
6. **Check** with the `reflex-check` steps.
7. **Commit** on the branch. Do not push unless asked.
8. **Report and stop.** Wait for a yes before the next screen.

## Rules

- Same rules as `reflex-start`: wrap the real Core, keep Reflex out of the app build, ask before editing other app files, never hide a platform difference and never make one platform match the other here.
- If a user can see it, it is in state. If a user can do it, it is an action. The node lists every action every time, with no conditionals.
- A CLI loads the same state the app shows. An empty or made-up start state makes the screen INCOMPLETE.
- Every network call needs a fixture. The guard fails the run otherwise.

## Report

One fenced `text` block with exactly these headings: Result, Needs your decision, What I added, Where it is, Try it. Put every remaining or flagged screen under Needs your decision. Try it ends with one next step, for example `Next: /reflex-cover home` or `Next: /reflex-check before you merge`.
