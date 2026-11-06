# Linux network guard check on 6 Nov 2026

One Debian 13 x86_64 host (glibc 2.41, Python 3.13.5, Temurin 21.0.13 JRE, gcc 14.2) ran the runner and `scripts/network_guard.c` from the working tree of the “Guard Linux runs and flag unguarded ones” commit. The Kotlin CLI jars were built on macOS and copied over. No Swift toolchain was installed. See `host.log`.

| Check | Log | Result |
| --- | --- | --- |
| Guard builds with `cc -shared -fPIC` | `guard-build.log` | exit 0 |
| Inventory Kotlin, three repeats and twenty warm samples | `inventory-kotlin.log` | `GUARD PASS backend=LD_PRELOAD`, `http-caught` reports `network=denied`, `RESULT PASS`, exit 0 |
| Outbox Kotlin, three repeats and twenty warm samples | `outbox-kotlin.log` | `GUARD PASS backend=LD_PRELOAD`, `tripwire` reports `network=denied`, `RESULT PASS`, exit 0 |
| `--no-guard` | `outbox-no-guard.log` | `RESULT PASS-UNGUARDED`, exit 3 |
| `--no-guard --allow-unguarded` | `outbox-allow-unguarded.log` | `RESULT PASS-UNGUARDED`, exit 0 |
| No C compiler on `PATH` | `outbox-no-compiler.log` | `GUARD SKIP`, `RESULT PASS-UNGUARDED`, exit 3 |
| A guard that loads but never denies (`noop_guard.c`) | `red-canary-noop-guard.log` | `GUARD FAIL`, exit 2 |

Not tested: Swift on Linux, ARM Linux, Alpine (musl), Docker, WSL 2 and Linux CI runners. The guard only sees calls through the C library, so a static binary or a raw system call gets past it.
