# Protocol changelog

History of the Reflex NDJSON protocol text. Newest first.

## 1, clarified (6 Nov 2026, kit 1.0.1)

Still protocol 1. These rules define behaviour the first text left open. Swift and Kotlin disagreed on each one. A client that sends LF-terminated strict UTF-8 lines sees no change. No error code was added.

- Keys, `op` names, action titles and schema field names compare by exact UTF-16 code units with no Unicode normalisation (G-1). `{"op":"ls","\u00e9":1,"e\u0301":2}` is `field.unknown` at `$.e\u0301` on both platforms. Swift used to report `json.duplicate_key` because Swift `String` equality uses canonical equivalence. The same fix covers field lookup, unknown-key detection, action titles, op names and the `Expect` matcher on Swift.
- LF is the only line terminator (G-2). CR is JSON whitespace inside the line. `{"op":"ls"}\r{"op":"ls"}\n` is one line and one `json.malformed` reply on both platforms. Kotlin used to treat the lone CR as a terminator and send two replies. Bytes after the last LF are one more line at EOF.
- Invalid UTF-8 is `json.malformed` at `$` on both platforms and is never echoed (G-3). Both kits used to accept it and store replacement characters: five on Swift and three on Kotlin for the QA repro.
- The conformance fixture adds stream cases with exact reply bytes. The runner fails on any reply byte difference between platforms and can send raw bytes.

## 1 (6 Nov 2026)

First versioned protocol. Differences from the unversioned inventory CLI it replaces:

- Every session starts with `{"op":"hello","protocol":1}`. Other operations before it fail with `protocol.handshake_required`.
- `error` is an object with `code` and `path` instead of one fixed string.
- Integers are Int64 on both platforms. Fractions and exponents such as `5.0` and `1e2` fail with `int.syntax`. Values outside Int64 fail with `int.range`.
- `input` must be absent or an object. `null` fails with `input.not_object`. `args` is an unknown field.
- Duplicate keys fail with `json.duplicate_key` and the key’s path at any depth.
- Responses are canonical: keys sorted by UTF-16 code unit with no whitespace. Swift and Kotlin emit the same bytes.
- Hosts may declare extra operations next to `hello`, `ls` and `do`. The outbox sample adds `advance` and `network`.
