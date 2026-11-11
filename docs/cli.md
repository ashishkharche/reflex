# CLI hosts

How to build and talk to the sample command-line hosts. Each host speaks [protocol v1](protocol/v1.md) through ReflexKit’s `Session`.

## Build

```bash
bash scripts/build.sh
```

| Sample | Swift executable | Kotlin entry point | Fixtures |
| --- | --- | --- | --- |
| inventory | `swift/.build/debug/inventory-cli` | `java -Xmx96m -cp 'kotlin/cli/build/install/cli/lib/*' reflex.MainKt` | `happy` `save-failure` `network` `network-caught` `http-caught` |
| outbox | `samples/outbox/swift/.build/debug/outbox-cli` | `java -Xmx96m -cp 'samples/outbox/kotlin/cli/build/install/cli/lib/*' reflex.outbox.MainKt` | `fake` `http` |

## Generated hosts

`runner/reflex_init.py` writes a host for an app with no hand-written code. See [Generate the first setup](add-to-your-app.md#generate-the-first-setup).

```bash
python3 ../reflex/runner/reflex_init.py --list
python3 ../reflex/runner/reflex_init.py --screen HomeViewModel
python3 ../reflex/runner/reflex_init.py --dry-run
```

| Flag | Effect |
| --- | --- |
| `--list` | Prints the ranked candidates and stops. |
| `--screen NAME` | Uses this class instead of the top one. |
| `--stack NAME` | Uses `kotlin`, `flutter`, `node` or `swift` instead of the one found. |
| `--dry-run` | Same as `--list`. |

## Human console

`scripts/console.py` sends `hello` and turns `ls` / `do` / `op` into wire JSON.

```bash
python3 scripts/console.py swift
python3 scripts/console.py kotlin outbox
```

Example mapping: human `do OpenProduct {"id":"shirt"}` becomes:

```json
{"op":"do","action":"OpenProduct","input":{"id":"shirt"}}
```

## Inventory host

- Initial node: `InventoryList` with `OpenProduct`, `Refresh`, `goBack`.
- Detail actions: `Decrement`, `OpenProduct`, `Save`, `SetQuantity`, `goBack`.
- Every response carries `networkAttempts`. A sticky service guard attempt exits 70 after the reply.

## Outbox host

- Node: `Outbox`. Every response carries `server`.
- Host ops `advance` and `network` drive the fake clock and flaky network.
- Details: [samples/outbox/README.md](../samples/outbox/README.md).

Captured transcripts live under `evidence/`.
