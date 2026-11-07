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

## What a run checks

1. `MATCHER`: the runner’s matcher agrees with the kit’s on the shared F-13 cases in `kit/conformance/strict-decoder.json`.
2. `GUARD`: builds `scripts/network_guard.c` when needed, then proves it with a canary. A non-SIP Python under the guard (`DYLD_INSERT_LIBRARIES` on macOS, `LD_PRELOAD` on Linux) must be denied a connect to 192.0.2.1. A failed canary stops the run with exit 2. With no guard for the OS, no C compiler on Linux or `--no-guard` the line reads `GUARD SKIP` and network isolation is not exercised. An unguarded run prints `NETWORK UNCHECKED` for each journey that expects `denied`.
3. Each journey runs in a fresh host process under the guard. Any reply line left over after the last step fails the journey. The runner sends `hello` first and expects the manifest’s protocol and sample. Each step’s response must match `expect` with the type-strict partial matcher and the manifest’s `everyResponse`. At the end the exit code and the guard audit must match the journey’s `exit` and `network`.
4. `SUITE`: one line per platform per repeat with journeys, steps and wall time.
5. `PARITY`: compares every reply across platforms as raw bytes and as parsed JSON with strict types, then the exit code and the network status. A reply whose values match but whose bytes differ prints `PARITY BYTES` with the first differing byte and counts in `byte_diffs`. Both fail the run.
6. `P50` and `COLD`: warm milliseconds per journey with startup excluded, then cold milliseconds per journey with process start included.
7. `RESULT`: `PASS` only with zero unexpected failures and a guard whose canary passed. A clean run without the guard prints `PASS-UNGUARDED` and exits 3. With `--allow-unguarded` it exits 0. Exit 1 on failure. A missing host binary stops the run with exit 2 before any journey. `guard=canary-pass` means the guard ran. `guard=skipped-unavailable` or `guard=skipped-no-guard` adds `network_isolation=NOT-exercised` and the count of unchecked network expectations.

Failure lines name the platform, journey, step, action, the line sent, the first mismatching path with expected and actual values and kinds, then the response with `node.inputs` elided. Parity diffs list every differing path with each platform’s value.

## xfail

A step or a journey may carry `"xfail": {"kotlin": "F-08"}`. A failing annotated step prints `XFAIL` and does not fail the run. An annotated step that passes prints `XPASS` and fails the run until the annotation is removed. `--strict` turns every `XFAIL` back into `FAIL`. A step with `"parity": "F-08"` turns its parity diff into `PARITY KNOWN`.

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

`root` is relative to the manifest. `{java}` resolves `JAVA_HOME` or `java` on `PATH` to its real binary. Launchers under SIP, such as `/usr/bin/java` or a `/bin/sh` start script, drop `DYLD_*` variables, so the runner never uses them. Any number of platforms may be listed. Parity compares each one with the first. `guard` may override the guard’s `source` and `library` paths.

## Journey files

A file holds one journey (`name` and `steps`) or several under `journeys`. Top-level keys other than `name`, `steps` and `journeys` are defaults for every journey in the file.

| Journey key | Meaning |
| --- | --- |
| `fixture` | Replaces `{fixture}` in the command. Default: the manifest’s `defaultFixture`. |
| `handshake` | `false` skips the automatic `hello` so steps can test it. |
| `exit` | Expected exit code. Default 0. |
| `network` | `clean` (default) or `denied`. A tripwire journey expects `denied`. |
| `everyResponse` | Replaces the manifest’s per-response expectation. `null` turns it off. |
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

`runner/explore.py` sends `ls`, `do` and `op` lines to every platform CLI in one process each, under the same guard and canary. It prints each reply without `node.inputs` after the first (`--full` keeps them), then `network=` per platform and a `PARITY` line. A `wait Name [ms]` or `wait {json} [ms]` line sends only `ls` until the screen or reply matches, for actions that load. It exits 2 with `BLOCKED` when the guard can’t run, so nobody explores unguarded.

Every CLI process the runner or the explore helper starts gets a fresh empty home folder (`HOME`, `TMPDIR`, the XDG folders and the JVM’s `user.home`). Saved settings, caches and databases can’t leak from one run or app copy into the next.

```bash
python3 runner/explore.py tests/inventory/reflex.json --fixture http-caught 'do OpenProduct {"id":"shirt"}' 'do Save'
```

Adoption guide: [docs/add-to-your-app.md](../docs/add-to-your-app.md).
