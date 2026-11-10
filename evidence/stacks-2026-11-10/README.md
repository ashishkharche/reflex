# Stack checks, 10 Nov 2026

Mac: Apple silicon, macOS 26.3.1. Xcode 26.5 with Swift 6.3.2. Gradle 9.8.2 on JDK 21 with Kotlin 2.4.21, AGP 9.5.0 and Compose Multiplatform 1.12.2. The runner used Python 3.13.5 and OpenJDK 23. Flutter 3.47.9 with Dart 3.13.7. Node 22.23.4 with React Native 0.88.1, React 19.3.0 and Jest 29. Code: `samples/stacks/`.

## Results

Every run used the network guard and its canary passed. `--repeat 3` means three fresh runs per host with identical raw transcripts.

| Stack | Host | Journey | Parity | App build | Log |
| --- | --- | --- | --- | --- | --- |
| UIKit | Swift kit | PASS | reference | iOS simulator, BUILD SUCCEEDED | `native-runner.log`, `uikit-app-xcodebuild-tail.log` |
| Android Views | Kotlin kit | PASS | bytes match uikit | debug APK, BUILD SUCCESSFUL | `native-runner.log`, `android-apps-build-tail.log` |
| Java on Android | Kotlin kit over Java | PASS | bytes match uikit | debug APK, BUILD SUCCESSFUL | `native-runner.log`, `android-apps-build-tail.log` |
| Kotlin Multiplatform | Kotlin kit on JVM, Swift kit on Kotlin/Native | PASS on both | bytes match | Android app and iOS simulator app | `kmp-runner.log`, `kmp-*-tail.log` |
| Compose Multiplatform | Kotlin kit on JVM, Swift kit on Kotlin/Native | PASS on both | bytes match | Android app and iOS simulator app | `cmp-runner.log`, `cmp-*-tail.log` |
| Flutter | Minimal Dart host, native executable | PASS | bytes match after `hello` | iOS simulator and debug APK, widget test passed | `flutter-*.log` |
| React Native | Minimal Node host | PASS | bytes match after `hello` | not built, Jest screen test passed | `react-native-*.log` |

`all-runner.log` runs all nine hosts in one manifest: `RESULT PASS`, 160 compared steps, 0 unexpected diffs, 0 byte diffs and 2 known diffs. The known diffs are the `kit` field in the Dart and Node `hello` replies.

## Red path

`red-react-native-clamp.log`: the Node ViewModel’s upper clamp was changed from 99 to 98 for one run. The journey failed at steps 17 and 18 with `expected=99 actual=98`, parity printed two `PARITY DIFF` lines and the run exited 1. The change was reverted.

## Not covered

- No app was launched on a simulator, emulator or phone. Builds prove each screen compiles against the ViewModel the host serves.
- The React Native iOS and Android shells were not built. The screen ran under Jest with the React Native preset.
- The Flutter platform shells came from `flutter create` in a copy outside the repo.
- The Dart and Node hosts were not run against `kit/conformance/strict-decoder.json`. They have no object or array fields.
- Expo and .NET MAUI were not tried.

Build logs are the last lines of each build. The full logs stayed on the Mac.
