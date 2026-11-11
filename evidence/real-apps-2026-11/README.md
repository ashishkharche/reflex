# Reflex on real open-source apps, 10 Nov 2026

Five well-known open-source apps, one main screen each, set up the way `/reflex-start` and [docs/add-to-your-app.md](../../docs/add-to-your-app.md) describe. Each app was a shallow clone outside this repo on a local `reflex/<screen>` branch. Nothing was pushed to the apps. No app code is in this repo: only logs.

Machine: MacBook Pro, Apple silicon, macOS 26.3.1, JDK 17, Flutter 3.47.9, Xcode 26.5. Times are wall clock from clone to a passing run and include the build fixes below.

## Results

| App | Stack | Screen | Time | Result |
| --- | --- | --- | --- | --- |
| KMP App Template (JetBrains) | Kotlin Multiplatform, Compose Multiplatform, Koin | Museum list and detail | 10 min | PASS, no app change |
| Now in Android (Google) | Jetpack Compose, Hilt, ViewModels in Android library modules | For You | 12 min | PASS, no app change |
| Compass (Flutter samples) | Flutter, Provider, `ChangeNotifier` ViewModels with commands | Home | 9 min | PASS, no app change |
| Fossify Calculator | Android Views, logic in a helper class that takes a `Context` | Calculator | 5 min | PASS on the main path. Divide by zero is `xfail` |
| Ice Cubes | SwiftUI, iOS-only Swift packages | Timeline | 2 min | Stopped: the packages don’t build for macOS |

