# Reflex runner

Reference client that runs shared journey files against every platform CLI a manifest names. Uses only the Python standard library. Speaks [protocol v1](../docs/protocol/v1.md).

## Quick commands

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform swift samples/outbox/journeys/02-backoff.json
python3 runner/reflex_runner.py samples/outbox/reflex.json --strict --evidence /tmp/outbox-evidence
```

| Flag | Effect |
| --- | --- |
| `--platform` | One platform name, a comma list or `both` (every platform in the manifest). |
| `--repeat N` | Runs the suite N times per platform. Every repeat must produce the same raw transcript as the first. |
| `--timings N` | Runs the manifest’s warm journey once unmeasured and then N measured times in one process. Prints the p50. `0` skips it. |
| `--strict` | Ignores `xfail` annotations so every finding fails. |
| `--no-guard` | Runs without the network guard and says so in the `GUARD` line. |
| `--allow-unguarded` | Exits 0 instead of 3 on `RESULT PASS-UNGUARDED`. |
| `--evidence DIR` | Writes raw NDJSON transcripts of repeat 1 per platform. |

Positional journey paths replace the manifest’s journey list.

Unit tests for the runner’s `stateKeys` map: `python3 runner/test_state_keys.py`.

## What a run checks

1. `MATCHER`: the runner’s matcher agrees with the kit’s on the shared F-13 cases in `kit/conformance/strict-decoder.json`.
2. `GUARD`: builds `scripts/network_guard.c` when needed, from the manifest root when it has one and from this Reflex clone otherwise, then proves it with a canary. A non-SIP Python under the guard (`DYLD_INSERT_LIBRARIES` on macOS, `LD_PRELOAD` on Linux) must be denied a connect to 192.0.2.1. A failed canary stops the run with exit 2. With no guard for the OS, no C compiler on Linux or `--no-guard` the line reads `GUARD SKIP` and network isolation is not exercised. An unguarded run prints `NETWORK UNCHECKED` for each journey that expects `denied`.
3. Each journey runs in a fresh host process under the guard. Any reply line left over after the last step fails the journey. The runner sends `hello` first and expects the manifest’s protocol and sample. Each step’s response must match `expect` with the type-strict partial matcher and the manifest’s `everyResponse`. At the end the exit code and the guard audit must match the journey’s `exit` and `network`.
4. `SUITE`: one line per platform per repeat with journeys, steps and wall time.
5. `PARITY`: compares every reply across platforms as raw bytes and as parsed JSON with strict types, then the exit code and the network status. A reply whose values match but whose bytes differ prints `PARITY BYTES` with the first differing byte and counts in `byte_diffs`. Both fail the run.
6. `P50` and `COLD`: warm milliseconds per journey with startup excluded, then cold milliseconds per journey with process start included.
7. `RESULT`: `PASS` only with zero unexpected failures and a guard whose canary passed. A clean run without the guard prints `PASS-UNGUARDED` and exits 3. With `--allow-unguarded` it exits 0. Exit 1 on failure. A missing host binary stops the run with exit 2 before any journey. So does a classpath folder with no jars, a `@` argument file or a script path in the command that doesn’t exist yet (`host input not found`). `guard=canary-pass` means the guard ran. `guard=skipped-unavailable` or `guard=skipped-no-guard` adds `network_isolation=NOT-exercised` and the count of unchecked network expectations.

Failure lines name the platform, journey, step, action, the line sent, the first mismatching path with expected and actual values and kinds, then the response with `node.inputs` elided. Parity diffs list every differing path with each platform’s value. When a host crashes, the line keeps the first exception line of its stack trace and its last line. A failed journey whose host wrote to stderr adds a `STDERR` line with its last lines. A stderr line that starts with `ReflexKit warning:` prints once per platform as `WARN`, even when the journey passes. The stateKeys hint for a missing key shows only when the manifest has more than one platform.

## xfail

A step or a journey may carry `"xfail": {"kotlin": "F-08"}`. A failing annotated step prints `XFAIL` and does not fail the run. An annotated step that passes prints `XPASS` and fails the run until the annotation is removed. `--strict` turns every `XFAIL` back into `FAIL`. A step with `"parity": "F-08"` turns its parity diff into `PARITY KNOWN`.

## State keys with different names

Two apps often keep the same fact under different state key names. Add `stateKeys` to the manifest or to a journey and the runner renames them before it checks `expect` and parity. With no `stateKeys` nothing changes.

```json
"stateKeys": {
 "kotlin": {
  "rename": {"started": "isRunning", "session.open": "isOpen"},
  "only": ["moreCount"]
 }
}
```

- Each key is a platform name from the manifest.
- `rename` maps a dotted path into `node.state` to the shared name of its last key. `session.open` renames `open` inside `session`. A list on the path applies to each item, so `rows.done` renames `done` in every row. Write journeys with the shared names.
- `only` lists dotted paths that exist on that platform alone. Parity skips them and prints `PARITY NOT COMPARED` with the platform, the key and the number of steps. `expect` still sees them. A listed key that the other platform also has is still compared.
- Values are never changed and keep strict types. A real value difference under a mapped key still prints `PARITY DIFF` and fails.
- A reply that `stateKeys` changed is compared as parsed JSON, not as bytes. The `PARITY` line then adds `mapped_steps` and `not_compared_keys`.
- A rename onto a key that is already there is a journey error. A journey’s `stateKeys` replaces the manifest’s. `null` turns it off. `explore.py` uses the manifest’s map for `wait` and its parity line.

Without a map, an `expect` key missing on one platform and a parity diff where each platform lacks a key the other has end with a hint to add `stateKeys`. Map only keys that mean the same thing. Two keys that mean different things are a platform difference: mark it with `parity` instead.

## Manifest

```json
{
 "sample": "outbox",
 "protocol": 1,
 "root": "../..",
 "conformance": "kit/conformance/strict-decoder.json",
 "defaultFixture": "fake",
 "platforms": {
  "swift": {"command": ["{root}/samples/outbox/swift/.build/debug/outbox-cli", "{fixture}"]},
  "kotlin": {"command": ["{java}", "-Xmx96m", "-cp", "{root}/samples/outbox/kotlin/cli/build/install/cli/lib/*", "reflex.outbox.MainKt", "{fixture}"]}
 },
 "journeys": ["samples/outbox/journeys/*.json"],
 "warm": "samples/outbox/warm.json",
 "everyResponse": {"node": {"name": "Outbox"}}
}
```

A platform may give `socket` (a loopback `host:port`) instead of `command` to drive a running debug build. With both, the runner starts `command` once and connects to `socket` for each journey. See [docs/real-build.md](../docs/real-build.md).

`root` is relative to the manifest. `{java}` resolves `JAVA_HOME` or `java` on `PATH` to its real binary. `{node}` resolves `node` on `PATH` the same way and `{python}` is the runner’s own Python. `{flutter_tester}` is Flutter’s headless engine in the SDK of `flutter` on `PATH`; build its kernel file with `runner/flutter_kernel.py`. A Java `@file` argument file works too, for a long classpath. Launchers under SIP, such as `/usr/bin/java` or a `/bin/sh` start script, drop `DYLD_*` variables, so the runner never uses them. Any number of platforms may be listed. Parity compares each one with the first. `guard` may override the guard’s `source` and `library` paths. Without it an app manifest uses the guard in this Reflex clone and builds it under the clone’s `.build/`. `stateKeys` maps state keys that differ by name ([State keys with different names](#state-keys-with-different-names)).

## Journey files

A file holds one journey (`name` and `steps`) or several under `journeys`. Top-level keys other than `name`, `steps` and `journeys` are defaults for every journey in the file.

| Journey key | Meaning |
| --- | --- |
| `fixture` | Replaces `{fixture}` in the command. Default: the manifest’s `defaultFixture`. |
| `handshake` | `false` skips the automatic `hello` so steps can test it. |
| `exit` | Expected exit code. Default 0. |
| `network` | `clean` (default) or `denied`. A tripwire journey expects `denied`. |
| `everyResponse` | Replaces the manifest’s per-response expectation. `null` turns it off. |
| `stateKeys` | Replaces the manifest’s state key map. `null` turns it off. See [State keys with different names](#state-keys-with-different-names). |
| `xfail` | Per platform finding id for the whole journey. |

| Step key | Meaning |
| --- | --- |
| `ls` | `true` sends `{"op":"ls"}`. |
| `do` and `input` | Sends `{"op":"do","action":…,"input":…}`. |
| `op` and `input` | Sends a host op. |
| `send` | Sends this object as JSON. |
| `raw` | Sends this exact line, for malformed JSON, duplicate keys or exponent literals. |
| `bytes` | Sends these bytes, written in hex, exactly. No LF is added, so include `0a`. Use it for framing and invalid UTF-8. |
| `replies` | Number of replies a `bytes` step produces. Default: the length of `expect` when it is a list, otherwise 1. `0` is allowed. |
| `expect` | Partial JSON that must match the reply with strict types. |
| `xfail` | Per platform finding id for this step. |
| `parity` | Finding id that marks a known cross-platform byte or value diff. |
| `before` | Precondition. Partial JSON that an `ls` reply must match before the step is sent. If it does not match, the step is not sent, the runner prints the last state and the journey stops. |
| `before_within_ms` | How long `before` may poll `ls`. Default 0: one check. |
| `eventually` | A step of its own that sends only `ls` until a reply matches this partial JSON or the deadline passes. It never re-sends an action. On failure it prints the poll count and the last state. |
| `within_ms` | Deadline for `eventually`. Default 2000, at most 60000. |
| `every_ms` | Wait between polls for `eventually` and `before`. Default 20, from 1 to 1000. |

### Waiting for slow updates

Send the action once, then wait with `eventually`:

```json
{"op": "advanceLater", "input": {"ms": 1000, "afterMs": 150}},
{"eventually": {"node": {"state": {"items": [{"key": "a", "status": "sent"}]}}}, "within_ms": 3000}
```

Only the matching reply goes into the transcript and parity. On failure the last reply does. The number of polls never makes a run flaky. `--evidence` records `polls` for each polling step. Each poll still has the usual 6 second reply timeout. The warm journey may not poll.

## Explore

`runner/explore.py` sends `ls`, `do` and `op` lines to every platform CLI in one process each, under the same guard and canary. It prints each reply without `node.inputs` after the first (`--full` keeps them), then `network=` per platform and a `PARITY` line. A `wait Name [ms]` or `wait {json} [ms]` line sends only `ls` until the screen or reply matches, for actions that load. When a CLI fails it prints the CLI’s last error lines, so there is no reason to launch one by hand. It exits 2 with `BLOCKED` when the guard can’t run, so nobody explores unguarded.

Every CLI process the runner or the explore helper starts gets a fresh empty home folder (`HOME`, `TMPDIR`, `CFFIXED_USER_HOME`, the XDG folders and the JVM’s `user.home`). JVM CLIs also get an in-memory `java.util.prefs` store from `runner/jvm/MemoryPreferences.java`, because on macOS Java Preferences ignore `user.home` and write the account’s own plist.

On macOS a native launcher applies a Seatbelt kernel policy before exec. It denies preferences read/write operations, cfprefsd IPC and file writes outside the private home. This still protects defaults if the target strips DYLD variables. The loaded guard checks the kernel policy before app code runs. A missing launcher, rejected or permissive profile or failed canary blocks the run. The macOS sandbox API is deprecated, so an unsupported OS fails closed rather than running without it.

UserDefaults set/get works within one process, including named suites and `.standard`. A later process starts fresh. `synchronize()` returns false: nothing is saved to the real account. App authors do not need an in-memory UserDefaults subclass for isolation. This is not a test of durable preferences or a general sandbox for hostile code. Unguarded and live socket sessions have no such guarantee.

Run `python3 runner/check_preferences.py` on macOS to compile the tiny Swift canary under gitignored `.build/`. It checks named and standard defaults in two fresh hosts, verifies both host domains are absent with read-only checks and proves missing, invalid or permissive profiles stop before Swift main. A hardened Swift binary also proves the preferences boundary survives stripped DYLD variables; its network guard remains unproved, so a normal journey would fail rather than report PASS. The old guard is rejected before any preferences probe can run. This regression runs in macOS CI.

Swift package unit tests can write host suites too. From the app repo, use `python3 ../reflex/runner/swift_tests.py ios` instead of plain `swift test --package-path ios`. It builds the XCTest bundle without running it, then applies the same preferences policy before executing each bundle. Test writes stay inside the private home. SwiftPM keeps its own build sandbox. This helper supports XCTest suites, not Swift Testing suites. It reports storage protection separately: SDK launchers may strip DYLD, so native unit tests do not prove the network guard.

```bash
python3 runner/explore.py tests/inventory/reflex.json --fixture http-caught 'do OpenProduct {"id":"shirt"}' 'do Save'
```

Adoption guide: [docs/add-to-your-app.md](../docs/add-to-your-app.md).
