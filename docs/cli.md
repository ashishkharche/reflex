# CLI hosts

Build with `bash scripts/build.sh`. Every host speaks [protocol v1](protocol/v1.md) through ReflexKit’s `Session`.

| sample | Swift executable | Kotlin entry point | fixtures |
| --- | --- | --- | --- |
| inventory | `swift/.build/debug/inventory-cli` | `java -Xmx96m -cp 'kotlin/cli/build/install/cli/lib/*' reflex.MainKt` | `happy` `save-failure` `network` `network-caught` `http-caught` |
| outbox | `samples/outbox/swift/.build/debug/outbox-cli` | `java -Xmx96m -cp 'samples/outbox/kotlin/cli/build/install/cli/lib/*' reflex.outbox.MainKt` | `fake` `http` |

A session starts with `{"op":"hello","protocol":1}`. Human command `do OpenProduct {"id":"shirt"}` maps to:

```json
{"op":"do","action":"OpenProduct","input":{"id":"shirt"}}
```

`python3 scripts/console.py swift` or `python3 scripts/console.py kotlin outbox` sends `hello` and translates `ls`, `do Action [json]` and `op name [json]` into the raw protocol without holding state itself.

## Inventory

The initial node is `InventoryList`. Its actions are `OpenProduct`, `Refresh` and `goBack`. Detail actions are `Decrement`, `OpenProduct`, `Save`, `SetQuantity` and `goBack`. `OpenProduct` takes a string `id`. `SetQuantity` takes an Int64 `quantity`. Every response carries `networkAttempts`. Any service guard attempt is sticky and the CLI exits 70 after the response. The runner also checks the process-level audit independently of that counter.

## Outbox

The node is `Outbox` and every response carries `server`. Host ops `advance` and `network` drive the fake clock and the flaky network. Details: [samples/outbox/README.md](../samples/outbox/README.md).

Captured transcripts from both native hosts are under `evidence/`.
