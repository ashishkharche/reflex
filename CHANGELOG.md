# Changelog

Changes to Reflex by version. Newest first. Each entry says whether the protocol or the kit API changed. Full protocol history: [docs/protocol/CHANGELOG.md](docs/protocol/CHANGELOG.md).

## Unreleased

Docs only. No protocol change and no kit API change.

- Shorter README with a plain-language intro, banner and AI setup prompt.
- The AI prompt says to clone Reflex next to your repo and ends with a five-part report.
- New guide for adding Reflex to your app, including separate iOS and Android repos.
- Docs reorganised into an index, a glossary and `docs/project/`.
- How-it-works diagrams in `assets/diagrams/`.
- Update prompt in the README and an Updating Reflex section in the guide.

## 1.0.0 (6 Nov 2026)

First public release.

- Protocol 1, clarified. See [docs/protocol/v1.md](docs/protocol/v1.md).
- ReflexKit 1.0.1 for Swift and Kotlin: strict decoder, schemas, nodes, `Session` and the `Expect` matcher. See [kit/README.md](kit/README.md).
- Runner with Swift and Kotlin parity checks, the macOS network guard and `RESULT` lines.
- Inventory and outbox samples with shared journeys.
