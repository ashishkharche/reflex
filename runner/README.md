# Reflex runner

`reflex_runner.py` runs shared journey files against every platform CLI a manifest names. It uses only the Python standard library and speaks [protocol v1](../docs/protocol/v1.md).

```bash
python3 runner/reflex_runner.py tests/inventory/reflex.json --platform both --repeat 3 --timings 20
python3 runner/reflex_runner.py samples/outbox/reflex.json --platform swift samples/outbox/journeys/02-backoff.json
python3 runner/reflex_runner.py samples/outbox/reflex.json --strict --evidence /tmp/outbox-evidence
```

| flag | effect |
| --- | --- |
| `--platform` | One platform name, a comma list or `both` (every platform in the manifest). |
| `--repeat N` | Runs the suite N times per platform. Every repeat must produce the same raw transcript as the first. |
| `--timings N` | Runs the manifest’s warm journey once unmeasured and then N measured times in one process. Prints the p50. `0` skips it. |
| `--strict` | Ignores `xfail` annotations so every finding fails. |
| `--no-guard` | Runs without the network guard and says so in the `GUARD` line. |
| `--evidence DIR` | Writes raw NDJSON transcripts of repeat 1 per platform. |

Positional journey paths replace the manifest’s journey list.

## What a run checks

1. `MATCHER`: the runner’s matcher agrees with the kit’s on the shared F-13 cases in `kit/conformance/strict-decoder.json`.
2. `GUARD`: builds `scripts/network_guard.c` when needed, then proves it with a canary. A Homebrew Python under `DYLD_INSERT_LIBRARIES` must be denied a connect to 192.0.2.1. A failed canary stops the run with exit 2. Off macOS the line reads `GUARD SKIP` and network isolation is not exercised. An unguarded run prints `NETWORK UNCHECKED` for each journey that expects `denied`.
3. Each journey runs in a fresh host process under the guard. Any reply line left over after the last step fails the journey. The runner sends `hello` first and expects the manifest’s protocol and sample. Each step’s response must match `expect` with the type-strict partial matcher and the manifest’s `everyResponse`. At the end the exit code and the guard audit must match the journey’s `exit` and `network`.
4. `SUITE`: one line per platform per repeat with journeys, steps and wall time.
5. `PARITY`: compares every reply across platforms as raw bytes and as parsed JSON with strict types, then the exit code and the network status. A reply whose values match but whose bytes differ prints `PARITY BYTES` with the first differing byte and counts in `byte_diffs`. Both fail the run.
6. `P50` and `COLD`: warm milliseconds per journey with startup excluded, then cold milliseconds per journey with process start included.
7. `RESULT`: `PASS` only with zero unexpected failures. Exit 0 on pass and 1 on failure. A missing host binary stops the run with exit 2 before any journey. `guard=canary-pass` means the guard ran. `guard=skipped-not-macos` or `guard=skipped-no-guard` adds `network_isolation=NOT-exercised` and the count of unchecked network expectations.

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

`root` is relative to the manifest. `{java}` resolves `JAVA_HOME` or `java` on `PATH` to its real binary. Launchers under SIP, such as `/usr/bin/java` or a `/bin/sh` start script, drop `DYLD_*` variables, so the runner never uses them. Any number of platforms may be listed. Parity compares each one with the first. `guard` may override the guard’s `source` and `library` paths.

## Journey files

A file holds one journey (`name` and `steps`) or several under `journeys`. Top-level keys other than `name`, `steps` and `journeys` are defaults for every journey in the file.

| journey key | meaning |
| --- | --- |
| `fixture` | Replaces `{fixture}` in the command. Default: the manifest’s `defaultFixture`. |
| `handshake` | `false` skips the automatic `hello` so steps can test it. |
| `exit` | Expected exit code. Default 0. |
| `network` | `clean` (default) or `denied`. A tripwire journey expects `denied`. |
| `everyResponse` | Replaces the manifest’s per-response expectation. `null` turns it off. |
| `xfail` | Per platform finding id for the whole journey. |

| step key | meaning |
| --- | --- |
| `ls` | `true` sends `{"op":"ls"}`. |
| `do` and `input` | Sends `{"op":"do","action":…,"input":…}`. |
| `op` and `input` | Sends a host op. |
| `send` | Sends this object as JSON. |
| `raw` | Sends this exact line, for malformed JSON, duplicate keys or exponent literals. |
| `bytes` | Sends these bytes, written in hex, exactly. No LF is added, so include `0a`. Use it for framing and invalid UTF-8. |
| `replies` | Number of replies a `bytes` step produces. Default: the length of `expect` when it is a list, otherwise 1. `0` is allowed. |
| `close` | `true` closes stdin after the step, for a last line with no LF. |
| `expect` | Type-strict partial match on the response. A list holds one match per reply. Default `{"ok":true}`. |
| `unchanged` | The response must equal the previous response apart from `ok` and `error`. |
| `xfail` and `parity` | See above. |
| `note` | Free text. |

The matcher follows ReflexKit’s `Expect`: expected object keys must be present, arrays match element by element with the same length and scalars need the same JSON kind. `true` is not `1`, `"90"` is not `90` and `90` is not `90.0`.

## Red paths

`runner/red/` holds journeys that must fail: `wrong-expect.json`, `xpass.json` and `parity-manifest.json` exit 1. `xfail.json` passes and fails under `--strict`.
