| case | finding | expected | kotlin | swift |
| --- | --- | --- | --- | --- |
| F-01-string-seconds | F-01 | reject "field.type" "$.input.seconds" | PASS reject `field.type` `$.input.seconds` | PASS reject `field.type` `$.input.seconds` |
| F-01-string-negative | F-01 | reject "field.type" "$.input.seconds" | PASS reject `field.type` `$.input.seconds` | PASS reject `field.type` `$.input.seconds` |
| F-01-string-nested | F-01 | reject "field.type" "$.input.meta.level" | PASS reject `field.type` `$.input.meta.level` | PASS reject `field.type` `$.input.meta.level` |
| F-01-string-in-array | F-01 | reject "field.type" "$.input.laps[1]" | PASS reject `field.type` `$.input.laps[1]` | PASS reject `field.type` `$.input.laps[1]` |
| F-01-string-bounded | F-01 | reject "field.type" "$.input.count" | PASS reject `field.type` `$.input.count` | PASS reject `field.type` `$.input.count` |
| F-01-string-protocol | F-01 | reject "field.type" "$.protocol" | PASS reject `field.type` `$.protocol` | PASS reject `field.type` `$.protocol` |
| F-02-fraction | F-02 | reject "int.syntax" "$.input.seconds" | PASS reject `int.syntax` `$.input.seconds` | PASS reject `int.syntax` `$.input.seconds` |
| F-02-whole-fraction | F-02 | reject "int.syntax" "$.input.seconds" | PASS reject `int.syntax` `$.input.seconds` | PASS reject `int.syntax` `$.input.seconds` |
| F-02-exponent | F-02 | reject "int.syntax" "$.input.seconds" | PASS reject `int.syntax` `$.input.seconds` | PASS reject `int.syntax` `$.input.seconds` |
| F-02-exponent-upper | F-02 | reject "int.syntax" "$.input.seconds" | PASS reject `int.syntax` `$.input.seconds` | PASS reject `int.syntax` `$.input.seconds` |
| F-02-exponent-negative | F-02 | reject "int.syntax" "$.input.seconds" | PASS reject `int.syntax` `$.input.seconds` | PASS reject `int.syntax` `$.input.seconds` |
| F-02-exponent-huge | F-02 | reject "int.syntax" "$.input.seconds" | PASS reject `int.syntax` `$.input.seconds` | PASS reject `int.syntax` `$.input.seconds` |
| F-02-fraction-nested | F-02 | reject "int.syntax" "$.input.rows[0].n" | PASS reject `int.syntax` `$.input.rows[0].n` | PASS reject `int.syntax` `$.input.rows[0].n` |
| F-02-integer | F-02 | accept {"seconds":90} | PASS accept {`seconds`:90} | PASS accept {`seconds`:90} |
| F-02-negative-zero | F-02 | accept {"seconds":0} | PASS accept {`seconds`:0} | PASS accept {`seconds`:0} |
| F-02-protocol-fraction | F-02 | reject "int.syntax" "$.protocol" | PASS reject `int.syntax` `$.protocol` | PASS reject `int.syntax` `$.protocol` |
| F-03-true-as-int | F-03 | reject "field.type" "$.input.seconds" | PASS reject `field.type` `$.input.seconds` | PASS reject `field.type` `$.input.seconds` |
| F-03-false-as-int | F-03 | reject "field.type" "$.input.seconds" | PASS reject `field.type` `$.input.seconds` | PASS reject `field.type` `$.input.seconds` |
| F-03-int-as-bool | F-03 | reject "field.type" "$.input.midSet" | PASS reject `field.type` `$.input.midSet` | PASS reject `field.type` `$.input.midSet` |
| F-03-zero-as-bool | F-03 | reject "field.type" "$.input.midSet" | PASS reject `field.type` `$.input.midSet` | PASS reject `field.type` `$.input.midSet` |
| F-03-bool | F-03 | accept {"midSet":true,"seconds":90} | PASS accept {`midSet`:true,`seconds`:90} | PASS accept {`midSet`:true,`seconds`:90} |
| F-04-above-int32 | F-04 | accept {"seconds":2147483648} | PASS accept {`seconds`:2147483648} | PASS accept {`seconds`:2147483648} |
| F-04-below-int32 | F-04 | accept {"seconds":-2147483649} | PASS accept {`seconds`:-2147483649} | PASS accept {`seconds`:-2147483649} |
| F-04-int64-max | F-04 | accept {"seconds":9223372036854775807} | PASS accept {`seconds`:9223372036854775807} | PASS accept {`seconds`:9223372036854775807} |
| F-04-int64-min | F-04 | accept {"seconds":-9223372036854775808} | PASS accept {`seconds`:-9223372036854775808} | PASS accept {`seconds`:-9223372036854775808} |
| F-04-above-int64 | F-04 | reject "int.range" "$.input.seconds" | PASS reject `int.range` `$.input.seconds` | PASS reject `int.range` `$.input.seconds` |
| F-04-below-int64 | F-04 | reject "int.range" "$.input.seconds" | PASS reject `int.range` `$.input.seconds` | PASS reject `int.range` `$.input.seconds` |
| F-04-huge | F-04 | reject "int.range" "$.input.seconds" | PASS reject `int.range` `$.input.seconds` | PASS reject `int.range` `$.input.seconds` |
| F-04-bounded-max | F-04 | accept {"count":100} | PASS accept {`count`:100} | PASS accept {`count`:100} |
| F-04-bounded-above | F-04 | reject "int.range" "$.input.count" | PASS reject `int.range` `$.input.count` | PASS reject `int.range` `$.input.count` |
| F-04-bounded-below | F-04 | reject "int.range" "$.input.count" | PASS reject `int.range` `$.input.count` | PASS reject `int.range` `$.input.count` |
| F-05-int-as-string | F-05 | reject "field.type" "$.input.upNext" | PASS reject `field.type` `$.input.upNext` | PASS reject `field.type` `$.input.upNext` |
| F-05-object-as-string | F-05 | reject "field.type" "$.input.upNext" | PASS reject `field.type` `$.input.upNext` | PASS reject `field.type` `$.input.upNext` |
| F-05-string-as-bool | F-05 | reject "field.type" "$.input.midSet" | PASS reject `field.type` `$.input.midSet` | PASS reject `field.type` `$.input.midSet` |
| F-05-null-optional | F-05 | reject "field.type" "$.input.upNext" | PASS reject `field.type` `$.input.upNext` | PASS reject `field.type` `$.input.upNext` |
| F-05-null-required | F-05 | reject "field.type" "$.input.seconds" | PASS reject `field.type` `$.input.seconds` | PASS reject `field.type` `$.input.seconds` |
| F-05-int-as-object | F-05 | reject "field.type" "$.input.meta" | PASS reject `field.type` `$.input.meta` | PASS reject `field.type` `$.input.meta` |
| F-05-object-as-array | F-05 | reject "field.type" "$.input.laps" | PASS reject `field.type` `$.input.laps` | PASS reject `field.type` `$.input.laps` |
| F-05-unknown | F-05 | reject "field.unknown" "$.input.extra" | PASS reject `field.unknown` `$.input.extra` | PASS reject `field.unknown` `$.input.extra` |
| F-05-unknown-nested | F-05 | reject "field.unknown" "$.input.meta.x" | PASS reject `field.unknown` `$.input.meta.x` | PASS reject `field.unknown` `$.input.meta.x` |
| F-05-unknown-in-array | F-05 | reject "field.unknown" "$.input.rows[1].m" | PASS reject `field.unknown` `$.input.rows[1].m` | PASS reject `field.unknown` `$.input.rows[1].m` |
| F-05-unknown-before-type | F-05 | reject "field.unknown" "$.input.zzz" | PASS reject `field.unknown` `$.input.zzz` | PASS reject `field.unknown` `$.input.zzz` |
| F-05-missing | F-05 | reject "field.missing" "$.input.seconds" | PASS reject `field.missing` `$.input.seconds` | PASS reject `field.missing` `$.input.seconds` |
| F-05-missing-nested | F-05 | reject "field.missing" "$.input.meta.tag" | PASS reject `field.missing` `$.input.meta.tag` | PASS reject `field.missing` `$.input.meta.tag` |
| F-05-all-fields | F-05 | accept {"laps":[1,2],"meta":{"level":3,"tag":"t"},"midSet":false,"rows":[{"n":4}],"seconds":90,"upNext":"Bench · Set 2"} | PASS accept {`laps`:[1,2],`meta`:{`level`:3,`tag`:`t`},`midSet`:false,`rows`:[{`n`:4}],`seconds`:90,`upNext`:`Bench · Set 2`} | PASS accept {`laps`:[1,2],`meta`:{`level`:3,`tag`:`t`},`midSet`:false,`rows`:[{`n`:4}],`seconds`:90,`upNext`:`Bench · Set 2`} |
| F-06-int-input | F-06 | reject "input.not_object" "$.input" | PASS reject `input.not_object` `$.input` | PASS reject `input.not_object` `$.input` |
| F-06-array-input | F-06 | reject "input.not_object" "$.input" | PASS reject `input.not_object` `$.input` | PASS reject `input.not_object` `$.input` |
| F-06-null-input | F-06 | reject "input.not_object" "$.input" | PASS reject `input.not_object` `$.input` | PASS reject `input.not_object` `$.input` |
| F-06-string-input | F-06 | reject "input.not_object" "$.input" | PASS reject `input.not_object` `$.input` | PASS reject `input.not_object` `$.input` |
| F-06-null-input-with-schema | F-06 | reject "input.not_object" "$.input" | PASS reject `input.not_object` `$.input` | PASS reject `input.not_object` `$.input` |
| F-06-empty-object | F-06 | accept {} | PASS accept {} | PASS accept {} |
| F-06-absent | F-06 | accept {} | PASS accept {} | PASS accept {} |
| F-06-extra-key-no-input | F-06 | reject "field.unknown" "$.input.a" | PASS reject `field.unknown` `$.input.a` | PASS reject `field.unknown` `$.input.a` |
| F-06-absent-with-schema | F-06 | reject "field.missing" "$.input.seconds" | PASS reject `field.missing` `$.input.seconds` | PASS reject `field.missing` `$.input.seconds` |
| F-06-args-alias | F-06 | reject "field.unknown" "$.args" | PASS reject `field.unknown` `$.args` | PASS reject `field.unknown` `$.args` |
| F-06-null-args-fallback | F-06 | reject "field.unknown" "$.args" | PASS reject `field.unknown` `$.args` | PASS reject `field.unknown` `$.args` |
| F-06-array-root | F-06 | reject "request.not_object" "$" | PASS reject `request.not_object` `$` | PASS reject `request.not_object` `$` |
| F-06-number-root | F-06 | reject "request.not_object" "$" | PASS reject `request.not_object` `$` | PASS reject `request.not_object` `$` |
| F-07-duplicate | F-07 | reject "json.duplicate_key" "$.input.seconds" | PASS reject `json.duplicate_key` `$.input.seconds` | PASS reject `json.duplicate_key` `$.input.seconds` |
| F-07-duplicate-nested | F-07 | reject "json.duplicate_key" "$.input.meta.tag" | PASS reject `json.duplicate_key` `$.input.meta.tag` | PASS reject `json.duplicate_key` `$.input.meta.tag` |
| F-07-duplicate-in-array | F-07 | reject "json.duplicate_key" "$.input.rows[0].n" | PASS reject `json.duplicate_key` `$.input.rows[0].n` | PASS reject `json.duplicate_key` `$.input.rows[0].n` |
| F-07-duplicate-in-unknown | F-07 | reject "json.duplicate_key" "$.input.x.a" | PASS reject `json.duplicate_key` `$.input.x.a` | PASS reject `json.duplicate_key` `$.input.x.a` |
| F-07-duplicate-op | F-07 | reject "json.duplicate_key" "$.op" | PASS reject `json.duplicate_key` `$.op` | PASS reject `json.duplicate_key` `$.op` |
| F-07-duplicate-action | F-07 | reject "json.duplicate_key" "$.action" | PASS reject `json.duplicate_key` `$.action` | PASS reject `json.duplicate_key` `$.action` |
| F-07-duplicate-input | F-07 | reject "json.duplicate_key" "$.input" | PASS reject `json.duplicate_key` `$.input` | PASS reject `json.duplicate_key` `$.input` |
| F-07-duplicate-protocol | F-07 | reject "json.duplicate_key" "$.protocol" | PASS reject `json.duplicate_key` `$.protocol` | PASS reject `json.duplicate_key` `$.protocol` |
| P-malformed | P | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| P-trailing | P | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| P-leading-zero | P | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| P-lone-surrogate | P | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| P-surrogate-pair | P | response | PASS accept {`seconds`:1,`upNext`:`😀`} | PASS accept {`seconds`:1,`upNext`:`😀`} |
| P-control-char | P | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| P-too-deep | P | reject "json.depth" "$" | PASS reject `json.depth` `$` | PASS reject `json.depth` `$` |
| P-deep-ok | P | reject "field.unknown" "$.input.x" | PASS reject `field.unknown` `$.input.x` | PASS reject `field.unknown` `$.input.x` |
| P-empty-line | P | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| P-handshake-required | P | reject "protocol.handshake_required" "$.op" | PASS reject `protocol.handshake_required` `$.op` | PASS reject `protocol.handshake_required` `$.op` |
| P-unsupported-version | P | reject "protocol.unsupported" "$.protocol" | PASS reject `protocol.unsupported` `$.protocol` | PASS reject `protocol.unsupported` `$.protocol` |
| P-version-missing | P | reject "field.missing" "$.protocol" | PASS reject `field.missing` `$.protocol` | PASS reject `field.missing` `$.protocol` |
| P-hello | P | response | PASS accept  | PASS accept  |
| P-hello-extra | P | reject "field.unknown" "$.client" | PASS reject `field.unknown` `$.client` | PASS reject `field.unknown` `$.client` |
| P-op-missing | P | reject "field.missing" "$.op" | PASS reject `field.missing` `$.op` | PASS reject `field.missing` `$.op` |
| P-op-type | P | reject "field.type" "$.op" | PASS reject `field.type` `$.op` | PASS reject `field.type` `$.op` |
| P-unknown-op | P | reject "request.unknown_op" "$.op" | PASS reject `request.unknown_op` `$.op` | PASS reject `request.unknown_op` `$.op` |
| P-unknown-op-before-handshake | P | reject "request.unknown_op" "$.op" | PASS reject `request.unknown_op` `$.op` | PASS reject `request.unknown_op` `$.op` |
| P-unknown-action | P | reject "action.unknown" "$.action" | PASS reject `action.unknown` `$.action` | PASS reject `action.unknown` `$.action` |
| P-action-case | P | reject "action.unknown" "$.action" | PASS reject `action.unknown` `$.action` | PASS reject `action.unknown` `$.action` |
| P-action-type | P | reject "field.type" "$.action" | PASS reject `field.type` `$.action` | PASS reject `field.type` `$.action` |
| P-action-missing | P | reject "field.missing" "$.action" | PASS reject `field.missing` `$.action` | PASS reject `field.missing` `$.action` |
| P-ls-extra | P | reject "field.unknown" "$.extra" | PASS reject `field.unknown` `$.extra` | PASS reject `field.unknown` `$.extra` |
| P-ls | P | response | PASS accept  | PASS accept  |
| G1-nfc-nfd-escaped | G-1 | reject "field.unknown" "$.é" | PASS reject `field.unknown` `$.é` | PASS reject `field.unknown` `$.é` |
| G1-nfc-nfd-raw | G-1 | reject "field.unknown" "$.é" | PASS reject `field.unknown` `$.é` | PASS reject `field.unknown` `$.é` |
| G1-nfc-nfd-input | G-1 | reject "field.unknown" "$.input.é" | PASS reject `field.unknown` `$.input.é` | PASS reject `field.unknown` `$.input.é` |
| G1-nfc-nfd-nested | G-1 | reject "field.unknown" "$.input.meta.é" | PASS reject `field.unknown` `$.input.meta.é` | PASS reject `field.unknown` `$.input.meta.é` |
| G1-exact-duplicate | G-1 | reject "json.duplicate_key" "$.é" | PASS reject `json.duplicate_key` `$.é` | PASS reject `json.duplicate_key` `$.é` |
| G1-raw-and-escaped-duplicate | G-1 | reject "json.duplicate_key" "$.é" | PASS reject `json.duplicate_key` `$.é` | PASS reject `json.duplicate_key` `$.é` |
| G1-kelvin-key | G-1 | reject "field.unknown" "$.K" | PASS reject `field.unknown` `$.K` | PASS reject `field.unknown` `$.K` |
| G1-field-nfd-undeclared | G-1 | reject "field.unknown" "$.input.é" | PASS reject `field.unknown` `$.input.é` | PASS reject `field.unknown` `$.input.é` |
| G1-field-nfc-declared | G-1 | accept {"é":"x"} | PASS accept {`é`:`x`} | PASS accept {`é`:`x`} |
| G1-field-both-forms | G-1 | reject "field.unknown" "$.input.é" | PASS reject `field.unknown` `$.input.é` | PASS reject `field.unknown` `$.input.é` |
| G1-action-kelvin-sign | G-1 | reject "action.unknown" "$.action" | PASS reject `action.unknown` `$.action` | PASS reject `action.unknown` `$.action` |
| G1-op-kelvin-sign | G-1 | reject "request.unknown_op" "$.op" | PASS reject `request.unknown_op` `$.op` | PASS reject `request.unknown_op` `$.op` |
| G1-string-value-kept | G-1 | accept {"seconds":1,"upNext":"é"} | PASS accept {`seconds`:1,`upNext`:`é`} | PASS accept {`seconds`:1,`upNext`:`é`} |
| G2-lf | G-2 | 1 replies | PASS ok | PASS ok |
| G2-crlf | G-2 | 1 replies | PASS ok | PASS ok |
| G2-two-crlf | G-2 | 2 replies | PASS ok, ok | PASS ok, ok |
| G2-lone-cr-between | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-cr-only-line | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-blank-line | G-2 | 3 replies | PASS ok, reject `json.malformed` `$`, ok | PASS ok, reject `json.malformed` `$`, ok |
| G2-spaces-line | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-no-final-newline | G-2 | 2 replies | PASS ok, ok | PASS ok, ok |
| G2-cr-no-final-newline | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-cr-at-eof | G-2 | 1 replies | PASS ok | PASS ok |
| G2-empty-stream | G-2 | 0 replies | PASS  | PASS  |
| G2-cr-in-string | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-nul-after-object | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-nul-in-string | G-2 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G2-nul-escape-key | G-2 | 1 replies | PASS reject `field.unknown` `$.\u0000` | PASS reject `field.unknown` `$.\u0000` |
| G2-bom-start | G-2 | 2 replies | PASS reject `json.malformed` `$`, reject `protocol.handshake_required` `$.op` | PASS reject `json.malformed` `$`, reject `protocol.handshake_required` `$.op` |
| G2-bom-later-line | G-2 | 2 replies | PASS ok, reject `json.malformed` `$` | PASS ok, reject `json.malformed` `$` |
| G3-invalid-ff | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-qa-repro | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-overlong-slash | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-overlong-nul | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-overlong-3byte | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-overlong-4byte | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-encoded-surrogate | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-encoded-surrogate-pair | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-above-max | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-f5-lead | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-truncated | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-truncated-at-eol | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-lone-continuation | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-in-key | G-3 | 1 replies | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-session-continues | G-3 | 2 replies | PASS reject `json.malformed` `$`, ok | PASS reject `json.malformed` `$`, ok |
| G3-valid-raw-4byte-key | G-3 | 1 replies | PASS reject `field.unknown` `$.😀` | PASS reject `field.unknown` `$.😀` |
| G3-valid-boundaries | G-3 | 1 replies | PASS reject `field.unknown` `$.퟿￿􏿿` | PASS reject `field.unknown` `$.퟿￿􏿿` |
| G3-lone-low-escape | G-3 | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-high-then-text | G-3 | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-high-high | G-3 | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-reversed-pair | G-3 | reject "json.malformed" "$" | PASS reject `json.malformed` `$` | PASS reject `json.malformed` `$` |
| G3-escaped-pair-key | G-3 | reject "field.unknown" "$.😀" | PASS reject `field.unknown` `$.😀` | PASS reject `field.unknown` `$.😀` |
| F-13-bool-vs-int | F-13 | no match | PASS no match | PASS no match |
| F-13-int-vs-string | F-13 | no match | PASS no match | PASS no match |
| F-13-bool-vs-string | F-13 | no match | PASS no match | PASS no match |
| F-13-false-vs-zero | F-13 | no match | PASS no match | PASS no match |
| F-13-string-vs-int | F-13 | no match | PASS no match | PASS no match |
| F-13-int-vs-fraction | F-13 | no match | PASS no match | PASS no match |
| F-13-null-vs-false | F-13 | no match | PASS no match | PASS no match |
| F-13-missing-key | F-13 | no match | PASS no match | PASS no match |
| F-13-array-length | F-13 | no match | PASS no match | PASS no match |
| F-13-array-vs-object | F-13 | no match | PASS no match | PASS no match |
| F-13-partial-object | F-13 | match | PASS match | PASS match |
| F-13-nested | F-13 | match | PASS match | PASS match |
| F-13-equal-bool | F-13 | match | PASS match | PASS match |
| F-13-equal-int64 | F-13 | match | PASS match | PASS match |
| F-13-fraction-equal | F-13 | match | PASS match | PASS match |
| G1-matcher-nfc-vs-nfd-value | G-1 | no match | PASS no match | PASS no match |
| G1-matcher-nfc-vs-nfd-key | G-1 | no match | PASS no match | PASS no match |
| G1-matcher-kelvin-key | G-1 | no match | PASS no match | PASS no match |
| G1-matcher-same-units | G-1 | match | PASS match | PASS match |

Cases: 161. Passed: kotlin 161/161, swift 161/161. Byte-identical replies: 142/142.
