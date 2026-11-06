---
name: reflex-add-screens
description: Add Reflex adapters and journeys for more screens of an app that already has Reflex set up. Use when the user asks to cover one screen, several screens or the whole app with Reflex tests. Also use it when the user asks which screens Reflex can test.
license: MIT
---

# Add screens to Reflex

Use this after `reflex-setup` has covered the main screen. If the app has no `reflex.json` yet, run `reflex-setup` first.

The how-to lives in the Reflex clone next to the app, usually `../reflex`. Read `docs/add-to-your-app.md` there, sections 4 (One adapter node per ViewModel) and 7 (Manifest and journey), before you write anything.

## Steps

1. List the screens. For each one name its ViewModel or state holder on iOS and on Android, side by side. Mark screens that exist on one platform only.
2. Flag every screen that keeps its state in its views or has no clear ViewModel. It needs a refactor before it can be tested. Do not refactor it. Ask the user.
3. Show the list and ask which screens to do, unless the user already named them. “The whole app” means every screen that is not flagged.
4. Do one screen at a time:
   - An adapter node on each platform the app has, with the same node name, state keys and action names on both.
   - The CLI wiring so the node is reachable.
   - One journey in the existing `reflex.json` journeys folder.
   - Run it with the `reflex-run` skill. Move on only when it passes or the report says why not.
5. Stop and ask when a screen needs a decision. Carry on with the others.

## Rules

- Same rules as `reflex-setup`: add new files, ask before editing other existing files or refactoring, wrap the real Core, never copy rules and never hide a platform difference.
- Never report PASS for a screen the runner did not run on every platform the app has.

## Report

Reply with the five-part report from the guide, in one fenced `text` block. List each screen under What I added. Put every flagged or skipped screen under Needs your decision.
