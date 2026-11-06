# Setup

Clone this repository and run the inventory sample on Swift and Kotlin. For adding Reflex to your own app, use [add-to-your-app.md](add-to-your-app.md).

## Prerequisites

- macOS when you use the Swift (iOS) side or the network guard (`DYLD_INSERT_LIBRARIES`)
- Xcode with Swift 6.0 or newer (`swift-tools-version: 6.0`) for Swift / iOS
- JDK 17 or newer (Kotlin targets JVM 17)
- Python 3
- Git
- Optional mobile hosts: iOS simulator SDK, XcodeGen, Android SDK platform 36 and build-tools 36.0.0

Linux, Docker and Linux CI work for Kotlin-only and Kotlin Multiplatform apps with `--platform kotlin`. The network guard is skipped there. Windows works through WSL 2. Details: [faq.md](faq.md).

Gradle downloads its pinned distribution on the first build. Behavior sessions cannot use the network.

## Clone

```bash
git clone https://github.com/ashishkharche/reflex.git
cd reflex
```

## Build and Swift tests

`scripts/build.sh` builds the network guard and both sample CLIs.

```bash
bash scripts/build.sh
swift test --package-path kit -j 2
swift test --package-path swift -j 2
```

Expect `CONFORMANCE platform=swift cases=161 passed=161` and `Test Suite 'All tests' passed`.

## Kotlin tests

```bash
kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :reflex-kit:test :core:test --console=plain
```

Expect `ConformanceTest` lines marked `PASSED` and `BUILD SUCCESSFUL`.

## Shared journeys

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both
```

Expect `RESULT PASS`. Off macOS the line includes `guard=skipped-not-macos`.

## Explore by hand

```bash
python3 scripts/console.py swift
```

Type `ls` and `do OpenProduct {"id":"shirt"}`. Raw protocol: [protocol/v1.md](protocol/v1.md).

## Outbox sample

```bash
swift test --package-path samples/outbox/swift -j 2
kotlin/gradlew -p samples/outbox/kotlin --no-daemon --max-workers=1 :core:test --console=plain
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both
python3 scripts/check_docs.py
```

## Layout

| Path | Role |
| --- | --- |
| `kit/` | ReflexKit Swift + Kotlin |
| `runner/` | Journey runner |
| `swift/`, `kotlin/` | Inventory sample |
| `samples/outbox/` | Outbox sample |
| `tests/inventory/` | Inventory journeys |
| `scripts/network_guard.c` | macOS egress guard |

More: [docs index](README.md).
