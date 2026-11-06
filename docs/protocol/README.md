# Reflex NDJSON protocol

The CLI hosts in this repository speak one versioned line protocol. ReflexKit implements it on Swift and Kotlin and the runner is its reference client.

| version | status | spec |
| --- | --- | --- |
| 1 | current | [v1.md](v1.md) |

Changes between versions are in [CHANGELOG.md](CHANGELOG.md). A host announces its version only in reply to `hello`.
