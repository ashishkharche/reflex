# How it works

Architecture overview for people who want to see how a Core, adapter, CLI and runner fit together. Reference: https://shopify.engineering/reflex

## Intro

Reflex keeps business logic in a UI-free [Core](glossary.md). A thin [adapter node](glossary.md) describes each screen. A [CLI](glossary.md) speaks [protocol v1](protocol/v1.md). The [runner](glossary.md) drives the same [journey](glossary.md) on Swift and Kotlin and fails when the answers differ.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/diagrams/01-in-your-app-dark.svg">
  <img src="../assets/diagrams/01-in-your-app-light.svg" alt="Your UI and the adapter both use the same ViewModel" width="100%">
</picture>

```mermaid
flowchart LR
  J[Journey file] --> R[Runner]
  R --> S[Swift CLI]
  R --> K[Kotlin CLI]
  S --> AS[Adapter / ReflexKit]
  K --> AK[Adapter / ReflexKit]
  AS --> CS[Swift Core]
  AK --> CK[Kotlin Core]
```

## The pieces

| Piece | What it is | Where it lives |
| --- | --- | --- |
| Core | Business logic, no UI, no ReflexKit | `swift/Sources/InventoryCore`, `kotlin/core`, `samples/outbox/*/core` |
| ViewModel | Typed state + `send` / `update` for one screen | Inside each Core |
| Adapter node | Name, JSON state, actions → `send` | `swift/Sources/InventoryIntrospection`, `kotlin/introspection`, outbox introspection modules |
| ReflexKit | Strict decoder, `Node`, `Session` | `kit/` (Swift package and `kit/kotlin`) |
| CLI | NDJSON host for one sample | `swift/Sources/InventoryCLI`, `kotlin/cli`, outbox CLIs |
| Journey | Shared `ls` / `do` steps | `tests/inventory/journeys/`, `samples/outbox/journeys/` |
| Runner | Parity + guard + `RESULT` | `runner/reflex_runner.py` |
| Network guard | Denies Internet sockets in tests | `scripts/network_guard.c` |

## What happens on `ls` and `do`

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/diagrams/02-one-exchange-dark.svg">
  <img src="../assets/diagrams/02-one-exchange-light.svg" alt="The same hello, ls and do requests get the same state from the Swift and Kotlin CLIs" width="100%">
</picture>

1. The runner (or you) sends `{"op":"hello","protocol":1}` once per process.
2. `ls` asks the focused [adapter node](glossary.md) for its name, state and actions.
3. `do` names an action and optional JSON input. ReflexKit decodes the input with the action’s schema.
4. The adapter calls `send` on the ViewModel. The Core updates state.
5. The reply includes `ok` and the new `node` snapshot. Both platforms must match on a shared journey.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/diagrams/03-shared-journey-dark.svg">
  <img src="../assets/diagrams/03-shared-journey-light.svg" alt="One journey runs on both CLIs and the runner prints RESULT" width="100%">
</picture>

## Rules the Core follows

- No UI framework imports in the Core.
- No ReflexKit imports in the Core.
- One `update` path writes state after construction.
- Services and clocks arrive through constructors (fixtures in tests).
- Navigation is Core state when the sample has more than one screen.
- Adapters only serialize state and dispatch actions; they do not invent business rules.

## Network guard

The runner loads `scripts/network_guard.c` before a behavior session: through `DYLD_INSERT_LIBRARIES` on macOS and `LD_PRELOAD` on Linux. It denies Internet `connect` and `sendto` (and `connectx` on macOS) and records attempts. A canary must be denied first. The runner fails a session that skips the ready marker or that attempts a request.

This is a deterministic test aid. It is not a security boundary against malicious native code. It only sees calls that go through the C library, so a static binary or a raw system call gets past it. When it can’t run, the runner prints `RESULT PASS-UNGUARDED` instead of `PASS` and exits 3 unless you pass `--allow-unguarded`. Mobile release builds do not include it.

## The samples

### Inventory

A list and detail flow with quantity edits. Code lives under `swift/`, `kotlin/` and `tests/inventory/`. Sample rules: [samples/inventory/README.md](../samples/inventory/README.md).

### Outbox

An offline queue with backoff and idempotency keys. Code lives under `samples/outbox/`. Sample rules: [samples/outbox/README.md](../samples/outbox/README.md).

No Shopify library is imported. Shared artifacts are journey files and the conformance fixture, not application code.
