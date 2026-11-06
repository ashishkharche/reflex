# Inventory sample A

Reference: https://shopify.engineering/reflex

This sample shows a small inventory app whose business logic lives in a Core with no UI. The Core holds `InventoryApp`, `InventoryNavigator`, `InventoryListViewModel` and `InventoryDetailViewModel`. Swift uses a package that targets macOS and iOS. Kotlin uses a JVM module with no Android imports. Mobile and CLI depend on Core. Core does not import either host or ReflexKit.

Each ViewModel has typed State, Action and private Message. `send` wraps an Action in a Message. `update` is the only state writer after construction. Save results return as internal Messages. `InventoryService` is supplied through constructors. The sample uses synchronous in-memory fixture services, not GraphQL or a production backend.

Navigation is Core state. The tree is app → navigator → list or detail. The CLI follows `child` until it reaches the leaf. The navigator lends `OpenProduct` and `goBack` on every screen. Opening from detail is a reducer no-op. A missing product ID is also a no-op. A leaf’s unavailable actions are rejected before dispatch.

Swift’s `InventoryIntrospection` target and Kotlin’s `introspection` module hold adapter nodes built on ReflexKit. Nodes expose stable names, JSON state, actions and optional child links. Action maps are unconditional. Every action closure calls `send`. Optional error encoding and child selection serialize Core state without deciding business rules. Each action declares its input as a kit `Schema`. Input validation belongs to the kit’s strict decoder, not the reducer or node action map.

Quantity accepts JSON integer literals in the signed 64-bit range on both platforms. Fractions and exponents are rejected even when whole. The business range is 0 through 999999. Out-of-range business values expose a visible error without changing quantity. Decrement clamps at zero and remains listed. Save commits to fixture memory. Back refreshes the list and discards unsaved detail edits. Save failure leaves persisted stock unchanged.

The Mobile hosts read ViewModel state and call `send`. A small revision counter bridges the synchronous Core to SwiftUI and Compose rendering. The counter contains no business state. Input text is local presentation state. There is no live socket transport or async effect runtime in this sample.

Behavior sessions load a macOS network guard (a dynamic interposer) before either native CLI starts. It denies Internet `connect`, `connectx` and `sendto` calls and records attempts. The runner refuses sessions without its ready marker and fails after an attempted request even when the service catches it. A constructor-supplied sticky guard catches unprovided HTTP at the service boundary too. This is a deterministic test guard, not a security boundary against malicious native code or direct syscalls. The process guard is macOS-only. Mobile release builds do not include it.

No Shopify library is imported. The shared artifacts are the journey files and the conformance fixture, not application code. ReflexKit is test infrastructure that describes each screen the same way on both platforms: both kits implement one documented contract and prove it on the same fixture.

## Outbox sample

`OutboxViewModel` follows the same shape: typed State and Action, a private Message for delivery results and one `update`. It takes a `Clock` and a `Transport` at construction. The Core never reads the system clock and has no network code. The CLI owns the wake loop through `FakeClock.advance` and the `http` tripwire transport.
