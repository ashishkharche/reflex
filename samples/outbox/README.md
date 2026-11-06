# Outbox sample

A standalone Reflex sample whose behaviour is hard to test on a device: an offline outbox that retries with exponential backoff and dedups by idempotency key. Swift and Kotlin each have a UI-free Core, an introspection adapter built on ReflexKit and a CLI. There is no mobile host.

## Build and run

From the repository root:

```bash
bash scripts/build.sh
swift test --package-path samples/outbox/swift -j 2
kotlin/gradlew -p samples/outbox/kotlin --no-daemon --max-workers=1 :core:test
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both --repeat 3 --timings 20
```

The Kotlin build reuses the wrapper in `kotlin/`. Both builds include the shared kit from `kit/`.

## Core

`OutboxViewModel` takes a `Clock` and a `Transport` at construction. Actions go in through `send` and one `update` owns every state write.

| action | effect |
| --- | --- |
| `Enqueue(key, body)` | Queues a message due now. A key already in the queue is dropped and counted in `deduped`. Keys are 1 to 64 ASCII letters, digits, dots, dashes or underscores. Bodies hold at most 280 Unicode code points. |
| `SyncNow` | Attempts every waiting message at once and ignores backoff. Offline it sets a visible error. |
| `SetOnline(online)` | Offline holds every message and clears the wake time. Back online it attempts what is due and keeps future backoff. |
| `Retry(key)` | Offered while a message has failed. Resets attempts and delivers when online. |
| `PurgeSent` | Offered while a message is sent. Removes sent messages. |
| `Wake` | The host timer fired. Attempts messages whose `nextAttemptAt` has passed. |

Delivery results: `created` and `duplicate` (HTTP 409) mark a message sent with that `ack`. `timeout` and HTTP 500 retry after 1, 2, 4, 8 and 16 seconds, then every 30 seconds, with no jitter. The seventh failed attempt marks the message failed. HTTP 422 fails at once. Each message keeps its own schedule, so one slow message never blocks the queue.

## Fixtures

`FakeClock` starts at 1800000000000 ms (above 2^31) and `advance(by:waking:)` fires the timer at every wake time on the way, as a host scheduler would. `FlakyNetwork` sits in front of a fake server that stores each idempotency key once. Each delivery consumes one scripted outcome and an empty script means `ok`:

| outcome | server | client sees |
| --- | --- | --- |
| `ok` | stores the key or already has it | `created` or `duplicate` |
| `lost` | stores the key | `timeout` |
| `timeout` | sees nothing | `timeout` |
| `500` | sees nothing | server error |
| `409` | already has the key | `duplicate` |
| `422` | rejects | rejected |

The CLI’s first argument picks `fake` (default) or `http`. `http` makes a real loopback TCP connect before each delivery so the runner’s DYLD guard has something to deny.

## Wire

The CLI speaks Reflex protocol v1 ([docs/protocol/v1.md](../../docs/protocol/v1.md)). The node is `Outbox`. Two host ops drive the fixtures:

```json
{"op":"advance","input":{"ms":1000}}
{"op":"network","input":{"script":["lost","500","ok"]}}
```

`ms` is an Int64 from 0 to 86400000. Unknown outcomes are rejected with `field.value` at their array path. Every response carries `server` with `requests`, `stored` and `scripted` so journeys can prove a key was stored once.

## Journeys

`journeys/` covers delivery, backoff timing, the 30 second cap and giving up, lost replies, 409 conflicts, client and server dedup, offline holds, 422 rejection and Retry, queue order, SyncNow, business validation, wire rejects, Int64 time and the network tripwire. `warm.json` is the repeatable warm-timing journey.
