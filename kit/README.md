# ReflexKit

One strict wire decoder and Introspection Kit for Swift and Kotlin. An app declares each action’s input once as a schema and the kit decodes, rejects, describes and serves it the same way on both platforms. The rules are in [protocol v1](../docs/protocol/v1.md).

| part | Swift (`kit/Package.swift`, product `ReflexKit`) | Kotlin (`kit/kotlin`, package `reflex.kit`) |
| --- | --- | --- |
| JSON value | `JSONValue` | `JsonValue` (`JsonInt`, `JsonString` …) |
| strict parser | `WireJSON.parse` | `WireJson.parse` |
| line framing and UTF-8 | `LineFramer`, `StrictUTF8` | `LineFramer`, `StrictUtf8` |
| schema and field types | `Schema`, `Field`, `FieldType` | `Schema`, `Field`, `FieldType` |
| typed accessors | `Args.int64` `string` `bool` `object` `array` `strings` `int64s` and `…IfPresent` | `Args.int64` `string` `bool` `obj` `array` `strings` `int64s` and `…OrNull` |
| errors | `WireError(code, path)`, `WireCode` | `WireError(code, path)`, `WireCode` |
| nodes | `Node`, `NodeAction`, `Focus` | `Node`, `NodeAction`, `Focus` |
| protocol v1 host | `Session`, `Session.Op`, `handle(bytes:)` | `Session`, `Session.Op`, `handle(ByteArray)` |
| matcher | `Expect.matches` `Expect.mismatch` | `Expect.matches` `Expect.mismatch` |

The kit has no dependencies. Kotlin needs only the Kotlin standard library.

## Adopt it in an app

Keep the Core free of the kit. Write one adapter node per ViewModel in a separate introspection target and one small CLI.

Swift, in `Package.swift`:

```swift
dependencies: [.package(path: "../reflex/kit")],
targets: [
    .target(name: "OvenTimerIntrospection", dependencies: ["OvenTimerCore", .product(name: "ReflexKit", package: "kit")]),
    .executableTarget(name: "oven-timer-cli", dependencies: ["OvenTimerIntrospection", .product(name: "ReflexKit", package: "kit")])
]
```

```swift
import ReflexKit
import OvenTimerCore

private let startInput = Schema([
    .required("seconds", .int64(min: 1, max: 3_600)),
    .optional("label", .string),
    .optional("fanOn", .bool)
])

struct OvenTimerNode: Node {
    let vm: OvenTimerViewModel
    var name: String { "OvenTimer" }
    var state: JSONValue {
        var fields: [String: JSONValue] = ["status": .string(vm.state.status.rawValue),
                                           "remainingSeconds": .int(vm.state.remainingSeconds)]
        if let label = vm.state.label { fields["label"] = .string(label) }
        return .object(fields)
    }
    var actions: [String: NodeAction] { [
        "Start": NodeAction(input: startInput) { args in
            vm.send(.start(seconds: args.int64("seconds"), label: args.stringIfPresent("label"),
                           fanOn: args.boolIfPresent("fanOn") ?? false))
        },
        "Skip": NodeAction { _ in vm.send(.skip) }
    ] }
}

let clock = FakeClock(now: 1_800_000_000_000)
let vm = OvenTimerViewModel(clock: clock)
Session(sample: "oven-timer", root: { OvenTimerNode(vm: vm) }, ops: [
    "tick": Session.Op(input: Schema([.required("ms", .int64(min: 0, max: 86_400_000))])) { args in
        clock.advance(by: args.int64("ms"))
    }
]).serveStandardIO()
```

Kotlin, in `settings.gradle.kts` and the module’s `build.gradle.kts`:

```kotlin
include(":reflex-kit")
project(":reflex-kit").projectDir = file("../reflex/kit/kotlin")

dependencies { implementation(project(":oventimer-core")); api(project(":reflex-kit")) }
```

```kotlin
import reflex.kit.*

private val startInput = Schema(
    Field.required("seconds", FieldType.int64(min = 1, max = 3_600)),
    Field.optional("label", FieldType.string),
    Field.optional("fanOn", FieldType.bool))

class OvenTimerNode(private val vm: OvenTimerViewModel) : Node {
    override val name = "OvenTimer"
    override val state: JsonValue get() = jsonObject(
        "status" to vm.state.status.wire.json,
        "remainingSeconds" to vm.state.remainingSeconds.json,
        "label" to vm.state.label?.json)
    override val actions get() = mapOf(
        "Start" to NodeAction(startInput) { args ->
            vm.send(OvenTimerViewModel.Action.Start(args.int64("seconds"), args.stringOrNull("label"), args.boolOrNull("fanOn") ?: false))
        },
        "Skip" to NodeAction { vm.send(OvenTimerViewModel.Action.Skip) })
}

fun main() {
    val clock = FakeClock(1_800_000_000_000L)
    val vm = OvenTimerViewModel(clock)
    Session("oven-timer", { OvenTimerNode(vm) }, mapOf(
        "tick" to Session.Op(Schema(Field.required("ms", FieldType.int64(min = 0, max = 86_400_000)))) { clock.advance(it.int64("ms")) }
    )).serveStandardIO()
}
```

`OvenTimerViewModel` and `FakeClock` above stand for the app’s own types. The kit decodes `seconds` as Int64 on both platforms. Let the Core take `Int64` or `Long`. If it takes a narrower type the adapter narrows the value and throws `WireError(WireCode.intRange, "$.input.seconds")` when it does not fit. Absent optionals come back as nil or null. A wrong type never reaches `run`.

Write state with JSON integers only. Times and durations in milliseconds keep both platforms exact.

## Test it

1. Write a manifest and journeys for the runner (see `runner/README.md`) and run them with `--platform both`.
2. Use `Expect.matches` or `Expect.mismatch` in unit tests that check a `Session.handle` reply. It is type-strict on both platforms.
3. Run the kit’s own tests to prove the decoder on the host toolchain:

```bash
swift test --package-path kit -j 2
kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :reflex-kit:test
```

Both read `kit/conformance/strict-decoder.json`. With `REFLEX_CONFORMANCE_REPORT=DIR` set they write `DIR/swift.ndjson` and `DIR/kotlin.ndjson` with the exact reply bytes of every case. `python3 runner/conformance_table.py DIR` turns them into a table and fails when any case’s reply bytes differ between platforms.

`serveStandardIO` reads raw bytes, frames them with `LineFramer` and answers each line with `handle(bytes:)` (Kotlin `handle(ByteArray)`). A host with another transport should do the same. `handle(_ line: String)` skips the framing and UTF-8 checks because its input is already text.

On Swift `WireJSON.parse` returns `JSONValue`, whose `String`-keyed dictionary cannot hold two canonically equivalent keys. It throws `json.duplicate_key` for such an object. `Session` does not use it and follows the exact-key rule.

## Conformance fixture

`conformance/strict-decoder.json` holds request cases with an expected rejection (`[code, path]`), an expected decoded input or a partial response, plus matcher cases. Case ids start with the finding they cover: F-01 strings as numbers, F-02 fractions and exponents, F-03 booleans as integers, F-04 Int64 range, F-05 wrong-typed, unknown and missing fields, F-06 non-object input and the `args` alias, F-07 duplicate keys, F-13 matcher strictness, G-1 exact key comparison, G-2 line framing, G-3 strict UTF-8 and P for protocol rules. A stream case holds raw bytes in hex and the exact reply lines it must produce, with `@node` for the probe node. Each kit feeds the bytes to `LineFramer` whole and one byte at a time. Add a case there before changing a rule and both platforms pick it up.
