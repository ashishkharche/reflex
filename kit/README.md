# ReflexKit

API reference for the shared Introspection Kit used by Swift and Kotlin hosts. Full adoption steps: [docs/add-to-your-app.md](../docs/add-to-your-app.md). Protocol rules: [docs/protocol/v1.md](../docs/protocol/v1.md).

An app declares each action’s input once as a schema. The kit decodes, rejects, describes and serves it the same way on both platforms.

| Part | Swift (`kit/Package.swift`, product `ReflexKit`) | Kotlin (`kit/kotlin`, package `reflex.kit`) |
| --- | --- | --- |
| JSON value | `JSONValue` | `JsonValue` (`JsonInt`, `JsonString` …) |
| Strict parser | `WireJSON.parse` | `WireJson.parse` |
| Line framing and UTF-8 | `LineFramer`, `StrictUTF8` | `LineFramer`, `StrictUtf8` |
| Schema and field types | `Schema`, `Field`, `FieldType` | `Schema`, `Field`, `FieldType` |
| Typed accessors | `Args.int64` `string` `bool` `object` `array` `strings` `int64s` and `…IfPresent` | `Args.int64` `string` `bool` `obj` `array` `strings` `int64s` and `…OrNull` |
| Errors | `WireError(code, path)`, `WireCode` | `WireError(code, path)`, `WireCode` |
| Nodes | `Node`, `NodeAction`, `Focus` | `Node`, `NodeAction`, `Focus` |
| Protocol v1 host | `Session`, `Session.Op`, `handle(bytes:)` | `Session`, `Session.Op`, `handle(ByteArray)` |
| Matcher | `Expect.matches` `Expect.mismatch` | `Expect.matches` `Expect.mismatch` |
| Debug socket host (debug builds only) | `SocketHost` in product `ReflexSocketHost` | `SocketHost` in `kit/kotlin-socket` (`reflex.kit.socket`) |

The socket host is a separate product and module so release builds never link it. See [docs/real-build.md](../docs/real-build.md).

The kit has no dependencies. Kotlin needs only the Kotlin standard library.

## Adopt it in an app

Keep the Core free of the kit. Write one adapter node per ViewModel in a separate introspection target and one small CLI. Step-by-step: [docs/add-to-your-app.md](../docs/add-to-your-app.md).

Swift package sketch, in its own harness package so the app never resolves the kit:

```swift
// ReflexHarness/Package.swift
dependencies: [.package(path: "../OvenTimerCore"), .package(path: "../../reflex/kit")],
targets: [
    .target(name: "OvenTimerIntrospection", dependencies: ["OvenTimerCore", .product(name: "ReflexKit", package: "kit")]),
    .executableTarget(name: "oven-timer-cli", dependencies: ["OvenTimerIntrospection", .product(name: "ReflexKit", package: "kit")])
]
```

Kotlin settings sketch, included only when the clone exists:

```kotlin
val reflexKit = file("../reflex/kit/kotlin")
if (reflexKit.isDirectory) {
    include(":reflex-kit")
    project(":reflex-kit").projectDir = reflexKit
}
```

A Swift ViewModel on the main actor needs `serveStandardIOOnMain(settle:)`, which answers each line on the main actor after the work an action started has run. `handle(bytes:settle:)` is the same for one line.

Longer Swift and Kotlin examples remain in this package’s tests (`AdoptionExampleTests` / `AdoptionExampleTest`) and in [docs/how-you-use-it.md](../docs/how-you-use-it.md).
