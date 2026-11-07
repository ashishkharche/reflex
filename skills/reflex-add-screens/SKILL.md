---
name: reflex-add-screens
description: Add Reflex adapters and journeys for more screens of an app that already has Reflex set up. Use when the user asks to cover one screen, several screens or the whole app with Reflex tests. Also use it when the user asks which screens Reflex can test.
license: MIT
---

# Add screens to Reflex

Use this after `reflex-setup` has covered the main screen. If the app has no `reflex.json` yet, run `reflex-setup` first.

The how-to lives in the Reflex clone next to the app, usually `../reflex`. Read `docs/add-to-your-app.md` there, For AI assistants and sections 4 (One adapter node per ViewModel), 7 (Manifest and journey) and 9 (Check the app still works), before you write anything.

## Steps

1. List the screens. For each one name its ViewModel or state holder on iOS and on Android, side by side. Mark screens that exist on one platform only.
2. Flag every screen that keeps its state in its views, has no clear ViewModel or whose view still does the real work while the model only mirrors it. It needs a refactor before it can be tested. Do not refactor it. Ask the user.
3. Show the list and ask which screen to do first, unless the user already named one. “The whole app” means this list, then one screen at a time. It never means all screens in one go.
4. Do one screen, on its own branch from the latest main branch (`main`, `master` or whatever `git symbolic-ref --short refs/remotes/origin/HEAD` names), for example `reflex/settings`:
   - An adapter node on each platform the app has, with the same node name, state keys and action names on both.
   - The CLI wiring so the node is reachable.
   - One journey in the existing `reflex.json` journeys folder.
   - Run it with the `reflex-run` skill, which also builds both apps and runs their unit tests.
5. Run `git fetch` and count the commits behind the main branch. If you are behind, rebase and run step 4 again.
6. Commit on the branch. Do not push or open a pull request unless the user asks.
7. Stop and report. Wait for a yes before the next screen. Do the same after any refactor the user approved.

## Rules

- Same rules as `reflex-setup`: add new files, keep Reflex out of the app build, ask before editing other existing files or refactoring, wrap the real Core, never copy rules and never hide a platform difference.
- Never report PASS for a screen the runner did not run on every platform the app has.
- A screen whose view still does the real work is INCOMPLETE. So is a screen whose tests drive a copy of its logic. Name it under Needs your decision.
- A step marked `parity` or `xfail` makes the Result INCOMPLETE. Put the difference under Needs your decision.
- A CLI must load the same state the app shows. If it starts from an empty or made-up state the app fills in elsewhere, the screen is INCOMPLETE. A `parity` or `xfail` mark must not hide that.
- When the Result is FAIL or BLOCKED, still name each INCOMPLETE screen and its reason under Needs your decision.
- If parity shows the platforms differ, do not make one match the other here. That is a product change. Ask first. If the user says yes, put it on its own branch in its own commit and name that branch in the report.

## Report

Reply with the report from the guide, in one fenced `text` block, with exactly these five headings in this order: Result, Needs your decision, What I added, Where it is, Try it. Never rename one. List the screen under What I added. Put every flagged, skipped or remaining screen under Needs your decision. Where it is says how many commits the branch is behind the main branch.
