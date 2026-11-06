#!/usr/bin/env python3
"""Human-readable ls / do / op frontend for a sample CLI. Transport stays NDJSON protocol v1."""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
hosts = {
    ("swift", "inventory"): root / "swift/.build/debug/inventory-cli",
    ("kotlin", "inventory"): root / "kotlin/cli/build/install/cli/bin/cli",
    ("swift", "outbox"): root / "samples/outbox/swift/.build/debug/outbox-cli",
    ("kotlin", "outbox"): root / "samples/outbox/kotlin/cli/build/install/cli/bin/cli",
}
if len(sys.argv) < 2 or sys.argv[1] not in ("swift", "kotlin") or (len(sys.argv) > 2 and sys.argv[2] not in ("inventory", "outbox")):
    raise SystemExit("Use: console.py swift|kotlin [inventory|outbox] [fixture]")
platform = sys.argv[1]
sample = sys.argv[2] if len(sys.argv) > 2 else "inventory"
command = [str(hosts[(platform, sample)])] + sys.argv[3:4]
with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding="utf-8") as process:
    def send(value):
        process.stdin.write(json.dumps(value, ensure_ascii=False) + "\n"); process.stdin.flush()
        print(process.stdout.readline().rstrip(), flush=True)
    send({"op": "hello", "protocol": 1})
    for line in sys.stdin:
        parts = line.strip().split(" ", 2)
        try:
            if parts == ["ls"]:
                value = {"op": "ls"}
            elif parts[0] in ("do", "op") and len(parts) >= 2:
                value = {"op": "do", "action": parts[1]} if parts[0] == "do" else {"op": parts[1]}
                if len(parts) == 3:
                    value["input"] = json.loads(parts[2])
            else:
                print(json.dumps({"ok": False, "error": "Use ls, do Action [json] or op name [json]"}), flush=True)
                continue
        except ValueError:
            print(json.dumps({"ok": False, "error": "Invalid JSON"}), flush=True)
            continue
        send(value)
    process.stdin.close()
    raise SystemExit(process.wait())
