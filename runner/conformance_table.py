#!/usr/bin/env python3
"""Merge the kit conformance reports (swift.ndjson, kotlin.ndjson, …) into one Markdown table.

Every decoder and stream row carries `wire`, the exact reply bytes. A case whose bytes differ
between platforms fails even when both platforms pass their own expectations."""
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
reports = {}
for path in sorted(folder.glob("*.ndjson")):
    reports[path.stem] = {row["id"]: row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if row}
if not reports:
    raise SystemExit(f"no *.ndjson reports in {folder}")
platforms = list(reports)
ids = list(next(iter(reports.values())))
for name, rows in reports.items():
    if list(rows) != ids:
        raise SystemExit(f"{name} ran different cases")
print("| case | finding | expected | " + " | ".join(platforms) + " |")
print("| --- | --- | --- | " + " | ".join("---" for _ in platforms) + " |")
failed = 0
for case in ids:
    first = reports[platforms[0]][case]
    cells = []
    for name in platforms:
        row = reports[name][case]
        failed += not row["pass"]
        cells.append(("PASS " if row["pass"] else "FAIL ") + row["got"].replace("|", "\\|").replace('"', "`", 2).replace('"', "`"))
    print(f"| {case} | {first['finding']} | {first['expected'].replace('|', chr(92) + '|')} | " + " | ".join(cells) + " |")
byte_diffs = [case for case in ids
              if "wire" in reports[platforms[0]][case]
              and len({reports[name][case].get("wire") for name in platforms}) > 1]
for case in byte_diffs:
    print(f"\nBYTES DIFFER {case}: " + " | ".join(f"{name}={reports[name][case].get('wire')!r}" for name in platforms))
compared = sum("wire" in reports[platforms[0]][case] for case in ids)
failed += len(byte_diffs)
totals = ", ".join(f"{name} {sum(r['pass'] for r in rows.values())}/{len(rows)}" for name, rows in reports.items())
print(f"\nCases: {len(ids)}. Passed: {totals}. Byte-identical replies: {compared - len(byte_diffs)}/{compared}.")
sys.exit(1 if failed else 0)
