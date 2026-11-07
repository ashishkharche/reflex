# Changelog

Changes to Reflex by version. Newest first. Each entry says whether the protocol or the kit API changed. Full protocol history: [docs/protocol/CHANGELOG.md](docs/protocol/CHANGELOG.md).

## Unreleased

No protocol change and no kit API change.

- Skills: `reflex-setup` checks the stack and the tools before any change. Flutter, React Native and other stacks without a kit, or a missing tool such as Xcode, a JDK or Python 3, stop with BLOCKED and say what is needed. Kotlin Multiplatform runs with `--platform kotlin`. All three skills find the main branch instead of assuming `main`, ask before touching uncommitted changes and commit on the branch without pushing.
- AI setup: a CLI that starts from an empty or made-up state the app fills in elsewhere makes that screen INCOMPLETE, and a `parity` or `xfail` mark can’t hide it. When the Result is FAIL or BLOCKED, the report still names each INCOMPLETE screen and its reason.
- Outbox sample: the adapter always lists Enqueue, PurgeSent, Retry, SetOnline and SyncNow. `update` decides validity and is the only state writer, including attempt counts. New journey `16-stable-actions.json`.
- AI report: Result is PASS only when every adapter wraps the real Core and no platform difference is hidden. Otherwise it is FAIL, BLOCKED or INCOMPLETE with the reasons under Needs your decision. New example.
- Runner: `eventually` steps poll `ls` up to a deadline without re-sending the action and print the last state on failure. `before` checks a precondition before a step is sent. The outbox CLIs add an `advanceLater` host op that changes state on a background thread, with journey `17-eventually.json` and two new red paths. No wire change.
- Network guard: also builds and loads on Linux through `LD_PRELOAD`, with the same canary. A clean run without the guard now prints `RESULT PASS-UNGUARDED` and exits 3 unless `--allow-unguarded` is passed. `guard=skipped-not-macos` is now `guard=skipped-unavailable`. Linux was tested on one Debian 13 x86_64 host with Kotlin hosts only.
- Debug socket host, first part. New Swift product `ReflexSocketHost` and Kotlin module `kit/kotlin-socket` serve a `Session` on 127.0.0.1. Runner platforms may set `socket`. The outbox CLIs take `--listen PORT` and `samples/outbox/live.json` runs a live journey on both. Kit API addition, no protocol change.
- Debug socket host in the sample apps. The inventory iOS and Android debug builds start it when launched with `reflexPort`, run each request on the main thread and redraw. `scripts/live_ui_check.py` checks the real screen after each action and `tests/inventory/live.json` runs a live journey. `scripts/check_release_exclusion.sh` proves the Release app and release APK leave out the host, its dependencies and on Android the `INTERNET` permission. The Kotlin host now binds IPv4 127.0.0.1 instead of the loopback default, which was `::1` on Android. Tested on one iOS simulator and one Android emulator, not on a physical phone. No protocol change.
- Assistant skills. `skills/` holds `reflex-setup`, `reflex-add-screens` and `reflex-run` in the Agent Skills format. The repo root is a `reflex` plugin for Claude Code and Grok Build (`.claude-plugin/`) and Cursor (`.cursor-plugin/`). Codex installs it from the same marketplace file. `reflex-setup` supports a dry run that changes nothing. The guide now says how to update files Reflex added earlier. See `docs/assistants.md`. No protocol change and no kit API change.
- Safer setup by assistants. No protocol change and no kit API change. Apply it on your next run:
  - Before reporting, build both apps and run their existing unit tests. A failed build or unit test makes the Result FAIL.
  - Keep Reflex out of the app build. The Swift Introspection target and CLI move to their own harness package, for example `ReflexHarness/`. The app’s `Package.swift`, Core package and Xcode project never name `../reflex`. On Kotlin, include the Reflex modules only when the clone exists. If your app already points at `../reflex`, move those parts out.
  - A screen whose view still does the real work is INCOMPLETE and named under Needs your decision.
  - A product change found through parity goes on its own branch in its own commit, after asking.
  - One screen per branch. Stop and report after each screen or refactor. “The whole app” means list first, then one at a time.
  - Where it is says how many commits the branch is behind the main branch. Rebase first when it is behind.
  - The report has exactly five headings: Result, Needs your decision, What I added, Where it is, Try it. “What I changed” is gone.

- Shorter README with a plain-language intro, banner and AI setup prompt.
- One AI prompt covers first setup and later updates and ends with a five-part report.
- New guide for adding Reflex to your app, including separate iOS and Android repos.
- Docs reorganised into an index, a glossary and `docs/project/`.
- How-it-works diagrams in `assets/diagrams/`.
- FAQ for environments, tech stacks, workflows and safety (`docs/faq.md`).
- Shorter AI prompt in the README. The full instructions moved to a For AI assistants section in the setup guide.
- The AI report is one text block with a heading per part, a numbered list of decisions and a new example, so it stays readable in a terminal.
- README, setup and add-to-your-app now say when macOS is needed (Swift / iOS and the network guard). Linux, Docker, Linux CI and WSL 2 cover Kotlin-only paths. See [docs/faq.md](docs/faq.md).

## 1.0.0 (6 Nov 2026)

First public release.

- Protocol 1, clarified. See [docs/protocol/v1.md](docs/protocol/v1.md).
- ReflexKit 1.0.1 for Swift and Kotlin: strict decoder, schemas, nodes, `Session` and the `Expect` matcher. See [kit/README.md](kit/README.md).
- Runner with Swift and Kotlin parity checks, the macOS network guard and `RESULT` lines.
- Inventory and outbox samples with shared journeys.
