# Evidence

Each folder holds raw logs from one run. Paths in logs are repo-relative where the run allowed it.

Commit SHAs named in this directory belong to the private development history and are not present in a single-commit public export.


| Folder | Run |
| --- | --- |
| `kit-outbox-2026-11-06/` | Kit extraction and the outbox sample: unit tests, runner output, conformance and deliberate red runs |
| `kit-wire-2026-11-06/` | Kit 1.0.1 wire parity for G-1 to G-3: conformance, the raw byte probe and runner output |
| `linux-2026-11-06/` | The runner on Linux: Kotlin journeys pass and the guard lines say network isolation is not exercised |

The 2026-11-06 logs predate the rename of the adoption example and fixture fields. They show `upNext` and `midSet` where the current fixture uses `label` and `fanOn`.

## Earlier runs on 5 Nov 2026

The raw logs from 5 Nov 2026 held local paths, host names and device IDs. They were removed from the tree and remain in git history. The numbers that mattered:

| Run | Result |
| --- | --- |
| Inventory go/no-go on `e68853a` | All seven TEST_PLAN criteria PASS |
| Warm journey p50, twenty samples after one warm-up | Swift 2.383 ms and Kotlin 3.602 ms |
| Flake budget | Ten new-session suite runs per native host with zero intermittent failures |
| Full shared suite with reruns, timings and guard checks | 2.737 seconds |
| Parity | Identical full JSON responses from Swift and Kotlin |
| Network guard | Six deliberate network failures exit 1. Swift `connectx` and Kotlin `connect` are denied. |
| Failure readability | Deliberate state mismatches name step, action, expected state and actual state |
| Fresh-clone README path on `e68853a` | Exit 0 in 29.436 seconds |
| Suite re-run on `1358a92`, three repeats | Swift p50 5.767 ms and Kotlin p50 11.126 ms |
| Host UI check on `2ceb302` | 14 of 14 iOS and Android steps PASS. Screens match the headless happy journey. |
| Host UI gap | The save-failure screen is unreachable from the thin hosts. The CLI covers it. |
| Mobile builds | Unsigned iOS simulator build and Compose debug APK both succeed |
