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
4. Read `../reflex/docs/add-to-your-app.md` from the top, including For AI assistants. It is the source of truth for layout, adapters, CLIs, the manifest, the checks and the report.
5. Make a branch from the latest main branch, for example `reflex/home`.
6. First setup: do the main screen only. Offer the `reflex-add-screens` skill for the rest.
7. Update: read `../reflex/CHANGELOG.md` from the noted commit to now. Apply each change to the Reflex files the app already has: adapters, CLIs, `reflex.json` and journeys.
8. Run the tests with the `reflex-run` skill. It also builds both apps and runs their unit tests.
9. Run `git fetch` and `git rev-list --count HEAD..origin/main`. If you are behind, rebase and run step 8 again.
10. Stop and reply with the report. Do not start another screen.

## Rules

- Keep Reflex out of the app build. The Swift Introspection target and CLI go in their own package, for example `ReflexHarness/`. Never add `../reflex` to the app’s `Package.swift`, its Core package or its Xcode project. On Kotlin, use the guarded `settings.gradle.kts` block from the guide.
- Keep the app’s code and behaviour unchanged. Add new files and the new modules the guide describes. Adding the guarded block to `settings.gradle.kts` is the only edit to app files you may make without asking. List it in the report.
- Files Reflex added earlier (adapters, CLIs, `reflex.json`, journeys) may be updated to follow the guide or the CHANGELOG. Ask before editing any other existing file.
- Ask before any refactor, for example a screen that keeps its state in its views. After a refactor, stop and report before anything else.
- Every adapter wraps the app’s real Core, the same object the screen uses. Never copy its rules into an adapter or a CLI.
- A screen whose view still does the real work is INCOMPLETE, not PASS. Name it under Needs your decision.
- Never hide a platform difference. Keep each platform’s real value and mark it as the guide says.
- Never make one platform match the other on this branch. That is a product change. Ask first. If the user says yes, do it on its own branch in its own commit.
- Never report PASS unless the guide’s Result words allow it. A failed app build or unit test is FAIL even when the runner passed.
- Dry run: if the user asks for a dry run or a plan, change nothing. Do not clone, write files, install or build. Reading is fine: inspect the app’s files and read the guide from the clone or from `https://github.com/ashishkharche/reflex/blob/main/docs/add-to-your-app.md`. Name the platforms and the main screen you found, say what each step would add, then give the report with Result INCOMPLETE and the reason “dry run”.

## Report

Reply with only the report from What you get back in the guide, in one fenced `text` block. Use exactly these five headings in this order and never rename them: Result, Needs your decision, What I added, Where it is, Try it. Where it is says how many commits the branch is behind the main branch.
