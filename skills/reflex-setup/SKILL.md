---
name: reflex-setup
description: Set up Reflex in an iOS and Android app for the first time or update an existing Reflex setup, so tests and AI agents can drive the app’s ViewModels without a screen. Use when the user asks to add, install, set up, upgrade or update Reflex.
license: MIT
---

# Set up or update Reflex

Reflex is a kit, not a dependency you vendor. The full instructions live in the Reflex repo. This skill tells you where to start and which rules always apply. Do not work from memory of the docs: read them from the clone.

## Steps

1. Confirm you are in the app’s repo, not in Reflex itself.
2. Find the platforms. If this repo has only iOS or only Android code, ask whether the app has the other platform and where its repo is. Do not guess.
3. Find Reflex next to the app, for example `../reflex`. It may also be a git submodule.
   - Not there: clone `https://github.com/ashishkharche/reflex.git` next to the app repo. Never clone or copy it inside the app repo.
   - Already there: this is an update. Note the current commit, then `git -C ../reflex pull`. With a submodule, update the submodule instead.
4. Read `../reflex/docs/add-to-your-app.md` from the top, including For AI assistants. It is the source of truth for layout, adapters, CLIs, the manifest and the report.
5. First setup: do the main screen only, as the guide says. Offer the `reflex-add-screens` skill for the rest.
6. Update: read `../reflex/CHANGELOG.md` from the noted commit to now. Apply each change to the Reflex files the app already has: adapters, CLIs, `reflex.json` and journeys.
7. Run the tests with the `reflex-run` skill and reply with its report.

## Rules

- Keep the app’s code and behaviour unchanged. Add new files and the new targets or modules the guide describes. Registering those targets in an existing build file (`Package.swift`, `settings.gradle.kts`, an Xcode project) is the only edit to app files you may make without asking. List each such edit in the report.
- Files Reflex added earlier (adapters, CLIs, `reflex.json`, journeys) may be updated to follow the guide or the CHANGELOG. Ask before editing any other existing file.
- Ask before any refactor, for example a screen that keeps its state in its views.
- Every adapter wraps the app’s real Core. Never copy its rules into an adapter or a CLI.
- Never hide a platform difference. Keep each platform’s real value and mark it as the guide says.
- Never report PASS unless the guide’s Result words allow it. Use FAIL, BLOCKED or INCOMPLETE otherwise, with every reason under Needs your decision.
- Dry run: if the user asks for a dry run or a plan, change nothing. Do not clone, write files, install or build. Reading is fine: inspect the app’s files and read the guide from the clone or from `https://github.com/ashishkharche/reflex/blob/main/docs/add-to-your-app.md`. Name the platforms and the main screen you found, say what each step would add, then give the report with Result INCOMPLETE and the reason “dry run”.

## Report

Reply with only the five-part report from What you get back in the guide, in one fenced `text` block: Result, Needs your decision, What I added (or What I changed), Where it is, Try it.
