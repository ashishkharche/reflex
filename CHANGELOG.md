# Changelog

Changes to Reflex by version. Newest first. Each entry says whether the protocol or the kit API changed. Full protocol history: [docs/protocol/CHANGELOG.md](docs/protocol/CHANGELOG.md).

## Unreleased

No protocol change and no kit API change.

- Outbox sample: the adapter always lists Enqueue, PurgeSent, Retry, SetOnline and SyncNow. `update` decides validity and is the only state writer, including attempt counts. New journey `16-stable-actions.json`.
- AI report: Result is PASS only when every adapter wraps the real Core and no platform difference is hidden. Otherwise it is FAIL, BLOCKED or INCOMPLETE with the reasons under Needs your decision. New example.

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
