#!/usr/bin/env python3
"""Explore an app through its Reflex CLIs with the network guard always on.

Use: explore.py tests/reflex.json [--platform both] [--fixture NAME] LINE...
Each LINE is `ls`, `do Action {json}`, `op name {json}` or one raw JSON object. With no LINE, lines come from stdin.
All lines run in one process per platform. It prints each reply, the network status and whether the platforms agree.
Exit 0 when every reply is ok and the network stayed clean, 1 otherwise, 2 when the guard cannot run (BLOCKED).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflex_runner as rr  # noqa: E402


def to_request(line):
    line = line.strip()
    if line.startswith("{"):
        return json.loads(line)
    parts = line.split(" ", 2)
    if parts == ["ls"]:
        return {"op": "ls"}
    if parts[0] in ("do", "op") and len(parts) >= 2:
        value = {"op": "do", "action": parts[1]} if parts[0] == "do" else {"op": parts[1]}
        if len(parts) == 3:
            value["input"] = json.loads(parts[2])
        return value
    raise ValueError(f"not a line: {line!r}. Use ls, do Action {{json}}, op name {{json}} or a JSON object")


def brief(reply):
    """Drops node.inputs after the first reply, so a long session costs fewer tokens. --full keeps them."""
    try:
        value = rr.parse(reply)
    except Exception:
        return reply
    if isinstance(value.get("node"), dict):
        value["node"].pop("inputs", None)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def run(manifest, target, fixture, guard, requests):
    host = rr.Host(manifest, target, fixture, guard)
    replies = []
    for request in [{"op": "hello", "protocol": manifest.protocol}] + requests:
        [(line, dead)] = host.send((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
        replies.append(line if line is not None else json.dumps({"ok": False, "error": dead}))
        if dead:
            break
    code, network, _ = host.close()
    return replies, code, network


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest")
    parser.add_argument("lines", nargs="*")
    parser.add_argument("--platform", default="both")
    parser.add_argument("--fixture")
    parser.add_argument("--full", action="store_true", help="keep node.inputs in every reply")
    args = parser.parse_args()
    manifest = rr.Manifest(args.manifest)
    targets = list(manifest.platforms) if args.platform in ("both", "all") else args.platform.split(",")
    try:
        requests = [to_request(l) for l in (args.lines or sys.stdin.read().splitlines()) if l.strip()]
    except ValueError as error:
        print(f"ERROR {error}")
        return 1
    guard, why = rr.build_guard(manifest)
    if not guard:
        print(f"BLOCKED {why}. Never explore without the guard.")
        return 2
    ok, audit, _ = rr.guard_canary(guard)
    if not ok:
        print(f"BLOCKED guard canary did not prove denial: {audit}")
        return 2
    fixture = args.fixture or manifest.default_fixture
    results, failed = {}, False
    for target in targets:
        if target not in manifest.platforms or "command" not in manifest.platforms[target]:
            print(f"BLOCKED platform {target} has no command in {args.manifest}")
            return 2
        if not os.access(manifest.command(target, fixture)[0], os.X_OK):
            print(f"BLOCKED {target} CLI is not built: {manifest.command(target, fixture)[0]}")
            return 2
        replies, code, network = run(manifest, target, fixture, guard, requests)
        results[target] = replies
        print(f"== {target} fixture={fixture} exit={code} network={network}")
        for index, (request, reply) in enumerate(zip([{"op": "hello"}] + requests, replies)):
            print(f"> {json.dumps(request, ensure_ascii=False)}")
            print(f"< {brief(reply) if index and not args.full else reply}")
            try:
                failed |= rr.parse(reply).get("ok") is not True
            except Exception:
                failed = True
        if network != "clean":
            failed = True
            print(f"NETWORK {network}: the CLI tried the network. Add a fixture before testing this action.")
    if len(results) > 1:
        first, *others = targets
        for other in others:
            diffs = [i for i, (a, b) in enumerate(zip(results[first], results[other])) if rr.parse(a) != rr.parse(b)]
            diffs += list(range(min(len(results[first]), len(results[other])), max(len(results[first]), len(results[other]))))
            print(f"PARITY {first}/{other} " + ("same" if not diffs else "differs at line " + ", ".join(map(str, diffs))))
            failed |= bool(diffs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
