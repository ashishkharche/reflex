# Linux runner check on 6 Nov 2026

A Debian 13 x86_64 Linux host ran the runner on a `git archive` of a pre-guard-state revision plus the runner that names the guard state in RESULT. Python 3.13.5 and Temurin 21.0.13 JRE. The Kotlin CLI jars came from the macOS build because the host had no Gradle or JDK. No Swift toolchain was installed.

| Check | Result |
| --- | --- |
| Inventory Kotlin, three repeats and twenty warm samples | `RESULT PASS` with `guard=skipped-not-macos network_isolation=NOT-exercised network_unchecked=1`. Warm p50 1.617 ms. |
| Outbox Kotlin, three repeats and twenty warm samples | `RESULT PASS` with the same guard fields. Warm p50 1.034 ms. |
| Journeys that expect `network` `denied` | `NETWORK UNCHECKED` for `04-tripwires.json#http-caught` and `14-tripwire.json#tripwire`. They pass without proving denial. |
| Swift host without a build | `RESULT FAIL` with the missing binary path and exit 2 |
| `scripts/network_guard.c` with gcc | Does not compile: `sa_endpoints_t` and `connectx` are Darwin only |

The DYLD guard is macOS only. Linux network isolation needs a different mechanism, such as `LD_PRELOAD` or a network namespace.
