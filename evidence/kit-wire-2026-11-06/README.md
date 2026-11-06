# Kit wire parity, 6 Nov 2026

Runs on macOS for G-1 to G-3 (kit 1.0.1). Command-line tools and unit tests only.

| file | content |
| --- | --- |
| `probe-before-6f8662a.log` | Raw bytes sent to both sample CLIs before the kit 1.0.1 wire fix. 13 of 142 sends differ. Its `lines=0` counts are a probe bug fixed before the after run. The reply lines are complete. The filename keeps a private-history SHA. |
| `probe-after.log` | The same sends after the fix. 142 of 142 byte-identical. |
| `wire_probe.py`, `wire-probe-cases.tsv` | The probe and its cases. `<LF>` `<CR>` and `<xHH>` become raw bytes. `<EOF>` drops the final LF. |
| `g1-red-old-swift-kit.log` | The G-1 fixture cases against the old Swift kit sources: 11 failures. |
| `conformance-*.log`, `conformance-table.md`, `*.ndjson` | 161 cases per platform. 142 replies compared byte for byte. |
| `runner-*.log`, `transcript-*.ndjson` | Both samples with `--platform both --repeat 3 --timings 20` and with `--strict`. |
| `red-*.log` | Red paths. Each must exit 1. |
| `swift-test-*.log`, `kotlin-test-*.log`, `build.log` | Unit tests and builds. |
| `leftover-processes.log` | Matching processes after the runs. The one line is a Gradle daemon started at 01:52:11 before any Gradle run here. All Gradle runs here used `--no-daemon`. No reflex CLI or runner process was left. |
