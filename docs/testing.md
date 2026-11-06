# Behavior tests

Run the README Setup path first. A journey is a JSON file of `ls` and `do` steps. `runner/reflex_runner.py` sends each journey to every platform CLI a manifest names. Python’s standard library supplies the runner and transport. No test framework or mock library is needed.

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform kotlin samples/outbox/journeys/07-offline.json
```

## Inventory journeys

`tests/inventory/journeys/` covers list, detail, quantity, save, persistence after back, decrement at zero, Int64 and business validation, wire rejects with the kit’s error code and path, the handshake, the save-failure fixture and three network tripwires. `network` is an unprovided service edge. `network-caught` catches the guard error inside the service. Both answer with `networkAttempts` 1 and exit 70. `http-caught` makes a real loopback connect through URLSession or HttpURLConnection that the DYLD guard denies, so the journey expects `network` `denied`. No external endpoint receives a request.

## Outbox journeys

`samples/outbox/journeys/` drives time with `advance` and failures with `network`. It covers backoff timing, the 30 second cap and giving up, lost replies deduped by idempotency key, 409, offline holds, 422 and Retry, queue order, SyncNow, validation, wire rejects, Int64 time and an `http` tripwire.

## Conformance

Conformance is the shared kit fixture that both platforms must answer the same way. Both kits run `kit/conformance/strict-decoder.json` in their unit tests: decoder cases F-01 to F-07, G-1 exact keys, G-2 line framing, G-3 strict UTF-8, protocol cases and matcher cases. Stream cases send raw bytes and require exact reply bytes. The table step fails when any reply differs by one byte between Swift and Kotlin. The runner checks its own matcher against the same matcher cases on every run. `tests/inventory/journeys/05-wire.json` and `samples/outbox/journeys/15-wire.json` send the same raw bytes to the sample CLIs.

```bash
REFLEX_CONFORMANCE_REPORT=/tmp/reflex-conformance swift test --package-path kit -j 2
REFLEX_CONFORMANCE_REPORT=/tmp/reflex-conformance kotlin/gradlew -p kotlin --no-daemon --max-workers=1 :reflex-kit:test --rerun-tasks
python3 runner/conformance_table.py /tmp/reflex-conformance
```

## Red paths

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json runner/red/wrong-expect.json --timings 0
python3 runner/reflex_runner.py tests/inventory/reflex.json runner/red/xpass.json --timings 0
python3 runner/reflex_runner.py tests/inventory/reflex.json runner/red/xfail.json --timings 0 --strict
python3 runner/reflex_runner.py runner/red/parity-manifest.json --timings 0
python3 runner/reflex_runner.py runner/red/bytes-manifest.json --timings 0
```

`bytes-manifest.json` pairs the Swift inventory CLI with `spaced_host.py`, which returns the same values with different bytes. It must print `PARITY BYTES` lines.

These must exit 1. Failure output names the platform, journey, step, action, the line sent and the first mismatching path with expected and actual values and JSON kinds. A six-second response deadline reports stalled hosts. Host processes are closed or killed after every journey.

## Fixtures and timings

Fixtures are passed in at construction: `FixtureInventoryService` for inventory and `FakeClock` plus `FlakyNetwork` for the outbox. Add fixture data there rather than patching a ViewModel during a test. Each repeat starts new native sessions and must reproduce the first transcript byte for byte. Warm timing samples reuse one session after one unmeasured full journey and include JSON transport plus assertions.

The GitHub Actions workflow runs the same commands on macOS. The network guard (the process that blocks real Internet calls during a session) is macOS only. On Linux the Kotlin journeys run and pass but the `GUARD` and `RESULT` lines say network isolation is not exercised. Linux needs a different guard, such as `LD_PRELOAD` or a network namespace. Mobile build checks do not claim pixel or device-journey coverage.

## Mobile host UI

`tests/mobile/ios-inventory-journey.yaml` and `tests/mobile/android-inventory-journey.yaml` exercise the happy fixture on InventoryMobile and the Compose host. The thin hosts do not expose the save-failure fixture so that path stays CLI-only until a host adds constructor input.
