# Drive a running build over a socket

Status: built and tested in the inventory sample apps on one iOS 26.5 simulator and one Android 16 (API 36) emulator. Not tested on a physical phone. See [Limits](#limits).

The usual CLI runs your Core in a test process. A debug socket host serves the same protocol v1 `Session` from inside a running app, so a test or an agent can drive the real build and watch the screen change.

## The hosts

| Platform | Module | Add it |
| --- | --- | --- |
| Swift | product `ReflexSocketHost` in `kit/Package.swift` | Debug configuration only |
| Kotlin | `kit/kotlin-socket` (`reflex.kit.socket.SocketHost`) | `debugImplementation` on Android |

Both bind IPv4 127.0.0.1 only and accept one client at a time. They speak the same framing and replies as the CLI. The `hello` handshake lasts as long as the host. Any local process can connect while it runs, so never start it in a release build.

`perform` decides where each request runs. Run the work on the main thread, so every action goes through the real Core and the live UI redraws.

## In the sample apps

The inventory apps start the host only when you opt in at launch. Without the opt-in a debug build opens no port.

| | iOS (`mobile/ios`) | Android (`kotlin/mobile`) |
| --- | --- | --- |
| Opt-in | launch argument `-reflexPort 47814` | intent extra `--ei reflexPort 47815` |
| Host code | `DebugSocket.swift`, all inside `#if DEBUG` | `src/debug/kotlin/reflex/DebugSocket.kt` |
| Release side | the Release configuration excludes `DebugSocket.swift` | `src/release` has a stub that does nothing |
| Dependencies | `InventoryIntrospection`, `ReflexKit` and `ReflexSocketHost` are `link: false`. Only Debug links them, through `OTHER_LDFLAGS`. | `debugImplementation(":introspection")` and `debugImplementation(":reflex-socket")` |
| Network permission | none needed for loopback on the simulator | `INTERNET` only in `src/debug/AndroidManifest.xml` |
| Redraw | the host bumps `InventoryModel.revision` on the main thread | the host bumps `InventoryModel.revision` on the main thread |

The shape of the iOS host:

```swift
#if DEBUG
let session = Session(sample: "inventory", root: { AppNode(app: model.app) })
let host = try SocketHost(session: session, port: port) { work in
    DispatchQueue.main.sync { let reply = work(); model.revision += 1; return reply }
}
host.start()
#endif
```

And the Android one, in `src/debug` only:

```kotlin
val host = SocketHost(session, port) { work ->
    val task = FutureTask { work().also { model.revision++ } }
    Handler(Looper.getMainLooper()).post(task)
    task.get()
}
```

A port that is already taken logs an error and the app keeps running.

Run it yourself. Use your own simulator or emulator and leave other people’s devices alone:

```bash
# iOS: build with scripts/check_release_exclusion.sh ios, then
xcrun simctl install <your-simulator> .build/ios-dd/Build/Products/Debug-iphonesimulator/InventoryMobile.app
xcrun simctl launch <your-simulator> com.ashishkharche.reflex.inventory -reflexPort 47814
python3 scripts/live_ui_check.py ios --device <your-simulator> --port 47814

# Android: build with scripts/check_release_exclusion.sh android, then
adb -s <your-emulator> install kotlin/mobile/build/outputs/apk/debug/mobile-debug.apk
adb -s <your-emulator> shell am start -n com.ashishkharche.reflex.inventory/reflex.MainActivity --ei reflexPort 47815
adb -s <your-emulator> forward tcp:47815 tcp:47815
python3 scripts/live_ui_check.py android --device <your-emulator> --port 47815

# Either platform, through the runner
python3 runner/reflex_runner.py tests/inventory/live.json --platform ios-simulator --repeat 2 --allow-unguarded
```

The iOS simulator shares the Mac’s loopback. On Android, `adb forward` carries the Mac port to the emulator.

## Does the screen really change?

`scripts/live_ui_check.py` sends actions over the socket and reads the real screen after each one: a simulator screenshot read with Vision OCR on iOS (`scripts/ocr_text.swift`) and a `uiautomator dump` on Android. It opens the shirt, sets 7, saves, goes back and checks that the list shows `Cotton shirt: 7`, then puts the stock back to 3. Each check waits up to six seconds for the wanted text and for the old text to disappear. It ends `RESULT LIVE-UI PASS` or `FAIL`.

It caught a real mistake. The first version skipped Save, so the list went back to `Cotton shirt: 3`. The wire said 3 as well, because an unsaved edit is dropped on Back. The screen and the state agreed and the check failed for the right reason.

`tests/inventory/live.json` runs `tests/inventory/live/01-live-stock.json` against a running app. It never launches a device.

## Release builds leave it out

`scripts/check_release_exclusion.sh [ios|android|both]` builds Debug and Release and fails unless each marker is absent from Release and present in Debug. The Debug count is the positive control, so a broken scan cannot pass.

| Platform | What it checks |
| --- | --- |
| iOS | Strings in the Release binary: `SocketHost`, `ReflexSocketHost`, `ReflexKit`, `InventoryIntrospection`, `AppNode` and `REFLEX LISTENING` |
| Android | Release dex classes under `reflex.kit`, `SocketHost` and `reflex.AppNode`. The `releaseRuntimeClasspath` graph for `:reflex-socket` and `:introspection`. The `INTERNET` permission. |

It needs Xcode and XcodeGen for iOS and the Android SDK for Android. Release minify is off in the sample, so the class scan proves the code was never compiled in, not that a shrinker removed it.

A red case from building it: the first iOS setup linked the package products in every configuration and the Release binary held `SocketHost` strings. Marking them `link: false` and linking them only from Debug `OTHER_LDFLAGS` brought Release to zero.

At runtime the Release app launched with `-reflexPort 47814` and the release APK launched with `--ei reflexPort 47815` both drew the list and opened no port.

## The runner

A platform with `socket` connects instead of starting a process per journey. An optional `command` starts one long-lived host for the whole run.

```json
"swift-live": {"socket": "127.0.0.1:47811", "command": ["{root}/samples/outbox/swift/.build/debug/outbox-cli", "fake", "--listen", "47811"]}
```

Only loopback addresses are accepted. State carries across journeys, so each live journey must leave the app as it found it. `--repeat` checks every repeat but does not compare transcripts. Exit codes and the network guard do not apply, so a clean live run ends `RESULT PASS-UNGUARDED`. A platform whose port does not accept ends `RESULT FAIL` with exit 2.

Try it with the outbox CLIs, no device needed:

```bash
bash scripts/build.sh
python3 runner/reflex_runner.py samples/outbox/live.json --platform both --repeat 2 --allow-unguarded
```

`runner/red/live-leftover.json` is a red path that leaves state behind and must fail on the second repeat.

## Limits

- Tested on one iOS 26.5 iPhone 17 simulator and one Android 16 (API 36) ATD emulator on an Apple silicon Mac. Not on a physical phone.
- The network guard cannot run inside an app, so live runs never prove network isolation. Keep the CLI suite for that.
- The live journey and the UI check cover the list and detail screens and Save. The save failure screen is not driven live.
- A debug build with the opt-in accepts any local process for as long as it runs. Use it on your own machine and device only.
- CI runs the exclusion check. It does not boot a simulator or an emulator.

Raw logs and screens: [evidence/live-ui-2026-11-06](../evidence/live-ui-2026-11-06/README.md).
