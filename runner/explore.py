#!/usr/bin/env python3
"""Explore an app through its Reflex CLIs with the network guard always on.

Use: explore.py tests/reflex.json [--platform both] [--fixture NAME] LINE...
Each LINE is `ls`, `do Action {json}`, `op name {json}`, `wait Name [ms]`, `wait {json} [ms]` or one raw JSON object.
`wait` sends only `ls` until the screen is Name or the reply contains {json}, for up to ms (default 5000). Use it after an action that loads.
With no LINE, lines come from stdin.
All lines run in one process per platform. It prints each reply, the network status and whether the platforms agree.
The manifest’s `stateKeys` map applies to `wait` and to the parity check, as in the runner. Replies print as sent.
Exit 0 when every reply is ok and the network stayed clean, 1 otherwise, 2 when the guard cannot run (BLOCKED).
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflex_runner as rr  # noqa: E402


WAIT_DEFAULT_MS = 5000


def to_wait(rest):
    rest = rest.strip()
    within = WAIT_DEFAULT_MS
    head, _, tail = rest.rpartition(" ")
    if head and tail.isdigit():
        rest, within = head.strip(), int(tail)
    if not 0 < within <= rr.POLL_MAX_MS:
        raise ValueError(f"wait ms must be from 1 to {rr.POLL_MAX_MS}")
    expected = json.loads(rest) if rest.startswith("{") else {"node": {"name": rest}}
    if not rest or not isinstance(expected, dict):
        raise ValueError("wait needs a screen name or a JSON object")
    return {"wait": expected, "within_ms": within}


def to_request(line):
    line = line.strip()
    if line.startswith("wait ") or line == "wait":
        return to_wait(line[4:])
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


def ok_reply(reply):
    try:
        return rr.parse(reply).get("ok") is True
    except Exception:
        return False


def brief(reply):
    """Drops node.inputs after the first reply, so a long session costs fewer tokens. --full keeps them."""
    try:
        value = rr.parse(reply)
    except Exception:
        return reply
    if isinstance(value.get("node"), dict):
        value["node"].pop("inputs", None)
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def run(manifest, target, fixture, guard, requests, rename):
    host = rr.Host(manifest, target, fixture, guard)
    replies = []
    for request in [{"op": "hello", "protocol": manifest.protocol}] + requests:
        if "wait" in request:
            line, dead, _, problem, polls, waited = rr.poll(host, request["wait"], None, request["within_ms"], rr.POLL_EVERY_MS, rename)
            if problem and not dead:
                line = json.dumps({"ok": False, "error": f"wait not met within {request['within_ms']} ms: {problem}"})
        else:
            [(line, dead)] = host.send((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
        replies.append(line if line is not None else json.dumps({"ok": False, "error": dead}))
        if dead:
            break
    code, network, _ = host.close()
    return replies, code, network, host.stderr_tail


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
    keys = rr.state_keys(manifest.state_keys, manifest.platforms)
    results, failed = {}, False
    for target in targets:
        if target not in manifest.platforms or "command" not in manifest.platforms[target]:
            print(f"BLOCKED platform {target} has no command in {args.manifest}")
            return 2
        try:
            executable = manifest.command(target, fixture)[0]
        except rr.NoJava as error:
            print(error)
            return 2
        if not os.access(executable, os.X_OK):
            print(f"BLOCKED {target} CLI is not built: {manifest.command(target, fixture)[0]}")
            return 2
        replies, code, network, stderr = run(manifest, target, fixture, guard, requests, keys.get(target, ({}, []))[0])
        results[target] = replies
        print(f"== {target} fixture={fixture} exit={code} network={network}")
        for index, (request, reply) in enumerate(zip([{"op": "hello"}] + requests, replies)):
            print(f"> {json.dumps(request, ensure_ascii=False)}")
            print(f"< {brief(reply) if index and not args.full else reply}")
            try:
                failed |= rr.parse(reply).get("ok") is not True
            except Exception:
                failed = True
        lines = [l for l in stderr.splitlines() if l.strip() and not l.startswith("Picked up JAVA_TOOL_OPTIONS")]
        if lines and (code != 0 or any(not ok_reply(r) for r in replies)):
            print("STDERR (last 20 lines). Debug from this, never by launching the CLI yourself:")
            print("\n".join("! " + l for l in lines[-20:]))
        if network == "host-did-not-start":
            failed = True
            print(f"NETWORK {network}: the CLI exited before its first reply. Fix the STDERR above first.")
        elif network != "clean":
            failed = True
            print(f"NETWORK {network}: the CLI tried the network. Add a fixture before testing this action.")
    if len(results) > 1:
        first, *others = targets

        def shared(target, reply):
            rename, only = keys.get(target, ({}, []))
            return rr.drop_state(rr.rename_state(rr.parse(reply), rename)[0], only)[0]

        for other in others:
            diffs = [i for i, (a, b) in enumerate(zip(results[first], results[other])) if shared(first, a) != shared(other, b)]
            diffs += list(range(min(len(results[first]), len(results[other])), max(len(results[first]), len(results[other]))))
            print(f"PARITY {first}/{other} " + ("same" if not diffs else "differs at line " + ", ".join(map(str, diffs))))
            failed |= bool(diffs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
