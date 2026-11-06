<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/brand/readme-banner-dark.png">
    <img src="assets/brand/readme-banner-light.png" alt="Reflex" width="100%">
  </picture>
</p>

Reflex is a UI-free Core with Elm-style ViewModels, a strict Introspection Kit for Swift and Kotlin and a platform-agnostic CLI (`ls` / `do`) over NDJSON. Shared journey files drive both platforms the same way. This project isn’t affiliated with or endorsed by Shopify. Architecture notes: https://shopify.engineering/reflex

`ls` lists the current state and the available actions. `do` runs one action and returns the new state.

## Use cases

- Test app logic with no UI by driving `ls` and `do` over NDJSON.
- Prove iOS and Android parity from one shared journey file.
- Cover behaviour that is hard to test on a device, such as timers backoff and an offline outbox.
- Run fast CI checks on the Core without a simulator or emulator.
- Let an agent explore and assert state through the same protocol a human uses.

## Requirements

- macOS. The process egress guard loads through `DYLD_INSERT_LIBRARIES` and works on macOS only. Off macOS the runner prints `guard=skipped-not-macos` and network isolation is not exercised.
- Xcode command line tools with Swift 6.0 or newer (`swift-tools-version: 6.0`).
- JDK 17 or newer (Kotlin targets JVM 17).
- Python 3.
- Git.
- Optional mobile hosts: Xcode with an iOS simulator SDK, XcodeGen, Android SDK platform 36 and build-tools 36.0.0.

Gradle downloads its pinned distribution and Maven dependencies during the first build. Behavior sessions cannot use the network.

## Setup

```bash
git clone https://github.com/ashishkharche/reflex.git
cd reflex
bash scripts/build.sh
swift test --package-path kit -j 2
swift test --package-path swift -j 2
swift test --package-path samples/outbox/swift -j 2
kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :reflex-kit:test :core:test --console=plain
kotlin/gradlew -p samples/outbox/kotlin --no-daemon --max-workers=1 :core:test --console=plain
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --strict
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both --strict
python3 scripts/check_docs.py
```

`RESULT PASS` with `guard=canary-pass` means every shared journey passed on both native Cores with strict full-JSON parity and a guard canary proved that network attempts are denied. Off macOS the line ends `guard=skipped-not-macos network_isolation=NOT-exercised`. The kit tests run `kit/conformance/strict-decoder.json` on each platform. Warm timings exclude process startup and follow one full warm-up journey. Builds run one at a time with two Swift jobs and one Gradle worker without a daemon.

Explore with:

```bash
printf 'ls\ndo OpenProduct {"id":"shirt"}\ndo SetQuantity {"quantity":12}\ndo Save\nls\n' | python3 scripts/console.py swift
python3 scripts/console.py kotlin
python3 scripts/console.py swift outbox
```

The console sends `hello` first. Type `ls`, `do OpenProduct {"id":"shirt"}`, `do SetQuantity {"quantity":12}`, `do Save` or `do goBack`. In the outbox try `do Enqueue {"key":"a","body":"hi"}`, `op network {"script":["lost"]}`, `op advance {"ms":0}` and `op advance {"ms":1000}`. End input with Ctrl-D. Every response is JSON. Raw protocol: [docs/protocol/v1.md](docs/protocol/v1.md).

## Adopt ReflexKit

Keep the Core free of the kit. Add one adapter node per ViewModel in a separate introspection target and a small CLI. Short guide with Swift and Kotlin examples: [kit/README.md](kit/README.md). Protocol rules: [docs/protocol/v1.md](docs/protocol/v1.md).

## Layout

- `kit/`: ReflexKit Swift package, Kotlin module `kit/kotlin` and the shared conformance fixture.
- `runner/`: journey runner, conformance table tool and red-path fixtures.
- `swift/`: inventory Swift Core, kit adapters and the macOS CLI.
- `kotlin/`: inventory JVM Core, kit adapters, JVM CLI and Compose host.
- `mobile/ios/`: SwiftUI host.
- `samples/outbox/`: outbox sample with its own Swift package, Gradle build and journeys.
- `tests/inventory/`: inventory manifest and shared journeys.
- `scripts/network_guard.c`: macOS process egress guard for behavior sessions.
- [docs/architecture.md](docs/architecture.md), [docs/testing.md](docs/testing.md), [TEST_PLAN.md](TEST_PLAN.md), [docs/ux-writing.md](docs/ux-writing.md), [docs/brand.md](docs/brand.md).

The samples keep fixture data in process memory. No production inventory endpoints or credentials are used.

## Licence

MIT. Copyright (c) 2026 Ashish Kharche. See [LICENSE](LICENSE).
