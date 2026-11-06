# Glossary

One-line definitions for terms used across the Reflex docs.

| Term | Meaning |
| --- | --- |
| Core | The app’s business logic with no UI attached. Lives in a Swift package or a Kotlin JVM module. |
| ViewModel | One screen’s typed state and actions. `send` takes an action and one `update` writes state. |
| Adapter node | A ReflexKit `Node` that exposes a name, JSON state and actions by calling `send` on a ViewModel. |
| ReflexKit | The shared Introspection Kit: strict JSON decoder, schemas, nodes and `Session` on Swift and Kotlin. |
| CLI | A small process that serves protocol v1 over stdin/stdout for one sample. |
| NDJSON | One JSON object per line. |
| Journey | A JSON file of `ls` and `do` steps with expected replies. One file drives both platforms. |
| Manifest | A `reflex.json` that names platforms, commands, journeys and optional guard paths. |
| Runner | `runner/reflex_runner.py`. Runs journeys, checks parity and prints `RESULT`. |
| Conformance | Shared kit fixture (`kit/conformance/strict-decoder.json`) that both platforms must answer the same way. |
| Network guard | A C library loaded with `DYLD_INSERT_LIBRARIES` on macOS or `LD_PRELOAD` on Linux that denies Internet sockets during behavior sessions. |
| Introspection | Describing a screen as name + state JSON + actions so a host can drive it without UI. |
