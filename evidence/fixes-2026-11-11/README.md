# Test and fix round, 11 Nov 2026

`runner/reflex_init.py` run on fresh clones of ten more open-source apps in five stacks, plus two small repro packages for cases the apps did not hit. Each log is the last run from the app’s root on a MacBook Pro or MacBook Air with Apple silicon, after the fixes below. Paths are shortened to `~/apps`.

| App | Stack | Result | Log |
| --- | --- | --- | --- |
| [Jetcaster](https://github.com/android/compose-samples) | Android, Compose | Clear STOP: real network client | [jetcaster.log](jetcaster.log) |
| [Pokedex Compose](https://github.com/skydoves/pokedex-compose) | Android, Compose | PASS in 87 s | [pokedex-compose.log](pokedex-compose.log) |
| [PeopleInSpace](https://github.com/joreilly/PeopleInSpace) | Kotlin Multiplatform | PASS in 355 s, cold Gradle | [peopleinspace.log](peopleinspace.log) |
| [Bloc flutter_todos](https://github.com/felangel/bloc) | Flutter, Bloc | PASS in 8 s | [flutter-todos-bloc.log](flutter-todos-bloc.log) |
| [Riverpod todos](https://github.com/rrousselGit/riverpod) | Flutter, Riverpod | PASS in 11 s | [riverpod-todos.log](riverpod-todos.log) |
| [Obytes template](https://github.com/obytes/react-native-template-obytes) | React Native, Zustand | PASS in 4 s, after the app’s install | [obytes.log](obytes.log) |
| [Food Truck](https://github.com/apple/sample-food-truck) | SwiftUI | PASS in 21 s | [food-truck.log](food-truck.log) |
| [SyncUps](https://github.com/pointfreeco/syncups) | SwiftUI | Clear STOP: models in the Xcode app target | [syncups.log](syncups.log) |
| [Clean Architecture SwiftUI](https://github.com/nalexn/clean-architecture-swiftui) | SwiftUI | STOP: state lives in views | [clean-architecture-swiftui.log](clean-architecture-swiftui.log) |
| [Simplenote iOS](https://github.com/Automattic/simplenote-ios) | UIKit | STOP: no state holder | [simplenote-ios.log](simplenote-ios.log) |

Bloc and Riverpod live in their library repos (`examples/flutter_todos` and `examples/todos`). The two repros are an iOS-only Swift package ([repro-ios-only.log](repro-ios-only.log)) and a package that needs a generated `SecretKey` file ([repro-needs-setup.log](repro-needs-setup.log)).

## What was fixed

- **Gradle:** the init script ran with configure on demand, so `reflexClasspath` was missing in some modules. Gradle now runs without it. When the default JDK is newer than Gradle supports, it runs on JDK 21 or 17 and says so before the build.
- **Kotlin actions:** an `onAction(event)` method gives one action per event, and data class arguments take their fields as input.
- **Flutter:** Bloc events and Riverpod `Notifier` providers are found. Named and private named parameters, enums and app model fields work. Mock test doubles count as stand-ins.
- **React Native:** Zustand stores behind a wrapper such as `createSelectors` are found and native modules get stand-ins.
- **Swift:** a target’s `path:` is read, actions take `String`, `Int`, `Bool` and `ID` arguments and `@Published` values show as values. The reason for the simulator build names the iOS-only declaration.
- **First journey:** it also runs up to three actions that need no input, work offline and end in the same state each time.
- **Clearer STOP lines:** a real network client names the chain to it, a model in an Xcode app target says to move it into a package and a package that needs its own setup step says to run it first.
- **Read-only clone:** the network guard builds next to the manifest when the Reflex clone can’t be written.
- **Simulator first reply:** a host on a freshly booted iOS simulator gets 30 seconds for its first reply. With 6 seconds one probe timed out and the first journey left out `Increment`.

## Still open

- Two runs that use the iOS simulator at the same time can fail. Run them one after the other.
- Jetcaster stops because `PodcastsRepository` reaches a real `OkHttpClient`. It needs a test double or another screen.
- SyncUps, Clean Architecture SwiftUI and Simplenote keep their state in an Xcode app target, in views or in UIKit. They need a refactor or a host by hand.
- The first journey proves the setup and actions that need no input. The main action with sample data is still written by hand.
