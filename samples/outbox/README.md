# Outbox sample

Standalone Reflex sample for an offline outbox with exponential backoff and idempotency-key dedup. There is no mobile host.

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

`OutboxViewModel` takes a `Clock` and a `Transport` at construction. Actions go in through `send` and one `update` owns every state write, including the attempt count and each delivery result.

The adapter always lists all five actions, whatever the state. `update` decides whether an action is valid. An action that does not apply sets a visible error or changes nothing.

| Action | Effect |
| --- | --- |
| `Enqueue(key, body)` | Queues a message due now. A key already in the queue is dropped and counted in `deduped`. Keys are 1 to 64 ASCII letters, digits, dots, dashes or underscores. Bodies hold at most 280 Unicode code points. |
| `SyncNow` | Attempts every waiting message at once and ignores backoff. Offline it sets a visible error. |
| `SetOnline(online)` | Offline holds every message and clears the wake time. Back online it attempts what is due and keeps future backoff. |
| `Retry(key)` | Resets attempts on a failed message and delivers when online. Any other key sets the error “Only failed messages can be retried.” |
| `PurgeSent` | Removes sent messages. With nothing sent it changes nothing. |
| `Wake` | The host timer fired. Attempts messages whose `nextAttemptAt` has passed. |

Delivery results: `created` and `duplicate` (HTTP 409) mark a message sent with that `ack`. `timeout` and HTTP 500 retry after 1, 2, 4, 8 and 16 seconds, then every 30 seconds, with no jitter. The seventh failed attempt marks the message failed. HTTP 422 fails at once. Each message keeps its own schedule, so one slow message never blocks the queue.

## Fixtures

`FakeClock` starts at 1800000000000 ms (above 2^31) and `advance(by:waking:)` fires the timer at every wake time on the way. `FlakyNetwork` sits in front of a fake server that stores each idempotency key once. Each delivery consumes one scripted outcome; an empty script means `ok`.

| Outcome | Server | Client sees |
| --- | --- | --- |
| `ok` | stores the key or already has it | `created` or `duplicate` |
| `lost` | stores the key | `timeout` |
| `timeout` | sees nothing | `timeout` |
| `500` | sees nothing | server error |
| `409` | already has the key | `duplicate` |
| `422` | rejects | rejected |

The CLI’s first argument picks `fake` (default) or `http`. `--listen PORT` serves the session on 127.0.0.1 through the debug socket host instead of stdin. `live.json` runs `live/01-live.json` that way. `http` makes a real loopback TCP connect before each delivery so the runner’s DYLD guard has something to deny.

## Wire

The CLI speaks Reflex protocol v1 ([docs/protocol/v1.md](../../docs/protocol/v1.md)). The node is `Outbox`. Two host ops drive the fixtures:

```json
{"op":"advance","input":{"ms":1000}}
{"op":"network","input":{"script":["lost","500","ok"]}}
```

The CLIs add one more host op for asynchronous tests:

```json
{"op":"advanceLater","input":{"ms":1000,"afterMs":150}}
```

It replies at once, then a background thread waits `afterMs` real milliseconds (0 to 5000) and advances the fake clock by `ms`. One lock serialises that thread with request handling, so a reply never shows half a change.

`ms` is an Int64 from 0 to 86400000. Unknown outcomes are rejected with `field.value` at their array path. Every response carries `server` with `requests`, `stored` and `scripted` so journeys can prove a key was stored once.

## Journeys

`journeys/` covers delivery, backoff timing, the 30 second cap and giving up, lost replies, 409 conflicts, client and server dedup, offline holds, 422 rejection and Retry, queue order, SyncNow, business validation, wire rejects, Int64 time, the network tripwire, a stable action set across states and waiting for a background change with `eventually` (`17-eventually.json`). `warm.json` is the repeatable warm-timing journey.
