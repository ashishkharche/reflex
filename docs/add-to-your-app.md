# Add Reflex to your app

Step-by-step guide for adding Reflex to an existing iOS and Android app so a test or an AI agent can drive both without a screen.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/diagrams/04-assistant-setup-dark.svg">
  <img src="../assets/diagrams/04-assistant-setup-light.svg" alt="Paste the README prompt into an assistant and it sets Reflex up step by step" width="100%">
</picture>

## For AI assistants

The README prompt is short on purpose. This section holds the full instructions behind it.

**Where Reflex lives**

- Its own clone next to the app repo, for example `../reflex`. A git submodule also works.
- Never copy Reflex files into the app repo.

**First setup**

- Start with the main screen.
- Add one adapter that lists its state and actions.
- Add one small CLI per platform the app has: Swift and Kotlin when both exist.
- Write a `reflex.json` manifest and one journey for that screen.

**Update**

- Pull the latest main. With a submodule, update the submodule instead.
- Read [CHANGELOG.md](../CHANGELOG.md) for changes since the app’s version.
- Apply them to the adapters, the CLIs and `reflex.json`.

**Rules**

- Keep the app’s code and behaviour unchanged. Only add new files and targets.
- If a screen keeps its state in its views, ask before refactoring.
- If iOS and Android are separate repos, ask where the other one is first.

**Run**

- Rebuild the CLIs.
- Run the runner with `--platform both`. If the app has one platform, pass just that one.
- Fix any failure and rerun.

**Report**

