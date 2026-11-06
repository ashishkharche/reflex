#!/usr/bin/env python3
"""Red host for the byte parity check: runs a real CLI and rewrites each reply with the same
JSON value but different bytes (a space after every separator). Parsed parity still holds."""
import json
import subprocess
import sys

host = subprocess.Popen(sys.argv[1:], stdin=sys.stdin, stdout=subprocess.PIPE)
for line in host.stdout:
    value = json.loads(line)
    sys.stdout.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    sys.stdout.flush()
sys.exit(host.wait())
