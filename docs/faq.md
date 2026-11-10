# FAQ

Short answers for environments, tech stacks, workflows and safety. For setup steps see [add-to-your-app.md](add-to-your-app.md). Protocol rules: [protocol/v1.md](protocol/v1.md).

## Compatibility

| Stack or OS | Works? | What you need |
| --- | --- | --- |
| macOS + SwiftUI + Jetpack Compose | Yes, tested | Xcode, JDK 17+, Python 3. Full path including the network guard. The inventory sample apps use SwiftUI and Compose. |
| UIKit or Android Views | Should work, untested | The Core and adapters never import UI code, so the UI toolkit doesn’t matter to Reflex. No sample uses UIKit or Views yet. |
| Java on Android | Should work, untested | The Kotlin kit runs on the JVM. Write the adapter and CLI in Kotlin around the Java ViewModel. No sample uses Java. |
| Linux (desktop, server or CI) | With limits | Python 3 and a JVM host work. The network guard runs through `LD_PRELOAD` when `cc` is installed. Tested on one Debian 13 x86_64 host only. The Swift kit’s `Package.swift` declares macOS and iOS only, so a Swift host on Linux is untested. `scripts/build.sh` builds a `.dylib` and expects macOS. |
| Windows native | No | The runner uses `select` on process pipes (`runner/reflex_runner.py`), which Python on Windows does not support for pipes. Use WSL 2 instead. |
| WSL 2 | With limits | Same as Linux. Use Linux paths in the manifest. Not tested yet. |
| Docker | With limits | Same as Linux inside the container. Mount the repo, install JDK, Python and `cc`, run the Kotlin (or other) host. Not tested yet. |
| GitHub Actions / CI | Yes on macOS | This repo’s workflow runs on `macos-latest` (`.github/workflows/behavior.yml`). Linux runners need `cc` for the guard. Not tested on a Linux runner yet. |
| iOS-only or Android-only | Yes | Put one platform in the manifest. Run `--platform swift` or `--platform kotlin` (or that platform’s name). Parity across platforms is skipped when only one runs. |
| Kotlin Multiplatform (shared Kotlin logic) | Should work, untested | One Kotlin/JVM CLI can cover the shared ViewModel. Run `--platform kotlin`. A second host is optional when there is no separate Swift Core. No KMP sample in this repo yet. |
| Compose Multiplatform | Should work, untested | Same as KMP when logic lives in Kotlin. |
| Flutter | Not out of the box | No Dart kit. A Dart process that speaks [protocol v1](protocol/v1.md) over stdin/stdout can work. Prove it with `kit/conformance/strict-decoder.json`. |
| React Native / Expo | Not out of the box | No JS/TS kit. A Node host that speaks protocol v1 can work. Same conformance file. |
| .NET MAUI / Xamarin | Not out of the box | No .NET kit. A C# host that speaks protocol v1 can work. Same conformance file. |
| Ionic / Capacitor | Not out of the box | Same as React Native: build a JS/TS host for protocol v1. |
| Web-only apps | No | The runner drives CLI processes over stdio, not a browser. Put shared logic in a Node (or other) host if you still want journeys. |
| Logic only on a backend | No | Reflex tests the app Core in-process. Point the CLI at fakes, not at production servers. |

## Environments

**Does it work on a Linux server or in CI without a Mac?**

The runner is plain Python 3 and starts whatever command the manifest lists (`runner/reflex_runner.py`). On Linux it builds the network guard with `cc` and loads it through `LD_PRELOAD`. Without a compiler it prints `GUARD SKIP` and ends with `RESULT PASS-UNGUARDED` (exit 3) instead of `PASS`. Kotlin/JVM CLIs run on Linux with JDK 17+. A full Swift + Kotlin sample build via `scripts/build.sh` expects macOS (it compiles `network_guard.c` into a `.dylib`).

**Does it work on Windows?**

Not natively. The runner’s `Host._read_line` calls `select.select` on the child process’s stdout pipe. On Windows that API only accepts sockets, so the runner fails there. WSL 2 works with the Linux limits above. Git Bash alone is not enough for the runner’s pipe I/O.

**Does the network guard work off macOS?**

