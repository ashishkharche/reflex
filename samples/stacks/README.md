# Stack checks

One small counter on each popular mobile stack, driven by one shared journey (`journeys/counter.json`). Each stack keeps a ViewModel with `send` and no UI imports, a screen that uses it and a Reflex host for the runner. The journey counts up and down, clamps at 0 and 99 and sends bad input that must be rejected before the ViewModel sees it.

| Stack | Folder | Host | Manifest |
| --- | --- | --- | --- |
| UIKit | `uikit/` | Swift kit | `native.json` |
| Android Views | `android/views-*` | Kotlin kit | `native.json` |
| Java on Android | `android/java-*` | Kotlin kit over a Java ViewModel | `native.json` |
| Kotlin Multiplatform | `kmp/` | Kotlin kit on JVM and Swift kit on Kotlin/Native | `kmp.json` |
| Compose Multiplatform | `cmp/` | Kotlin kit on JVM and Swift kit on Kotlin/Native | `cmp.json` |
| Flutter | `flutter/` | Minimal Dart host in `lib/reflex/host.dart` | `flutter.json` |
| React Native | `react-native/` | Minimal Node host in `src/reflexHost.js` | `react-native.json` |

`all.json` runs every host in one go. Parity compares each host with `uikit`. The `hello` step is marked `host-kit` because the Dart and Node hosts report their own kit name. Every other reply must match byte for byte.

## Build the hosts

Run these from the repo root. JDK 17 or newer, Xcode and Swift 6 are needed. Flutter needs the Flutter SDK and React Native needs Node 18 or newer.

```bash
swift build --package-path samples/stacks/uikit/Harness -j 2
kotlin/gradlew -p samples/stacks/android --no-daemon :views-cli:installDist :java-cli:installDist
kotlin/gradlew -p samples/stacks/kmp --no-daemon :cli:installDist :shared:assembleSharedXCFramework
swift build --package-path samples/stacks/kmp/SwiftHost -j 2
kotlin/gradlew -p samples/stacks/cmp --no-daemon :cli:installDist :shared:assembleSharedXCFramework
swift build --package-path samples/stacks/cmp/SwiftHost -j 2
(cd samples/stacks/flutter && flutter pub get && dart compile exe bin/reflex_host.dart -o build/reflex-host)
(cd samples/stacks/flutter && python3 ../../../runner/flutter_kernel.py bin/reflex_host.dart build/reflex-host.dill)
python3 runner/reflex_runner.py samples/stacks/all.json --platform all --repeat 3 --timings 0
```

The Flutter host runs twice: as a `dart` executable and on `flutter_tester`, Flutter’s headless engine, as `flutter-tester`. A real Flutter ViewModel usually imports `package:flutter`, which `dart` can’t load, so apps use the second way ([Flutter apps](../../docs/add-to-your-app.md#flutter-apps)).

The React Native host needs no build. Its screen test needs `npm install` and `npx jest` in `react-native/`. Keep `node_modules` out of the repo.

## Build the apps

These prove each screen compiles against the same ViewModel the host serves. Android builds take `-Pmobile=true` and need the Android SDK.

```bash
(cd samples/stacks/uikit/App && xcodegen generate && xcodebuild -scheme CounterUIKit -sdk iphonesimulator -derivedDataPath .build/ios build)
kotlin/gradlew -p samples/stacks/android -Pmobile=true --no-daemon :views-app:assembleDebug :java-app:assembleDebug
kotlin/gradlew -p samples/stacks/kmp -Pmobile=true --no-daemon :androidApp:assembleDebug :shared:linkDebugFrameworkIosSimulatorArm64
(cd samples/stacks/kmp/iosApp && xcodegen generate && xcodebuild -scheme CounterKMP -sdk iphonesimulator -derivedDataPath .build/ios build)
kotlin/gradlew -p samples/stacks/cmp -Pmobile=true --no-daemon :androidApp:assembleDebug :composeApp:linkDebugFrameworkIosSimulatorArm64
(cd samples/stacks/cmp/iosApp && xcodegen generate && xcodebuild -scheme CounterCMP -sdk iphonesimulator -derivedDataPath .build/ios build)
(cd samples/stacks/flutter && flutter test)
```

The Flutter folder has no `ios/` or `android/` shell. Run `flutter create --platforms=ios,android .` in a copy to build the app. The React Native folder has no app shell either: the screen is checked with Jest and the React Native preset.

## Limits

- The apps were built, not launched. The inventory sample covers a running app through the [debug socket](../../docs/real-build.md).
- The Dart and Node hosts handle integer, string and boolean fields, strict JSON and canonical output. They don’t handle object or array fields and don’t run the kit conformance file.
- The Compose Multiplatform Android app needs compileSdk 37 because Compose 1.12 asks for it.

Results and logs: [evidence/stacks-2026-11-10](../../evidence/stacks-2026-11-10/README.md).
