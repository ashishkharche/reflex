# Inventory sample

Small list/detail app used as the main Reflex sample. Core code lives at the repo root under `swift/` and `kotlin/`. Journeys live in `tests/inventory/`.

## Layout

| Path | Role |
| --- | --- |
| `swift/Sources/InventoryCore` | UI-free Swift Core |
| `swift/Sources/InventoryIntrospection` | ReflexKit adapters |
| `swift/Sources/InventoryCLI` | macOS CLI |
| `kotlin/core` | JVM Core (no Android imports) |
| `kotlin/introspection` | ReflexKit adapters |
| `kotlin/cli` | JVM CLI |
| `mobile/ios`, `kotlin/mobile` | Thin UI hosts |
| `tests/inventory/` | Manifest and journeys |

## Core rules specific to this sample

- Quantity accepts JSON integer literals in the signed 64-bit range on both platforms.
- Fractions and exponents are rejected even when whole.
- Business range is 0 through 999999. Out-of-range values show an error and leave quantity unchanged.
- Decrement clamps at zero and stays listed.
- Save commits to in-memory fixture data. Save failure leaves persisted stock unchanged.
- Back refreshes the list and discards unsaved detail edits.
- Opening an unknown product ID is a no-op. Opening from detail is a no-op.

## Run

From the repository root, follow [docs/setup.md](../../docs/setup.md). Architecture overview: [docs/architecture.md](../../docs/architecture.md).
