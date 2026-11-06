# Setup

macOS is required for the network guard. Off macOS the runner prints `guard=skipped-not-macos` and network isolation is not exercised.

## 1. Prerequisites

You need:

- macOS. The process egress guard loads through `DYLD_INSERT_LIBRARIES` and works on macOS only.
- Xcode with Swift 6.0 or newer (`swift-tools-version: 6.0` in every Swift package).
- JDK 17 or newer (Kotlin targets JVM 17).
- Python 3.
- Git.
- Optional mobile hosts: Xcode with an iOS simulator SDK, XcodeGen, Android SDK platform 36 and build-tools 36.0.0.

Gradle downloads its pinned distribution and Maven dependencies during the first build. Behavior sessions cannot use the network.

## 2. Clone

```bash
git clone https://github.com/ashishkharche/reflex.git
cd reflex
```

## 3. Run the Swift sample

`scripts/build.sh` compiles the macOS network guard and both sample CLIs. The Swift tests then prove ReflexKit’s conformance fixture and the inventory Core.

```bash
bash scripts/build.sh
swift test --package-path kit -j 2
swift test --package-path swift -j 2
```

Expect `CONFORMANCE platform=swift cases=161 passed=161` and `Test Suite 'All tests' passed` for the inventory package. Builds use two Swift jobs (`-j 2`).

## 4. Run the Kotlin sample

The Gradle modules run the same kit fixture and the inventory JVM Core. Use one worker and no daemon on a small machine.

```bash
kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :reflex-kit:test :core:test --console=plain
```

Expect each `ConformanceTest` line marked `PASSED` and `BUILD SUCCESSFUL`. The kit also records `CONFORMANCE platform=kotlin cases=161 passed=161` in its test output.

## 5. Run the shared journeys on both

One journey file drives both native CLIs. Strict mode requires full-JSON parity.

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --strict
```

Expect `RESULT PASS mode=strict unexpected_failures=0 xfail=0 platforms=swift,kotlin repeat=1 sample=inventory guard=canary-pass`. Off macOS the line ends `guard=skipped-not-macos network_isolation=NOT-exercised`.

### Outbox sample

```bash
swift test --package-path samples/outbox/swift -j 2
kotlin/gradlew -p samples/outbox/kotlin --no-daemon --max-workers=1 :core:test --console=plain
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both --strict
python3 scripts/check_docs.py
```

Warm timings and repeat runs: [testing.md](testing.md).

## Explore

```bash
printf 'ls\ndo OpenProduct {"id":"shirt"}\ndo SetQuantity {"quantity":12}\ndo Save\nls\n' | python3 scripts/console.py swift
python3 scripts/console.py kotlin
python3 scripts/console.py swift outbox
```

The console sends `hello` first. Type `ls`, `do OpenProduct {"id":"shirt"}`, `do SetQuantity {"quantity":12}`, `do Save` or `do goBack`. End input with Ctrl-D. Every response is JSON. Raw protocol: [protocol/v1.md](protocol/v1.md).

## Add it to your own app

Keep the Core free of the kit. Add one adapter node per ViewModel in a separate introspection target and a small CLI. Short guide: [kit/README.md](../kit/README.md).

## Layout

- `kit/`: ReflexKit Swift package, Kotlin module `kit/kotlin` and the shared conformance fixture.
- `runner/`: journey runner, conformance table tool and red-path fixtures.
- `swift/`: inventory Swift Core, kit adapters and the macOS CLI.
- `kotlin/`: inventory JVM Core, kit adapters, JVM CLI and Compose host.
- `mobile/ios/`: SwiftUI host.
- `samples/outbox/`: outbox sample with its own Swift package, Gradle build and journeys.
- `tests/inventory/`: inventory manifest and shared journeys.
- `scripts/network_guard.c`: macOS process egress guard for behavior sessions.

The samples keep fixture data in process memory. No production inventory endpoints or credentials are used.
