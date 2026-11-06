# How you use it

You want a test or an AI agent to check your app’s logic on iOS and Android without tapping through screens. The inventory sample shows the whole path.

## Keep the ViewModel. Add a small adapter.

The Core ViewModel does not import ReflexKit. It still owns state and `send`:

```swift
// swift/Sources/InventoryCore/Inventory.swift
public func send(_ action: Action) { update(.viewAction(action)) }
```

```kotlin
// kotlin/core/src/main/kotlin/reflex/Inventory.kt
fun send(action: Action) = update(Message.ViewAction(action))
```

A separate adapter node reads that state and maps actions to `send`:

```swift
// swift/Sources/InventoryIntrospection/Node.swift
public struct DetailNode: Node {
    let vm: InventoryDetailViewModel
    public var name: String { "InventoryDetail" }
    public var state: JSONValue {
        // … product, saved, error from vm.state …
    }
    public var actions: [String: NodeAction] { [
        "SetQuantity": NodeAction(input: quantityInput) { args in
            // … Int conversion …
            vm.send(.setQuantity(quantity))
        },
        "Decrement": NodeAction { _ in vm.send(.decrement) },
        "Save": NodeAction { _ in vm.send(.save) }
    ] }
}
```

```kotlin
// kotlin/introspection/src/main/kotlin/reflex/Node.kt
class DetailNode(private val vm: InventoryDetailViewModel) : Node {
    override val name = "InventoryDetail"
    override val state: JsonValue get() = jsonObject(
        "product" to vm.state.product.json(), "saved" to vm.state.saved.json,
        "error" to vm.state.error?.json)
    override val actions get() = mapOf(
        "SetQuantity" to NodeAction(quantityInput) {
            vm.send(InventoryDetailViewModel.Action.SetQuantity(it.int64("quantity")))
        },
        "Decrement" to NodeAction { vm.send(InventoryDetailViewModel.Action.Decrement) },
        "Save" to NodeAction { vm.send(InventoryDetailViewModel.Action.Save) })
}
```

## Add a tiny CLI entry point

```swift
// swift/Sources/InventoryCLI/main.swift
let app = InventoryApp(service: FixtureInventoryService(fixture: fixture, guardrail: network))
let session = Session(sample: "inventory", root: { AppNode(app: app) },
                      extras: { ["networkAttempts": JSONValue(network.attempts)] })
session.serveStandardIO { network.attempts > 0 ? 70 : nil }
```

```kotlin
// kotlin/cli/src/main/kotlin/reflex/Main.kt
val app = InventoryApp(FixtureInventoryService(fixture, network))
val session = Session("inventory", { AppNode(app) },
    extras = { mapOf("networkAttempts" to network.attempts.json) })
session.serveStandardIO { if (network.attempts > 0) 70 else null }
```

More adoption detail: [kit/README.md](../kit/README.md).

## Drive it from a terminal

After `bash scripts/build.sh`:

```bash
printf 'ls\ndo OpenProduct {"id":"shirt"}\ndo SetQuantity {"quantity":12}\ndo Save\nls\n' \
  | python3 scripts/console.py swift
```

Real replies (schema `inputs` omitted; values unchanged):

```text
$ ls
{"ok":true,"node":{"name":"InventoryList","state":{"products":[{"id":"shirt","quantity":3,"title":"Cotton shirt"},{"id":"mug","quantity":0,"title":"Ceramic mug"}]},"actions":["OpenProduct","Refresh","goBack"]},"networkAttempts":0}

$ do OpenProduct {"id":"shirt"}
{"ok":true,"node":{"name":"InventoryDetail","state":{"product":{"id":"shirt","quantity":3,"title":"Cotton shirt"},"saved":false},"actions":["Decrement","OpenProduct","Save","SetQuantity","goBack"]},"networkAttempts":0}

$ do SetQuantity {"quantity":12}
{"ok":true,"node":{"name":"InventoryDetail","state":{"product":{"id":"shirt","quantity":12,"title":"Cotton shirt"},"saved":false},"actions":["Decrement","OpenProduct","Save","SetQuantity","goBack"]},"networkAttempts":0}

$ do Save
{"ok":true,"node":{"name":"InventoryDetail","state":{"product":{"id":"shirt","quantity":12,"title":"Cotton shirt"},"saved":true},"actions":["Decrement","OpenProduct","Save","SetQuantity","goBack"]},"networkAttempts":0}
```

## Turn that into a shared test

Those same steps live in `tests/inventory/journeys/01-happy.json`. Opening stretch:

```json
{
  "name": "happy",
  "fixture": "happy",
  "steps": [
    {
      "ls": true,
      "expect": {
        "ok": true,
        "node": {
          "name": "InventoryList",
          "state": {
            "products": [
              {"id": "shirt", "title": "Cotton shirt", "quantity": 3},
              {"id": "mug", "title": "Ceramic mug", "quantity": 0}
            ]
          },
          "actions": ["OpenProduct", "Refresh", "goBack"]
        }
      }
    },
    {
      "do": "OpenProduct",
      "input": {"id": "shirt"},
      "expect": {
        "ok": true,
        "node": {
          "name": "InventoryDetail",
          "state": {
            "product": {"id": "shirt", "title": "Cotton shirt", "quantity": 3},
            "saved": false
          }
        }
      }
    },
    {
      "do": "SetQuantity",
      "input": {"quantity": 12},
      "expect": {
        "ok": true,
        "node": {"state": {"product": {"quantity": 12}, "saved": false}}
      }
    },
    {
      "do": "Save",
      "expect": {
        "ok": true,
        "node": {"state": {"saved": true}}
      }
    }
  ]
}
```

Run every inventory journey on both platforms:

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --strict
```

```text
RESULT PASS mode=strict unexpected_failures=0 xfail=0 platforms=swift,kotlin repeat=1 sample=inventory guard=canary-pass
```

Warm P50 on this machine was about 1.4 ms per step. When the two Cores disagree, the runner fails the suite. The same approach found a real rest timer crash in Workout Director: a Swift trap when adding seconds to the rest timer.

Full setup commands: [setup.md](setup.md).