On Linux, yes. The same `scripts/network_guard.c` builds as a shared library and loads through `LD_PRELOAD`. It denies Internet `connect` and `sendto`. The runner proves that with a canary before any journey. It only sees calls through the C library, so a static binary or a raw system call gets past it.

What was tested on 6 Nov 2026: one Debian 13 x86_64 host with glibc 2.41, Python 3.13 and a Temurin 21 JRE, running the inventory and outbox Kotlin hosts with `--platform kotlin --repeat 3`. Both passed with the guard and both tripwire journeys reported `network=denied`. A guard that never denies failed the canary with exit 2. The Kotlin jars were built on macOS. Swift on Linux, ARM Linux, Alpine (musl), Docker, WSL 2 and Linux CI runners are not tested. Logs: `evidence/linux-guard-2026-11-06/`.

Windows has no guard. Any run without the guard, including `--no-guard`, ends `RESULT PASS-UNGUARDED` and exits 3. Pass `--allow-unguarded` to exit 0 when you accept that.

**Can I run only one platform?**

Yes. `--platform` accepts one name, a comma list or `both`/`all` (every platform in the manifest). Example: `python3 runner/reflex_runner.py tests/reflex.json --platform kotlin`.

**Does the runner care which language the host is written in?**

No. A platform entry is just a `command` argv list. `{java}`, `{node}`, `{root}`, `{fixture}` and `{python}` are substituted. Any program that speaks protocol v1 on stdin/stdout can be a host.

## Tech stacks

**SwiftUI / UIKit with Jetpack Compose / Android Views**

This is the path the samples and [add-to-your-app.md](add-to-your-app.md) document. The sample apps use SwiftUI and Jetpack Compose. UIKit and Android Views should work the same way but are untested. Keep a UI-free Core, add a ReflexKit adapter and a small CLI per platform, then share journeys.

**My app has no ViewModels and state lives in the views**

Extract a ViewModel (or an equivalent object with state + `send`) before the adapter can wrap it. The README prompt tells the assistant to stop and ask before that refactor.

**Redux, MVI, TCA, Bloc, Riverpod or similar**

Works when you can read a serialisable snapshot and dispatch named actions. The adapter maps store state to JSON and each action name to a dispatch. Keep UI frameworks out of the Core module the CLI links.

**Timers, network calls and databases inside the ViewModel**

Inject clocks, transports and stores through the constructor. The outbox sample uses a `FakeClock` and an `advance` host op so journeys move time without sleeping (`samples/outbox`). Inventory uses named fixtures (`happy`, `save-failure`, `network`, …) selected by the CLI’s first argument. Do not call production endpoints from a behavior session.

**What if state changes after the reply, on a background thread?**

Use an `eventually` step. It polls `ls` up to a deadline without sending the action again and prints the last state if time runs out. A `before` key checks a precondition before a step is sent. Your host must handle requests and background changes under one lock. Example: `samples/outbox/journeys/17-eventually.json`. Details: [runner/README.md](../runner/README.md).

**Kotlin Multiplatform**

If iOS and Android share one Kotlin ViewModel, one JVM CLI is enough to test that logic. Add a Swift host only when you also keep a separate Swift Core you care about parity with.

**Flutter, React Native, .NET MAUI and other non-Swift/Kotlin stacks**

There is no kit in those languages yet. The wire format is language-agnostic NDJSON ([protocol/v1.md](protocol/v1.md)). To support one, build a host that implements framing, `hello` / `ls` / `do`, strict decoding and canonical output, then run it under the runner and against `kit/conformance/strict-decoder.json` (142 decoder cases and 19 matcher cases).

**Xcode project with no Swift package**

