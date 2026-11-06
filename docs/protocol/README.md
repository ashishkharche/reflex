# Reflex NDJSON protocol

Versioned line protocol spoken by every CLI host in this repository. ReflexKit implements it on Swift and Kotlin. The runner is the reference client.

| Version | Status | Spec |
| --- | --- | --- |
| 1 | current | [v1.md](v1.md) |

Changes: [CHANGELOG.md](CHANGELOG.md). A host announces its version only in reply to `hello`.
