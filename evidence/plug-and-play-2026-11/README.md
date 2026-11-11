# Plug and play, 11 Nov 2026

`runner/reflex_init.py` run on fresh clones of six open-source apps, with no hand-written adapter, CLI or manifest. Each log is one run from the app’s root on a MacBook Pro with Apple silicon. Paths are shortened to `~/apps`.

| App | Stack | Plug and play | Time to first pass | Manual step |
| --- | --- | --- | --- | --- |
| [KMP App Template](kmp-app-template.log) | Kotlin Multiplatform | Yes | 8 s | None |
| [Now in Android](now-in-android.log) | Android, Compose | Yes | 16 s | None |
| [Flutter Compass](flutter-compass.log) | Flutter | Yes | 3 s | Clone all of `flutter/samples` (see below) |
| [Ignite boilerplate](ignite.log) | React Native | Yes, after `npm install` | 3 s | The app’s own `npm install` |
| [Ice Cubes](ice-cubes.log) | SwiftUI, iOS only | Yes | 332 s | None |
| [NetNewsWire](netnewswire.log) | UIKit and AppKit | No | Stops after 30 s | A host by hand or a refactor |

Times are for the generator alone with warm Gradle, pub and SwiftPM caches. Cloning all six took 36 s. The first cold runs during development took 36 s for the KMP App Template and 58 s for Now in Android, most of it Gradle. Ice Cubes spends its time building the app’s Swift packages for the iOS simulator and booting a throwaway device. `git status` at the end of each log shows that only `tests/` was added (and `package-lock.json` from `npm install` in Ignite).

## What each run found

- **KMP App Template:** `ListViewModel` in `shared`. `InMemoryMuseumStorage` from the app and a stand-in for `MuseumApi`, so the list starts empty. No actions: the screen only reads.
- **Now in Android:** `ForYouViewModel` on the module’s unit test classpath, with the app’s `Test*` doubles from `core:testing` and a stand-in for `UserNewsResourceRepository`. Four actions, including `UpdateTopicSelection`.
- **Flutter Compass:** `HomeViewModel` with `FakeBookingRepository` and `FakeUserRepository` from the app’s tests. Actions `DeleteBooking` and `Load`. The repo is a pub workspace, so `flutter pub get` fails in a sparse clone of one app. With a full clone it passes and the generator runs it.
- **Ignite boilerplate:** the `Episodes` React context rendered with `react-test-renderer`. Actions `FetchEpisodes` and `ToggleFavoritesOnly`. `FetchEpisodes` calls the network, so it needs a fixture before a journey can use it.
- **Ice Cubes:** `TimelineViewModel` on the iOS simulator, with the app’s pinned package versions. One action, `Reset`. Its other public methods were not picked up as actions.
- **NetNewsWire:** the only state holder found is `CloudKitStatsViewModel`, not the main screen. The feed list’s state lives in a UIKit coordinator. The host also does not build: the `Account` package needs `SecretKey`, which the app’s own build step writes from a secrets file. The run stops and says to write the host by hand.

## Limits

- A stand-in returns empty values. A first run with one proves the host works, not the data path. Replace it with a fixture before testing the main action.
- Actions are public methods with simple parameters. Events sent through one `onAction(event)` method, Riverpod providers and Bloc events are not found. Node functions that take arguments are skipped.
- The first-run journey checks `hello`, the settled state and an unknown action. It does not run the main action. That journey is still written by the agent or by hand.

Run it again: `python3 ../reflex/runner/reflex_init.py` from an app’s root, with Reflex cloned next to it.
