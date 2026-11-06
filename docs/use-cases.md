# Use cases

- Test app logic with no UI by driving `ls` and `do` over NDJSON (one JSON message per line).
- Prove iOS and Android parity from one shared journey file.
- Cover behaviour that is hard to test on a device, such as timers backoff and an offline outbox.
- Run fast CI checks on the Core without a simulator or emulator.
- Let an agent explore and assert state through the same protocol a human uses.

A journey file is a shared list of `ls` and `do` steps. The same file drives both the Swift Core and the Kotlin Core, so one test proves both platforms match.

The Core is the app’s business logic with no UI attached. Each screen is a ViewModel: typed state in, an action in and new state out through one `update` function. ReflexKit is the shared Introspection Kit: a strict decoder and node layer that describes each screen the same way in Swift and Kotlin. Conformance cases are the kit’s shared fixture that both platforms must answer byte for byte. On macOS a network guard blocks real Internet calls during behavior sessions so a journey cannot leak HTTP. Linux notes for the guard live in [testing.md](testing.md).