Supported. Put the Core in a local Swift package with no UIKit/SwiftUI imports. The Introspection target and the CLI go in a separate harness package that depends on the Core and ReflexKit. The Xcode project never references the harness or the Reflex clone, except in Debug for the optional [socket host](real-build.md). Details: [2. Swift](add-to-your-app.md#2-swift).

**Gradle without Android application modules**

Fine. The kit and sample CLIs are JVM modules. You only need an Android app module if you also ship the Compose UI from the same repo.

## Workflows

**Monorepo vs separate iOS and Android repos**

Both work. The runner never needs the two apps in one tree; it only needs each platform’s command. See “If iOS and Android are separate repos” in [add-to-your-app.md](add-to-your-app.md).

**Where does the Reflex clone live?**

Next to your app (for example `../reflex`), not inside it. A git submodule is optional. Only the Reflex harness package and a guarded block in `settings.gradle.kts` point at it, so the app builds without the clone.

**How do I set it up or update with an AI assistant?**

Install the Reflex skills and run `reflex-start` ([assistants.md](assistants.md)). Without skills, paste the single prompt in the [README](../README.md). If no clone or submodule exists next to the repo, the assistant clones and sets up. If one exists, it pulls latest, reads `CHANGELOG.md` and applies changes. Both paths rebuild, run the runner, build both apps, run their unit tests and finish with the five-part report.

**Which assistants have Reflex skills?**

Claude Code, Grok Build and Codex install the `reflex` plugin from this repo. Cursor reads `.cursor-plugin/` but was not tested. Any assistant that reads Agent Skills folders can use `skills/` directly. Commands and what was tested are in [assistants.md](assistants.md).

**Why does the report say INCOMPLETE when the runner passed?**

PASS means the tests drove your real Core on every platform with nothing hidden. If an adapter uses a copy of the rules, a screen’s view still does the real work, a platform was skipped, a difference is marked known or the guard did not run, the report says INCOMPLETE or BLOCKED and lists why under Needs your decision. See [Result words](add-to-your-app.md#result-words).

**Why does the report say FAIL when the runner passed?**

An app failed to build or one of its unit tests failed. The runner only proves the adapters agree, so the report also checks the apps themselves. See [9. Check the app still works](add-to-your-app.md#9-check-the-app-still-works).

**Can I say “add Reflex to the whole app”?**

Yes. The assistant lists every screen first, flags the ones that need a refactor and then does one screen per branch. It stops after each screen or refactor and waits for your yes. If the two apps behave differently, it asks before changing either and puts that fix on its own branch.

**How do I update by hand?**

`git -C ../reflex pull` (or update the submodule), read [CHANGELOG.md](../CHANGELOG.md), rebuild both CLIs and rerun the runner. Same steps as the “Updating Reflex” section in the setup guide.

**Protocol or kit version changes**

The protocol version is one integer in `hello`. Additive changes stay on v1; removals or meaning changes need v2 ([protocol/v1.md](protocol/v1.md) §Compatibility). Kit versions are semantic and independent. Follow root `CHANGELOG.md` and `docs/protocol/CHANGELOG.md`.

**How do I remove Reflex from my app?**

Delete the CLI and Introspection targets, the `tests/reflex.json` and journeys and the sibling `reflex` clone or submodule. Because phone targets never linked ReflexKit, release builds need no further change.

**Can I use it in CI?**

Yes. This repo’s workflow builds and runs both samples on `macos-latest`. Point your job at your manifest with `--platform both` (or one platform) after building the CLIs.

## Safety

**Does Reflex ship in App Store or Play release builds?**

It must not. Keep ReflexKit, adapters and CLIs out of the phone UI targets. The network guard is test instrumentation only and is never linked into Core or a Mobile host (`scripts/network_guard.c` header comment; [architecture.md](architecture.md)).

**Does a behavior session use the network?**

On macOS the guard denies Internet `connect` / `connectx` / `sendto` and the runner fails the canary if denial cannot be proved. Hosts should talk to in-process fakes. The guard is a deterministic test aid, not a security boundary against malicious native code.

**What does the CLI expose?**

Local stdin/stdout on your machine. Anyone who can run the CLI already has local code execution on that checkout.

**Is there a server socket?**

Only if you add one and opt in at launch. The optional debug socket host (`ReflexSocketHost` in Swift, `kit/kotlin-socket` in Kotlin) listens on 127.0.0.1 inside a debug build, one client at a time. Any local process can drive it while it runs, so keep it out of release builds. The inventory sample apps use it on an iOS simulator and an Android emulator. `scripts/check_release_exclusion.sh` proves their release builds leave out the code, the dependency and on Android the network permission. It has not run on a physical phone. See [real-build.md](real-build.md).
