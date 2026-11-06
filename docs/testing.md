# Writing tests

How journeys, conformance and red paths work. Run [Setup](setup.md) first.

A [journey](glossary.md) is a JSON file of `ls` and `do` steps. `runner/reflex_runner.py` sends each journey to every platform CLI named in a [manifest](glossary.md).

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both --repeat 3 --timings 20
```

## Inventory journeys

`tests/inventory/journeys/` covers list, detail, quantity, save, persistence after back, decrement at zero, Int64 and business validation, wire rejects, the handshake, save-failure and three network tripwires.

| Fixture | Behaviour |
| --- | --- |
| `network` | Unprovided service edge; `networkAttempts` 1; exit 70 |
| `network-caught` | Guard error caught in the service; same counters |
| `http-caught` | Real loopback connect denied by the DYLD guard; expects `network` `denied` |

## Outbox journeys

`samples/outbox/journeys/` drives time with `advance` and failures with `network`. Coverage includes backoff, the 30 second cap, lost replies, 409, offline holds, 422, queue order, SyncNow, validation, wire rejects and an `http` tripwire.

## Conformance

[Conformance](glossary.md) is the shared kit fixture both platforms must answer the same way.

```bash
REFLEX_CONFORMANCE_REPORT=/tmp/reflex-conformance swift test --package-path kit -j 2
REFLEX_CONFORMANCE_REPORT=/tmp/reflex-conformance kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :reflex-kit:test --rerun-tasks
python3 runner/conformance_table.py /tmp/reflex-conformance
```

Cases include decoder F-01–F-07, G-1 exact keys, G-2 line framing, G-3 strict UTF-8, protocol and matcher cases. The table fails when any reply differs by one byte between Swift and Kotlin.

## Red paths

These must exit 1:

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json runner/red/wrong-expect.json --timings 0
python3 runner/reflex_runner.py tests/inventory/reflex.json runner/red/xpass.json --timings 0
python3 runner/reflex_runner.py tests/inventory/reflex.json runner/red/xfail.json --timings 0 --strict
python3 runner/reflex_runner.py runner/red/parity-manifest.json --timings 0
python3 runner/reflex_runner.py runner/red/bytes-manifest.json --timings 0
```

Failure lines name platform, journey, step, action, the sent line and the first mismatching path.

## Fixtures and timings

Pass fixtures in at construction (`FixtureInventoryService`, `FakeClock`, `FlakyNetwork`). Each repeat starts new native sessions and must match the first transcript byte for byte. Warm timings reuse one session after one unmeasured journey.

## Network guard and Linux

The [network guard](glossary.md) is macOS only. On Linux, Kotlin journeys can pass while `GUARD` / `RESULT` say network isolation is not exercised. Mobile UI YAML under `tests/mobile/` does not claim pixel coverage.

Full runner flags: [runner/README.md](../runner/README.md).