React Native and a UIKit app were not tried. See [Not done](#not-done).

## What each app showed

**KMP App Template.** The list ViewModel is an androidx `ViewModel` whose only state is a `StateFlow` made with `stateIn(viewModelScope, WhileSubscribed(5000))`. The CLI depends on the shared module’s JVM target, as the desktop app does. The adapter adds `Open` and `Back` around `DetailViewModel`, since navigation lives in Compose. Fixture: a fake `MuseumApi`, so the Ktor client never runs. Three build fixes: add the lifecycle ViewModel library (`Cannot access 'androidx.lifecycle.ViewModel'`), exclude duplicate jar names in `installDist` and clear a stale install folder. Then the list stayed `[]` for ever: no `Dispatchers.Main` on the JVM, and nothing collected the `WhileSubscribed` flow. `kmp-template-runner-nomain.log` shows the old result: one step fails with `expected=2 items actual=0 items`, and the empty-list journey passes for the wrong reason. Parity: the iOS app runs the same Kotlin code inside Compose, so a Kotlin/JVM host covers it. A Kotlin/Native host would only repeat it.

**Now in Android.** `ForYouViewModel` takes six dependencies and an assisted key through Hilt. Hilt didn’t get in the way: the constructor is public and the app ships test doubles in `core:testing`. The ViewModel lives in an Android library module, so a JVM CLI can’t depend on it. A small library module `reflexForYou` holds the host in `src/test` and runs it on that module’s unit test classpath, including AGP’s stub `android.jar`, through a Java `@` argument file. The host needed exactly what the app’s own `ForYouViewModelTest` does: `Dispatchers.setMain(UnconfinedTestDispatcher())` and a collector for each `WhileSubscribed` flow. Then every reply was settled, with no `eventually` steps. Without the collector the feed stays at loading (`nia-runner-nocollect.log`). Without Main, actions that launch in `viewModelScope` don’t show in the reply (`nia-runner-nomain.log`). The kit’s Gradle file failed under the app’s isolated projects setting and was fixed. The app built with `../reflex` moved away and its own ViewModel tests passed.

**Compass.** `HomeViewModel` extends `ChangeNotifier` from `package:flutter`, so `dart run` fails with `dart:ui is not available`. The same host compiled to a kernel file runs unchanged on `flutter_tester`, which has `dart:ui` and reads stdin. The app’s `testing/` fakes are the fixtures. Two host fixes: `flutter_tester` doesn’t pass arguments to `main`, and commands are async, so replies showed `deleting: true` before the delete finished (`compass-runner1.log`). A probe that opens a socket inside `flutter_tester` ended `network=denied`, so the guard holds there (`compass-runner-network-probe.log`). The sample’s pub workspace needs the whole samples repo, so `resolution: workspace` was removed locally for the sparse clone. The app’s home widget tests still pass.

**Fossify Calculator.** No ViewModel: `CalculatorImpl` takes a callback and a `Context`, digits arrive as `R.id` values and history goes to Room through the `Context`. With no library module, the host sits in the app module’s `src/test`, with `isReturnDefaultValues` and a stand-in `ContextWrapper`. 7 + 5 = 12, decimals, clear and reset all pass. Divide by zero reports its error only as a toast, which the stub `android.jar` can’t build, so the host stops. That journey is `xfail` (`calc-final.log`). Seeing the error needs a small refactor: report it through the callback, as state.

**Ice Cubes.** `TimelineViewModel` is `@MainActor @Observable` with an injectable status fetcher, which would suit a fixture. Its packages declare only iOS and so do dependencies such as Bodega and SQLite. `swift build` on macOS fails at resolution, even after adding `.macOS(.v15)` to the app’s own packages (`icecubes-macos-build2.log`). A Swift host for such an app has to run in the iOS simulator. Reflex has no host for that today.

## Lessons

1. Modern Android ViewModels are not in JVM modules. Asking for a JVM Core would mean a refactor nobody wants. The module’s unit test classpath already runs them.
2. The silent failures were the expensive ones. A missing `Dispatchers.Main` or a missing collector gives a frozen first state, no error, and a journey that can pass for the wrong reason.
3. A host should do what the app’s own ViewModel tests do. Both Android apps already had the dispatcher rule and the collectors.
4. Apps with test fakes (Now in Android, Compass) were the quickest. The fakes became fixtures with no new code.
5. Real Flutter ViewModels import Flutter. A plain Dart host only fits the sample.
6. Async actions need the reply to wait. Otherwise every step sees work in flight.
7. Errors shown only as a toast or a snackbar are invisible to Reflex. That is the refactor to ask for.

## Kept

| Change | Proof on a real app |
| --- | --- |
| Kotlin kit warns when coroutines are present and `Dispatchers.Main` is missing. The runner prints `ReflexKit warning:` lines as `WARN`, even on a pass. | KMP App Template without Main: `WARN` names the cause and the fix, including on the journey that passed for the wrong reason (`kmp-template-runner-nomain-after.log`). No warning once Main is set (`kmp-template-final.log`, `nia-runner-pass-after.log`). |
| Kit Gradle file works with isolated projects. | Now in Android failed before the fix (`nia-build1.log`) and built after it. |
| Guard found in the Reflex clone when the manifest has no `guard`. | The first KMP run stopped with a Python traceback: clang could not find `scripts/network_guard.c` in the app (that log was overwritten). All four app manifests run with no `guard` block. |
| `host input not found` with exit 2 for a missing classpath folder or `@` file. | KMP with no install folder: one clear line instead of every step failing with EOF and `ClassNotFoundException` (`kmp-template-runner-unbuilt.log`). |
| stateKeys hint only with two or more platforms. | Now in Android with one platform: the old hint pointed at stateKeys for a feed stuck at loading (`nia-runner-nocollect.log`). It is gone (`nia-runner-nocollect-after.log`). |
| Host stderr: a `STDERR` line for a failed journey, and the exception line of a crash. | Fossify Calculator: the crash now reads `NullPointerException: getString(...) must not be null` instead of the end of a stack trace (`calc-runner1.log` before, `calc-runner2.log` after). |
| `{flutter_tester}` and `runner/flutter_kernel.py`. Dart host waits for async actions and reads the fixture on `flutter_tester`. | Compass passes with no app change (`compass-runner-pass.log`). Before, replies showed work in flight and the fixture was ignored (`compass-runner1.log`). |
| Runner `WARN … node.state never changed` when a step expected a change after an action or while polling and the state stayed as it was. Added 11 Nov. | KMP App Template with the list collector removed: before, one `eventually` failure with `0 items` and no cause (`kmp-warn-nocollect-before.log`). After, the same failure plus a `WARN` naming `stateIn(WhileSubscribed)` with no subscriber among the causes (`kmp-warn-nocollect-after.log`). No warning on the working adapter, repeat 3 (`kmp-warn-final.log`). |
| Guide: ViewModels in Android modules, `viewModelScope` and `stateIn`, Flutter apps. | Written from the Now in Android, KMP App Template and Compass setups. |

## Dropped

- A Kotlin kit module with its own Main dispatcher and flow collectors. Both apps needed two lines that Android developers already write in ViewModel tests. A second kit module, with a coroutines dependency, cost more than it saved. The warning and the guide cover it.
- A Gradle plugin that writes the unit test classpath. The task is 15 lines, and app builds differ in flavors and convention plugins.
- A Robolectric based host for code that needs a real `Context`. It would hide the refactor Reflex should ask for, and Robolectric is not built to run outside JUnit.
- An iOS simulator host for iOS-only Swift packages through `simctl spawn`. Too large to build and prove in this pass.

## Not done

- React Native: no real app was tried. The popular ones need large `node_modules` and free disk was near the 10 GB limit at one point.
- UIKit: no real UIKit app was tried. Wikipedia and similar apps are large Xcode builds.
- Ice Cubes stopped at the macOS build. No app was launched on a simulator or emulator in this pass.