- Reply with the five-part report in [What you get back](#what-you-get-back): Result, Needs your decision, What I added or changed, Where it is, Try it.
- Put the whole report in one fenced `text` block with a heading per part and a blank line between parts. Follow the rules in that section and keep it under 20 lines.

Layout used below: your app and a clone of this repo sit next to each other.

```text
your-workspace/
  reflex/          # git clone https://github.com/ashishkharche/reflex.git
  your-app/        # your project
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/diagrams/01-in-your-app-dark.svg">
  <img src="../assets/diagrams/01-in-your-app-light.svg" alt="Your UI and the adapter both use the same ViewModel" width="100%">
</picture>

### If iOS and Android are separate repos

```text
your-workspace/
  reflex/           # the kit
  my-app-ios/       # its own repo, builds the Swift CLI
  my-app-android/   # its own repo, builds the Kotlin CLI
```

Put `tests/reflex.json` and `tests/journeys/` in either repo or in a small third tests repo. Each platform command in the manifest points at its own repo with a relative path, for example `"../my-app-ios/.build/debug/your-cli"` and `"-cp", "../my-app-android/cli/build/install/cli/lib/*"`. Both CLIs must use the same node names, state keys and action names.

## 0. Prerequisites

- macOS (the network guard needs `DYLD_INSERT_LIBRARIES`)
- Xcode with Swift 6.0 or newer
- JDK 17 or newer
- Python 3
- Git

## 1. Get the kit

Clone Reflex next to your repo, not inside it. A git submodule is optional.

```bash
cd your-workspace
git clone https://github.com/ashishkharche/reflex.git
```

You will point Swift and Kotlin at `reflex/kit`.

## 2. Swift

Keep your Core free of UI and free of ReflexKit. Add a separate Introspection target and a small CLI.

In a Swift package next to the kit (paths match the layout above):

```swift
// Package.swift
dependencies: [
    .package(path: "../reflex/kit")
],
targets: [
    .target(name: "YourCore"),
    .target(name: "YourIntrospection", dependencies: [
        "YourCore", .product(name: "ReflexKit", package: "kit")
    ]),
    .executableTarget(name: "your-cli", dependencies: [
        "YourCore", "YourIntrospection", .product(name: "ReflexKit", package: "kit")
    ])
]
```

If your app is an Xcode project: put the Core in a Swift package or a folder with no UIKit or SwiftUI imports. Add a second target or local package for Introspection that depends on the Core and ReflexKit. Add a Command Line Tool target for the CLI. Do not link ReflexKit into the UI target.

## 3. Kotlin

Keep the Core as a JVM module with no Android imports. Include the kit from the clone.

```kotlin
// settings.gradle.kts
include(":core", ":introspection", ":cli", ":reflex-kit")
project(":reflex-kit").projectDir = file("../reflex/kit/kotlin")
```

```kotlin
// introspection/build.gradle.kts
dependencies {
    implementation(project(":core"))
    api(project(":reflex-kit"))
}
```

```kotlin
// cli/build.gradle.kts
plugins { kotlin("jvm"); application }
dependencies {
    implementation(project(":core"))
    implementation(project(":introspection"))
}
application { mainClass.set("yourapp.MainKt") }
```

Use JVM 17. Build the CLI with one worker and no daemon on a small machine:

```bash
./gradlew --no-daemon --max-workers=1 :cli:installDist
```

## 4. One adapter node per ViewModel

An adapter is a small type that implements ReflexKit’s `Node`. It exposes a name, JSON state and named actions. It only calls `send` on your ViewModel.

Tiny counter example (JSON integers only):

```swift
// Core — no ReflexKit import
public final class CounterViewModel {
    public struct State { public var count: Int }
    public enum Action { case increment, set(Int) }
    public private(set) var state = State(count: 0)
    public func send(_ action: Action) { /* update state */ }
}
```

```swift
// Introspection
import ReflexKit
private let setInput = Schema([.required("value", .int64)])
public struct CounterNode: Node {
    let vm: CounterViewModel
    public var name: String { "Counter" }
    public var state: JSONValue { ["count": JSONValue(vm.state.count)] }
    public var actions: [String: NodeAction] { [
        "Increment": NodeAction { _ in vm.send(.increment) },
        "Set": NodeAction(input: setInput) { args in
            vm.send(.set(Int(args.int64("value"))))
        }
    ] }
}
```

```kotlin
// Core — no ReflexKit import
class CounterViewModel {
    data class State(val count: Int)
    sealed interface Action {
        data object Increment : Action
        data class Set(val value: Long) : Action
    }
    var state = State(0); private set
    fun send(action: Action) { /* update state */ }
}
```

```kotlin
// Introspection
import reflex.kit.*
private val setInput = Schema(Field.required("value", FieldType.int64))
class CounterNode(private val vm: CounterViewModel) : Node {
    override val name = "Counter"
    override val state: JsonValue get() = jsonObject("count" to vm.state.count.json)
    override val actions get() = mapOf(
        "Increment" to NodeAction { vm.send(CounterViewModel.Action.Increment) },
        "Set" to NodeAction(setInput) {
            vm.send(CounterViewModel.Action.Set(it.int64("value")))
        }
    )
}
```

## 5. A small CLI per platform

The CLI builds your root node and serves protocol v1 on stdin/stdout.

```swift
import ReflexKit
let vm = CounterViewModel()
Session(sample: "counter", root: { CounterNode(vm: vm) }).serveStandardIO()
```

```kotlin
import reflex.kit.Session
fun main() {
    val vm = CounterViewModel()
    Session("counter", { CounterNode(vm) }).serveStandardIO()
}
```

Build Swift with two jobs:

```bash
swift build --package-path swift -j 2
```

## 6. Try it by hand

The CLI speaks NDJSON (one JSON object per line). Send `hello`, then `ls` and `do`:

```bash
printf '%s\n' \
  '{"op":"hello","protocol":1}' \
  '{"op":"ls"}' \
  '{"op":"do","action":"Increment"}' \
  | swift/.build/debug/counter-cli
```

You should see `"ok":true` and `"state":{"count":1}` after Increment.

## 7. Manifest and journey

Create `tests/reflex.json`. `root` is your app directory (relative to the manifest). Point conformance and the network guard at the reflex clone. Do not set `warm` until a journey restores starting state; warm timings reuse one process.

```json
{
  "sample": "counter",
  "protocol": 1,
  "root": "..",
  "conformance": "../reflex/kit/conformance/strict-decoder.json",
  "guard": {
    "source": "../reflex/scripts/network_guard.c",
    "library": ".build/network_guard.dylib"
  },
  "platforms": {
    "swift": {
      "command": ["{root}/swift/.build/debug/counter-cli"]
    },
    "kotlin": {
      "command": [
        "{java}",
        "-Xmx96m",
        "-cp",
        "{root}/kotlin/cli/build/install/cli/lib/*",
        "yourapp.MainKt"
      ]
    }
  },
  "journeys": ["tests/journeys/*.json"]
}
```

One journey file:

```json
{
  "name": "count",
  "steps": [
    {
      "ls": true,
      "expect": {
        "ok": true,
        "node": {
          "name": "Counter",
          "state": {"count": 0},
          "actions": ["Increment", "Set"]
        }
      }
    },
    {
      "do": "Increment",
      "expect": {
        "ok": true,
        "node": {"state": {"count": 1}}
      }
    },
    {
      "do": "Set",
      "input": {"value": 5},
      "expect": {
        "ok": true,
        "node": {"state": {"count": 5}}
      }
    }
  ]
}
```

Full field list: [runner/README.md](../runner/README.md).

## 8. Run the shared journeys

`bash scripts/build.sh` is only for this repo’s samples. For your app, build the two CLIs as above, then:

```bash
python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both
```

PASS looks like:

```text
RESULT PASS mode=xfail-tracked unexpected_failures=0 xfail=0 platforms=swift,kotlin repeat=1 sample=counter guard=canary-pass
```

FAIL names the step and the first mismatching path:

```text
FAIL platform=swift journey=… step=1 action=ls send={"op":"ls"} $.node.state.count expected=99 (integer) actual=0 (integer) …
RESULT FAIL mode=xfail-tracked unexpected_failures=1 xfail=0 platforms=swift repeat=1 sample=counter guard=canary-pass
```

## What you get back

If you used the AI prompt from the README, the assistant ends with a five-part report. It follows these rules so it stays readable in a terminal:

- The whole report sits in one fenced `text` block so the line breaks survive.
- Each part starts with a short heading on its own line. A blank line separates the parts.
- **Result:** the PASS or FAIL word plus the platforms, for example “PASS on swift and kotlin”. Not the full RESULT line.
- **Needs your decision:** a numbered list with one decision per item. Each item is at most two short lines that say what differs and the options. “None” if empty.
- **What I added** (or **What I changed** on an update): one bullet per file or folder.
- **Where it is:** branch, commit and pushed or not, one line each.
- **Try it:** the command alone on its own line.
- Under 20 lines in total. No long sentences.

Example:

```text
Result
PASS on swift and kotlin

Needs your decision
1. Home opens on a different default item on Android and iOS.
   Pick one. Both CLIs use the iOS value for now.
2. Home keeps its state in the views. The test uses a copy of its rules.
   Say yes to move both screens onto the shared core.

What I added
- tests/reflex.json
- tests/journeys/home.json
- HomeCore, HomeNode, home-cli (Swift and Kotlin)

Where it is
Branch: reflex/home
Commit: abc1234, not pushed

Try it
python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both
```

## 9. Troubleshooting

| Symptom | What to check |
| --- | --- |
| `host binary not found` | Build the Swift executable and run Gradle `:cli:installDist` first. |
| `json.malformed` on the first line | Send `{"op":"hello","protocol":1}` before `ls` or `do`. Human `ls` / `do` lines are not the wire format; use JSON objects. |
| Kotlin and Swift disagree on keys | Both kits compare keys by exact UTF-16 code units. Use the same spellings. |
| Warm timing fails after a green suite | The warm run reuses one process. Omit `warm` until the journey resets state. Another option is a reset action. |
| `guard=skipped-not-macos` | Expected off macOS. Journeys still run; network isolation is not exercised. |
| SIP drops the guard on `/usr/bin/java` | Prefer `{java}` from `JAVA_HOME` in the manifest. The runner resolves a real binary. |

More protocol detail: [protocol/v1.md](protocol/v1.md). Kit API table: [kit/README.md](../kit/README.md).

## Updating Reflex

Paste the same README AI prompt again; it pulls the latest clone (or updates the submodule), reads [CHANGELOG.md](../CHANGELOG.md) and reruns the suite. By hand:

1. Pull the latest kit: `git -C ../reflex pull`. If you use a submodule, run `git submodule update --remote reflex` instead.
2. Read [CHANGELOG.md](../CHANGELOG.md) for protocol or kit API changes since your version and apply them to your adapters, CLIs and `reflex.json`.
3. Rebuild both CLIs: the Swift executable and Gradle `:cli:installDist`.
4. Rerun the runner: `python3 ../reflex/runner/reflex_runner.py tests/reflex.json --platform both`.

Environments, other stacks and CI notes: [faq.md](faq.md).
