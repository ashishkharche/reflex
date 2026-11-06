#!/usr/bin/env python3
"""Drives a running debug build of the inventory sample over its loopback socket and checks that
each external action changes the real screen, not just the state the socket returns.

  python3 scripts/live_ui_check.py ios --device UDID --port 47814 --evidence DIR
  python3 scripts/live_ui_check.py android --device emulator-5554 --port 47815 --evidence DIR

iOS reads the simulator screen with `simctl io screenshot` and Vision OCR (scripts/ocr_text.swift).
Android reads the view tree with `uiautomator dump`. The run restores the starting stock at the end.
"""
import argparse
import json
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Wire:
    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=6)
        self.file = self.sock.makefile("rwb")

    def send(self, request):
        self.file.write((json.dumps(request, separators=(",", ":")) + "\n").encode("utf-8"))
        self.file.flush()
        reply = json.loads(self.file.readline())
        print(f"WIRE send={json.dumps(request, separators=(',', ':'))} ok={reply.get('ok')} node={reply['node']['name']} "
              f"state={json.dumps(reply['node']['state'], separators=(',', ':'))}", flush=True)
        if reply.get("ok") is not True:
            raise SystemExit(f"FAIL wire reply not ok: {reply}")
        return reply


def ios_text(device, shot):
    subprocess.run(["xcrun", "simctl", "io", device, "screenshot", str(shot)], check=True, capture_output=True)
    ocr = ROOT / ".build/ocr_text"
    if not ocr.exists() or ocr.stat().st_mtime < (ROOT / "scripts/ocr_text.swift").stat().st_mtime:
        subprocess.run(["swiftc", "-O", str(ROOT / "scripts/ocr_text.swift"), "-o", str(ocr)], check=True)
    return subprocess.run([str(ocr), str(shot)], check=True, capture_output=True, text=True).stdout.splitlines()


def android_text(device, dump):
    subprocess.run(["adb", "-s", device, "shell", "uiautomator", "dump", "/sdcard/reflex-ui.xml"], check=True, capture_output=True)
    xml = subprocess.run(["adb", "-s", device, "exec-out", "cat", "/sdcard/reflex-ui.xml"], check=True, capture_output=True,
                         text=True).stdout
    dump.write_text(xml, encoding="utf-8")
    return [t for t in re.findall(r'text="([^"]*)"', xml) if t]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("platform", choices=["ios", "android"])
    parser.add_argument("--device", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--evidence", default=".build/live-ui")
    args = parser.parse_args()
    folder = Path(args.evidence)
    folder.mkdir(parents=True, exist_ok=True)
    failures = 0
    checks = 0

    def screen(want, absent=(), deadline_s=6):
        """Polls the real screen until every `want` line is visible and every `absent` line is gone."""
        nonlocal failures, checks
        checks += 1
        started = time.monotonic()
        while True:
            path = folder / f"{args.platform}-{checks:02d}.{'png' if args.platform == 'ios' else 'xml'}"
            lines = ios_text(args.device, path) if args.platform == "ios" else android_text(args.device, path)
            missing = [w for w in want if not any(w == line.strip() for line in lines)]
            present = [a for a in absent if any(a == line.strip() for line in lines)]
            if not missing and not present:
                print(f"UI PASS check={checks} want={want} absent={list(absent)} file={path.name}", flush=True)
                return
            if time.monotonic() - started > deadline_s:
                failures += 1
                print(f"UI FAIL check={checks} missing={missing} still_present={present} screen={lines} file={path.name}", flush=True)
                return
            time.sleep(0.5)

    wire = Wire(args.port)
    hello = wire.send({"op": "hello", "protocol": 1})
    start = {p["id"]: p["quantity"] for p in hello["node"]["state"].get("products", [])}
    if hello["node"]["name"] != "InventoryList" or "shirt" not in start:
        raise SystemExit("FAIL the app must start on the list screen")
    shirt = start["shirt"]
    target = 7 if shirt != 7 else 8
    screen([f"Cotton shirt: {shirt}"])
    wire.send({"op": "do", "action": "OpenProduct", "input": {"id": "shirt"}})
    screen([f"Quantity: {shirt}"], absent=[f"Cotton shirt: {shirt}"])
    wire.send({"op": "do", "action": "SetQuantity", "input": {"quantity": target}})
    screen([f"Quantity: {target}"], absent=[f"Quantity: {shirt}", "Stock saved"])
    wire.send({"op": "do", "action": "Save"})
    screen([f"Quantity: {target}", "Stock saved"])
    wire.send({"op": "do", "action": "goBack"})
    screen([f"Cotton shirt: {target}"], absent=[f"Quantity: {target}"])
    wire.send({"op": "do", "action": "OpenProduct", "input": {"id": "shirt"}})
    wire.send({"op": "do", "action": "SetQuantity", "input": {"quantity": shirt}})
    wire.send({"op": "do", "action": "Save"})
    wire.send({"op": "do", "action": "goBack"})
    screen([f"Cotton shirt: {shirt}"], absent=[f"Cotton shirt: {target}"])
    print(f"RESULT LIVE-UI {'PASS' if failures == 0 else 'FAIL'} platform={args.platform} checks={checks} failures={failures}")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
