#!/usr/bin/env python3
"""Test host for stateKeys: runs a real CLI and gives node.state other key names, the way a second app
might. The first argument is a JSON file (renames.json): `rename` maps a dotted path to a new last key and `add` sets extra
state keys. A list on the path applies to each item. Values are never changed."""
import json
import subprocess
import sys


def at_path(value, parts, visit):
    if isinstance(value, list):
        for item in value:
            at_path(item, parts, visit)
    elif isinstance(value, dict):
        if len(parts) == 1:
            visit(value, parts[0])
        elif parts[0] in value:
            at_path(value[parts[0]], parts[1:], visit)


def rename(parent, key, new):
    if key in parent:
        parent[new] = parent.pop(key)


with open(sys.argv[1], encoding="utf-8") as handle:
    spec = json.load(handle)
host = subprocess.Popen(sys.argv[2:], stdin=sys.stdin, stdout=subprocess.PIPE)
for line in host.stdout:
    value = json.loads(line)
    state = value.get("node", {}).get("state")
    if isinstance(state, dict):
        for path, new in spec.get("rename", {}).items():
            at_path(state, path.split("."), lambda parent, key: rename(parent, key, new))
        state.update(spec.get("add", {}))
    sys.stdout.write(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    sys.stdout.flush()
sys.exit(host.wait())
