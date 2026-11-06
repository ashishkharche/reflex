# Drive a running build over a socket

Status: the kit hosts, the runner transport and a desktop journey work and are tested. Wiring into the iOS and Android sample apps is not done yet. See [What is not done yet](#what-is-not-done-yet).

The usual CLI runs your Core in a test process. A debug socket host serves the same protocol v1 `Session` from inside a running app, so a test or an agent can drive the real build and watch the screen change.

## The hosts

| Platform | Module | Add it |
| --- | --- | --- |
| Swift | product `ReflexSocketHost` in `kit/Package.swift` | Debug configuration only |
| Kotlin | `kit/kotlin-socket` (`reflex.kit.socket.SocketHost`) | `debugImplementation` on Android |

Both bind 127.0.0.1 only and accept one client at a time. They speak the same framing and replies as the CLI. The `hello` handshake lasts as long as the host. Any local process can connect while it runs, so never start it in a release build.

`perform` decides where each request runs. Pass a closure that runs the work on the main thread, so every action goes through the real Core and the live UI updates. These two sketches have not been built in an app yet:

```swift
#if DEBUG
import ReflexSocketHost
let host = try SocketHost(session: session, port: 47811) { work in DispatchQueue.main.sync(execute: work) }
host.start()
#endif
```

```kotlin
// src/debug only
val host = SocketHost(session, 47812) { work ->
    val result = java.util.concurrent.FutureTask { work() }
    android.os.Handler(android.os.Looper.getMainLooper()).post(result)
    result.get()
}
host.start()
```

On Android, reach the device port with `adb forward tcp:47812 tcp:47812`. The iOS simulator shares the Mac’s loopback.

## The runner

A platform with `socket` connects instead of starting a process per journey. An optional `command` starts one long-lived host for the whole run.

```json
"swift-live": {"socket": "127.0.0.1:47811", "command": ["{root}/samples/outbox/swift/.build/debug/outbox-cli", "fake", "--listen", "47811"]}
```

Only loopback addresses are accepted. State carries across journeys, so each live journey must leave the app as it found it. `--repeat` checks every repeat but does not compare transcripts. Exit codes and the network guard do not apply, so a clean live run ends `RESULT PASS-UNGUARDED`.

Try it with the outbox CLIs:

```bash
bash scripts/build.sh
python3 runner/reflex_runner.py samples/outbox/live.json --platform both --repeat 2 --allow-unguarded
```

The journey is `samples/outbox/live/01-live.json`. `runner/red/live-leftover.json` is a red path that leaves state behind and must fail on the second repeat.

## What is not done yet

- The iOS and Android sample apps do not start a socket host yet. Nothing here has run on a simulator or a device.
- No check yet proves that a release build excludes the host. The plan is to scan a release APK and an iOS Release binary for `SocketHost` and fail when it is found.
- No journey drives a live UI yet.

Until those land, report a socket setup as INCOMPLETE ([Result words](add-to-your-app.md#result-words)).
