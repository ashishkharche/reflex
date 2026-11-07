#!/usr/bin/env python3
"""Reflex journey runner. Standard library only.

Runs shared journey files against N platform CLIs over NDJSON protocol v1, checks each step
with a type-strict partial matcher, compares every reply across platforms step by step as raw
bytes and as parsed JSON, tracks xfail annotations (XPASS fails the run), repeats suites for
determinism, measures warm p50 and runs every host under the network guard (DYLD on macOS,
LD_PRELOAD on Linux) after a canary proves denial. A run without the guard never prints a plain PASS. Steps may send raw bytes, so framing and UTF-8 rules are exercised too.
Manifest and journey formats: runner/README.md. Protocol: docs/protocol/v1.md.
"""
import argparse
import glob
import json
import os
import platform as host_platform
import select
import shutil
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROTOCOL = 1
TIMEOUT_S = 6
POLL_DEFAULT_MS = 2000
POLL_MAX_MS = 60000
POLL_EVERY_MS = 20
LS_WIRE = '{"op":"ls"}'
GUARD_ENV = "DYLD_INSERT_LIBRARIES" if sys.platform == "darwin" else "LD_PRELOAD"
EXIT_UNGUARDED = 3
IGNORED_FOR_UNCHANGED = {"ok", "error", "protocol", "sample", "kit", "supported"}


class DuplicateKey(ValueError):
    pass


def no_dupes(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise DuplicateKey(key)
        seen[key] = value
    return seen


def parse(text):
    return json.loads(text, object_pairs_hook=no_dupes)


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def kind(value):
    if value is None: return "null"
    if isinstance(value, bool): return "boolean"
    if isinstance(value, int): return "integer"
    if isinstance(value, float): return "number"
    if isinstance(value, str): return "string"
    if isinstance(value, list): return "array"
    return "object"


def same(a, b):
    """Strict equality: same JSON kind at every level. 1 != true, 90 != 90.0, "90" != 90."""
    if kind(a) != kind(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def mismatch(actual, expected, path="$"):
    """Type-strict partial match, the same rules as ReflexKit Expect. Returns None or a reason."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(expected):
            if key not in actual:
                return f"{path}.{key} expected={dumps(expected[key])} actual=<absent>"
            problem = mismatch(actual[key], expected[key], f"{path}.{key}")
            if problem:
                return problem
        return None
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return f"{path} expected={len(expected)} items actual={len(actual)} items"
        for index, (a, e) in enumerate(zip(actual, expected)):
            problem = mismatch(a, e, f"{path}[{index}]")
            if problem:
                return problem
        return None
    if same(actual, expected):
        return None
    return f"{path} expected={dumps(expected)} ({kind(expected)}) actual={dumps(actual)} ({kind(actual)})"


def diff_paths(a, b, names, path="$"):
    if same(a, b):
        return []
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append(f"{path}.{key} {names[0]}={dumps(a.get(key, '<absent>'))} {names[1]}={dumps(b.get(key, '<absent>'))}")
            else:
                out.extend(diff_paths(a[key], b[key], names, f"{path}.{key}"))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for index, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_paths(x, y, names, f"{path}[{index}]"))
        return out
    return [f"{path} {names[0]}={dumps(a)} {names[1]}={dumps(b)}"]


def brief(value):
    """Readable response: node.inputs elided (schemas rarely change). Raw stays in transcripts."""
    if isinstance(value, dict) and isinstance(value.get("node"), dict):
        value = dict(value, node={k: v for k, v in value["node"].items() if k != "inputs"})
    return dumps(value)


class Manifest:
    def __init__(self, path):
        self.path = Path(path).resolve()
        data = parse(self.path.read_text(encoding="utf-8"))
        self.sample = data["sample"]
        self.protocol = data.get("protocol", PROTOCOL)
        self.root = (self.path.parent / data.get("root", ".")).resolve()
        self.platforms = data["platforms"]
        self.journeys = data["journeys"]
        self.warm = data.get("warm")
        self.every = data.get("everyResponse")
        self.default_fixture = data.get("defaultFixture", "default")
        guard = data.get("guard", {})
        self.guard_source = self.root / guard.get("source", "scripts/network_guard.c")
        self.guard_library = self.root / guard.get("library", ".build/network_guard.dylib")
        self.conformance = self.root / data["conformance"] if data.get("conformance") else None

    def command(self, target, fixture):
        java = os.environ.get("JAVA_HOME")
        java = str(Path(java) / "bin/java") if java else shutil.which("java") or "java"
        # SIP-protected launchers (/usr/bin/java, /bin/sh scripts) drop DYLD variables; use the real binary.
        java = os.path.realpath(java)
        values = {"root": str(self.root), "fixture": fixture, "java": java, "python": os.path.realpath(sys.executable)}
        return [part.format(**values) for part in self.platforms[target]["command"]]

    def journey_paths(self, extra):
        if extra:
            return [str(Path(p).resolve()) for p in extra]
        out = []
        for pattern in self.journeys:
            out.extend(sorted(glob.glob(str(self.root / pattern))))
        return out


def load_journeys(manifest, paths):
    out = []
    for path in paths:
        data = parse(Path(path).read_text(encoding="utf-8"))
        rel = os.path.relpath(path, manifest.root)
        base = {k: v for k, v in data.items() if k not in ("journeys", "steps", "name")}
        items = data["journeys"] if "journeys" in data else [data]
        for item in items:
            journey = dict(base, **item)
            journey["id"] = f"{rel}#{item['name']}"
            journey.setdefault("fixture", manifest.default_fixture)
            out.append(journey)
    return out


def wire_for(step):
    if "bytes" in step:
        return "bytes:" + step["bytes"]
    if "raw" in step:
        return step["raw"]
    if "send" in step:
        return dumps(step["send"])
    if step.get("ls"):
        return dumps({"op": "ls"})
    if "do" in step:
        command = {"op": "do", "action": step["do"]}
    elif "op" in step:
        command = {"op": step["op"]}
    else:
        raise ValueError(f"step has no send, raw, ls, do or op: {step}")
    if "input" in step:
        command["input"] = step["input"]
    return dumps(command)


def payload_for(step):
    """The exact bytes a step writes. `bytes` steps are sent as given, with no LF added."""
    if "bytes" in step:
        return bytes.fromhex(step["bytes"])
    return (wire_for(step) + "\n").encode("utf-8")


def expectations(step):
    """One expectation per reply. A `bytes` step may expect several replies or none."""
    expect = step.get("expect", {"ok": True})
    count = step.get("replies", len(expect) if isinstance(expect, list) else 1)
    expect = expect if isinstance(expect, list) else [expect] * count
    if len(expect) != count:
        raise ValueError(f"step expects {len(expect)} replies but replies is {count}: {step}")
    return expect


def label(step):
    if "bytes" in step:
        return "bytes " + step["bytes"][:60]
    if "raw" in step:
        return "raw " + step["raw"][:60]
    if "do" in step:
        return step["do"]
    if "send" in step:
        return step["send"].get("action") or step["send"].get("op") if isinstance(step["send"], dict) else "send"
    return "ls" if step.get("ls") else step.get("op", "?")


def poll_settings(step, within_key):
    """Deadline and interval for a polling check. Raises ValueError on a bad journey."""
    within = step.get(within_key, POLL_DEFAULT_MS if within_key == "within_ms" else 0)
    every = step.get("every_ms", POLL_EVERY_MS)
    for name, value, low, high in ((within_key, within, 0, POLL_MAX_MS), ("every_ms", every, 1, 1000)):
        if kind(value) != "integer" or not low <= value <= high:
            raise ValueError(f"{name} must be an integer from {low} to {high}, got {dumps(value)}")
    return within, every


def poll(host, expected, every_response, within_ms, every_ms):
    """Sends only `ls` until a reply matches `expected` or the deadline passes. Never re-sends an action.
    Returns (line, dead, response, problem, polls, waited_ms). `problem` is None on a match."""
    started = time.monotonic()
    deadline = started + within_ms / 1000
    polls = 0
    while True:
        [(line, dead)] = host.send((LS_WIRE + "\n").encode("utf-8"))
        polls += 1
        response, problem = None, dead
        if line is not None and not dead:
            try:
                response = parse(line)
            except ValueError as error:
                problem = f"response is not JSON: {error}"
            else:
                problem = mismatch(response, expected) if isinstance(response, dict) else "response is not an object"
                if not problem and every_response:
                    problem = mismatch(response, every_response)
        waited = round((time.monotonic() - started) * 1000)
        if not problem or dead or time.monotonic() + every_ms / 1000 > deadline:
            return line, dead, response, problem, polls, waited
        time.sleep(every_ms / 1000)


class Host:
    def __init__(self, manifest, target, fixture, guard):
        self.target = target
        self.audit = None
        # A fresh home per process, so saved settings, caches or databases never leak between runs or app copies.
        self.home = tempfile.mkdtemp(prefix="reflex-home-")
        env = dict(os.environ, HOME=self.home, TMPDIR=self.home, XDG_CONFIG_HOME=self.home + "/.config",
                   XDG_DATA_HOME=self.home + "/.local/share", XDG_CACHE_HOME=self.home + "/.cache")
        # The JVM takes user.home from the account, not HOME, so pass it as well.
        env["JAVA_TOOL_OPTIONS"] = (env.get("JAVA_TOOL_OPTIONS", "") + f" -Duser.home={self.home} -Djava.io.tmpdir={self.home}").strip()
        if guard:
            handle = tempfile.NamedTemporaryFile(prefix="reflex-net-", delete=False)
            handle.close()
            self.audit = handle.name
            env.update({GUARD_ENV: str(guard), "REFLEX_NETWORK_LOG": self.audit})
        self.stderr = tempfile.TemporaryFile()
        self.proc = subprocess.Popen(manifest.command(target, fixture), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.stderr, env=env, bufsize=0)
        self.buffer = b""
        self.dead = None
        self.closed = False

    def _read_line(self):
        """One reply line as bytes without its LF, or None at EOF or after the deadline."""
        deadline = time.monotonic() + TIMEOUT_S
        while b"\n" not in self.buffer:
            left = deadline - time.monotonic()
            ready, _, _ = select.select([self.proc.stdout], [], [], max(left, 0))
            if not ready:
                return None, False
            chunk = os.read(self.proc.stdout.fileno(), 65536)
            if not chunk:
                return None, True
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line, True

    def send(self, data, replies=1, close=False):
        """Writes the exact bytes, then reads `replies` lines. Returns a list of (line, dead)."""
        if self.dead:
            return [(None, self.dead)] * replies
        try:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()
            if close:
                self.proc.stdin.close()
                self.closed = True
        except BrokenPipeError:
            pass
        out = []
        for _ in range(replies):
            raw, ready = self._read_line()
            if raw is None:
                try:
                    code = self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill(); self.proc.wait(); code = "timeout"
                self.stderr.seek(0)
                err = self.stderr.read().decode("utf-8", "replace").strip()[-200:]
                self.dead = f"EOF exit={code} stderr={err!r}" if ready else f"no response in {TIMEOUT_S}s"
                out.append((None, self.dead))
                continue
            try:
                out.append((raw.decode("utf-8"), None))
            except UnicodeDecodeError:
                out.append((raw.decode("utf-8", "backslashreplace"), "reply is not UTF-8"))
        return out

    def network(self):
        if not self.audit:
            return "unguarded"
        text = Path(self.audit).read_text()
        if "READY" not in text:
            return "guard-not-loaded"
        return "denied" if "DENIED" in text else "clean"

    def close(self):
        """Closes stdin and returns the exit code, the network status and any reply lines nobody asked for."""
        if not self.closed:
            try:
                self.proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
        try:
            code = self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill(); self.proc.wait(); code = "timeout"
        rest = self.buffer + self.proc.stdout.read()
        self.proc.stdout.close()
        self.stderr.close()
        status = self.network()
        if self.audit:
            Path(self.audit).unlink(missing_ok=True)
        shutil.rmtree(self.home, ignore_errors=True)
        return code, status, rest


class SocketConn:
    """A live host reached over a loopback socket (a debug build of an app). Same interface as Host.
    State lives as long as the app, so exit codes and the network guard do not apply."""

    def __init__(self, address):
        name, port = address.rsplit(":", 1)
        if name not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(f"socket {address}: only loopback addresses are allowed")
        self.sock = socket.create_connection((name, int(port)), timeout=TIMEOUT_S)
        self.buffer = b""
        self.dead = None
        self.closed = False

    def _read_line(self):
        deadline = time.monotonic() + TIMEOUT_S
        while b"\n" not in self.buffer:
            left = deadline - time.monotonic()
            ready, _, _ = select.select([self.sock], [], [], max(left, 0))
            if not ready:
                return None, False
            chunk = self.sock.recv(65536)
            if not chunk:
                return None, True
            self.buffer += chunk
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line, True

    def send(self, data, replies=1, close=False):
        if self.dead:
            return [(None, self.dead)] * replies
        try:
            self.sock.sendall(data)
            if close:
                self.sock.shutdown(socket.SHUT_WR)
                self.closed = True
        except OSError:
            pass
        out = []
        for _ in range(replies):
            raw, ready = self._read_line()
            if raw is None:
                self.dead = "socket closed" if ready else f"no response in {TIMEOUT_S}s"
                out.append((None, self.dead))
                continue
            try:
                out.append((raw.decode("utf-8"), None))
            except UnicodeDecodeError:
                out.append((raw.decode("utf-8", "backslashreplace"), "reply is not UTF-8"))
        return out

    def close(self):
        rest = self.buffer
        try:
            if not self.closed:
                self.sock.shutdown(socket.SHUT_WR)
            self.sock.settimeout(0.3)
            while True:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                rest += chunk
        except OSError:
            pass
        self.sock.close()
        return "live", "live", rest


def launch_live(manifest, target):
    """Starts a socket platform’s optional `command` once and waits until its port accepts."""
    entry = manifest.platforms[target]
    proc = None
    if "command" in entry:
        proc = subprocess.Popen(manifest.command(target, manifest.default_fixture), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    name, port = entry["socket"].rsplit(":", 1)
    deadline = time.monotonic() + 20
    while True:
        try:
            socket.create_connection((name, int(port)), timeout=1).close()
            return proc
        except OSError:
            if time.monotonic() > deadline or (proc and proc.poll() is not None):
                if proc:
                    proc.kill()
                raise RuntimeError(f"socket {entry['socket']} for platform {target} did not accept connections")
            time.sleep(0.1)


def build_guard(manifest):
    """Builds the guard for this OS. Returns (library, None) or (None, why it is unavailable)."""
    src = manifest.guard_source
    if sys.platform == "darwin":
        lib = manifest.guard_library
        build = ["clang", "-dynamiclib", "-O2", "-Wall", "-Werror", str(src), "-o", str(lib)]
    elif sys.platform.startswith("linux"):
        lib = manifest.guard_library.with_suffix(".so")
        compiler = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not compiler and not (lib.exists() and lib.stat().st_mtime >= src.stat().st_mtime):
            return None, "linux: no C compiler to build the LD_PRELOAD guard, network isolation is NOT exercised"
        build = [compiler or "cc", "-shared", "-fPIC", "-O2", "-Wall", "-Werror", str(src), "-o", str(lib), "-ldl"]
    else:
        return None, f"{sys.platform}: no network guard for this OS, network isolation is NOT exercised"
    if not lib.exists() or lib.stat().st_mtime < src.stat().st_mtime:
        lib.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(build, capture_output=True, text=True)
        if result.returncode != 0:
            if sys.platform == "darwin":
                raise subprocess.CalledProcessError(result.returncode, build, result.stdout, result.stderr)
            return None, f"guard did not build: {result.stderr.strip()[:200]!r}, network isolation is NOT exercised"
    return lib, None


def guard_canary(guard):
    """Positive control: a non-SIP Python under the guard must be denied an Internet connect."""
    handle = tempfile.NamedTemporaryFile(prefix="reflex-canary-", delete=False)
    handle.close()
    env = dict(os.environ, REFLEX_NETWORK_LOG=handle.name)
    env[GUARD_ENV] = str(guard)
    code = ("import socket\ns=socket.socket()\ns.settimeout(2)\ntry:\n s.connect(('192.0.2.1',443));print('CONNECTED')\n"
            "except OSError as e:\n print('ERR',e.errno)")
    out = subprocess.run([os.path.realpath(sys.executable), "-c", code], env=env, capture_output=True, text=True, timeout=10)
    audit = Path(handle.name).read_text()
    Path(handle.name).unlink()
    ok = "READY" in audit and "DENIED" in audit and "CONNECTED" not in out.stdout
    return ok, audit.strip().replace("\n", " | "), out.stdout.strip()


def matcher_self_test(manifest):
    """The runner’s matcher must agree with the kit’s on the shared F-13 cases."""
    data = parse(manifest.conformance.read_text(encoding="utf-8"))
    cases = data["matcher"]
    bad = [c["id"] for c in cases if (mismatch(c["actual"], c["expected"]) is None) != c["match"]]
    return len(cases), bad


def run_journey(manifest, target, journey, guard, strict):
    live = "socket" in manifest.platforms[target]
    host = SocketConn(manifest.platforms[target]["socket"]) if live else Host(manifest, target, journey["fixture"], guard)
    records = []
    every = journey.get("everyResponse", manifest.every)
    previous = None
    stopped = None
    steps = list(journey["steps"])
    if journey.get("handshake", True):
        steps.insert(0, {"send": {"op": "hello", "protocol": manifest.protocol},
                         "expect": {"ok": True, "protocol": manifest.protocol, "sample": manifest.sample}, "hello": True})
    try:
        index = 0 if journey.get("handshake", True) else 1
        for step in steps:
            if "before" in step:
                record = {"step": f"{index}.before", "action": "before " + label(step), "wire": LS_WIRE, "raw": None,
                          "dead": None, "resp": None, "parity": step.get("parity"), "problems": [],
                          "xfail": (step.get("xfail") or {}).get(target)}
                try:
                    within, every_ms = poll_settings(step, "before_within_ms")
                except ValueError as error:
                    record["problems"].append(f"journey error: {error}")
                    records.append(record)
                    stopped = f"journey stopped at step {index}: bad precondition"
                    break
                line, dead, response, problem, polls, waited = poll(host, step["before"], every, within, every_ms)
                record.update(raw=line, dead=dead, resp=response, polls=polls)
                records.append(record)
                if problem:
                    record["problems"].append(f"precondition not met after {polls} ls poll(s) in {waited} ms: {problem}; "
                                              f"step not sent; last state={brief(response) if response else dead}")
                    stopped = f"journey stopped at step {index}: precondition not met"
                    break
                previous = response
            if "eventually" in step:
                record = {"step": index, "action": "eventually", "wire": LS_WIRE, "raw": None, "dead": None, "resp": None,
                          "parity": step.get("parity"), "problems": [], "xfail": (step.get("xfail") or {}).get(target)}
                try:
                    clash = sorted(k for k in ("do", "op", "ls", "send", "raw", "bytes", "expect") if k in step)
                    if clash:
                        raise ValueError(f"an eventually step only polls ls; move {','.join(clash)} to its own step")
                    within, every_ms = poll_settings(step, "within_ms")
                except ValueError as error:
                    record["problems"].append(f"journey error: {error}")
                    records.append(record)
                    index += 1
                    continue
                line, dead, response, problem, polls, waited = poll(host, step["eventually"], every, within, every_ms)
                record.update(raw=line, dead=dead, resp=response, polls=polls)
                if problem:
                    record["problems"].append(f"eventually not met within {within} ms after {polls} ls poll(s), action not re-sent: "
                                              f"{problem}; last state={brief(response) if response else dead}")
                if response is not None:
                    previous = response
                records.append(record)
                index += 1
                continue
            wire = wire_for(step)
            wanted = expectations(step)
            replies = host.send(payload_for(step), len(wanted), step.get("close", False))
            if not wanted:
                record = {"step": index, "action": label(step), "wire": wire, "raw": None, "dead": None, "resp": None,
                          "parity": step.get("parity"), "problems": [], "xfail": (step.get("xfail") or {}).get(target),
                          "none": True}
                records.append(record)
                index += 1
                continue
            for reply, ((line, dead), expected) in enumerate(zip(replies, wanted)):
                record = {"step": index if len(wanted) == 1 else f"{index}.{reply + 1}", "action": label(step), "wire": wire,
                          "raw": line, "dead": dead, "resp": None, "parity": step.get("parity"), "problems": [],
                          "xfail": (step.get("xfail") or {}).get(target)}
                if line is not None:
                    try:
                        record["resp"] = parse(line)
                    except DuplicateKey as error:
                        record["problems"].append(f"response has duplicate key {error}")
                    except ValueError as error:
                        record["problems"].append(f"response is not JSON: {error}")
                if dead:
                    record["problems"].append(f"actual={dead}")
                response = record["resp"]
                if isinstance(response, dict):
                    problem = mismatch(response, expected)
                    if problem:
                        record["problems"].append(f"{problem} response={brief(response)}")
                    if every:
                        problem = mismatch(response, every)
                        if problem:
                            record["problems"].append(f"everyResponse {problem}")
                    if step.get("unchanged"):
                        before = {k: v for k, v in (previous or {}).items() if k not in IGNORED_FOR_UNCHANGED}
                        after = {k: v for k, v in response.items() if k not in IGNORED_FOR_UNCHANGED}
                        if previous is None:
                            record["problems"].append("journey error: unchanged needs a previous response")
                        elif not same(before, after):
                            record["problems"].append("expected=unchanged " + "; ".join(diff_paths(before, after, ("before", "after"))))
                    previous = response
                records.append(record)
            index += 1
    finally:
        code, network, rest = host.close()
    end = [stopped] if stopped else []
    if rest:
        lines = rest.split(b"\n")
        lines = lines[:-1] if lines[-1] == b"" else lines
        end.append(f"unexpected output after the last expected reply: {len(lines)} line(s), first={lines[0][:120]!r}")
    if live:
        if journey.get("exit", 0) != 0 or journey.get("network", "clean") != "clean":
            end.append("journey error: a socket platform cannot check exit or network")
        return records, code, network, end
    want_exit = journey.get("exit", 0)
    if code != want_exit:
        end.append(f"expected exit={want_exit} actual exit={code}")
    want_network = journey.get("network", "clean") if guard else "unguarded"
    if network != want_network:
        end.append(f"expected network={want_network} actual network={network}")
    return records, code, network, end


def classify(records, end, journey, target, strict):
    """Assign PASS, FAIL, XFAIL or XPASS to each step and to the journey end checks."""
    journey_xfail = (journey.get("xfail") or {}).get(target)
    for record in records:
        tag = None if strict else (record["xfail"] or journey_xfail)
        if record["problems"]:
            record["status"] = "XFAIL" if tag else "FAIL"
        else:
            record["status"] = "XPASS" if record["xfail"] and not strict else "PASS"
    end_status = "PASS"
    if end:
        end_status = "XFAIL" if journey_xfail and not strict else "FAIL"
    elif journey_xfail and not strict and not any(r["status"] == "XFAIL" for r in records):
        end_status = "XPASS"
    return end_status


def warm_p50(manifest, target, guard, path, samples):
    journey = load_journeys(manifest, [path])[0]
    host = Host(manifest, target, journey["fixture"], guard)
    try:
        [(line, dead)] = host.send((dumps({"op": "hello", "protocol": manifest.protocol}) + "\n").encode("utf-8"))
        if dead or parse(line).get("ok") is not True:
            raise AssertionError(f"warm handshake failed platform={target} actual={line or dead}")
        if any("eventually" in s or "before" in s for s in journey["steps"]):
            raise AssertionError(f"warm journey {path} must not poll: remove eventually and before steps")
        payloads = [(payload_for(s), expectations(s)) for s in journey["steps"]]

        def once():
            for step, (data, wanted) in zip(journey["steps"], payloads):
                for (line, dead), expected in zip(host.send(data, len(wanted)), wanted):
                    problem = dead or mismatch(parse(line), expected)
                    if problem:
                        raise AssertionError(f"warm journey failed platform={target} action={label(step)} {problem}")
        once()
        times = []
        for _ in range(samples):
            start = time.perf_counter_ns(); once(); times.append((time.perf_counter_ns() - start) / 1e6)
    finally:
        _, network, _ = host.close()
    return times, network, len(journey["steps"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manifest", help="sample manifest, such as samples/outbox/reflex.json")
    parser.add_argument("journeys", nargs="*", help="journey files (default: the manifest’s journeys)")
    parser.add_argument("--platform", default="both", help="a platform name, a comma list, or both/all")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timings", type=int, default=20, help="measured warm runs (0 skips)")
    parser.add_argument("--strict", action="store_true", help="ignore xfail annotations: every finding fails")
    parser.add_argument("--no-guard", action="store_true", help="run unguarded (network isolation NOT exercised)")
    parser.add_argument("--allow-unguarded", action="store_true",
                        help=f"exit 0 on PASS-UNGUARDED instead of {EXIT_UNGUARDED} (network isolation NOT exercised)")
    parser.add_argument("--evidence", help="directory for raw NDJSON transcripts")
    args = parser.parse_args()

    manifest = Manifest(args.manifest)
    names = list(manifest.platforms)
    targets = names if args.platform in ("both", "all") else args.platform.split(",")
    for target in targets:
        if target not in manifest.platforms:
            parser.error(f"unknown platform {target}; manifest has {','.join(names)}")
    paths = manifest.journey_paths(args.journeys)
    journeys = load_journeys(manifest, paths)
    out = lambda text: print(text, flush=True)
    out(f"HOST {host_platform.platform()} python={host_platform.python_version()} runner=reflex_runner protocol={manifest.protocol} "
        f"sample={manifest.sample} platforms={','.join(targets)} journeys={len(journeys)} files={len(paths)}")
    failures = 0
    live_targets = [t for t in targets if "socket" in manifest.platforms[t]]
    for target in targets:
        if target in live_targets and "command" not in manifest.platforms[target]:
            continue
        executable = manifest.command(target, manifest.default_fixture)[0]
        if not os.access(executable, os.X_OK):
            out(f"RESULT FAIL platform={target} host binary not found: {os.path.relpath(executable, manifest.root)}. "
                "Build it with the README commands first.")
            sys.exit(2)
    if manifest.conformance:
        count, bad = matcher_self_test(manifest)
        out(f"MATCHER {'PASS' if not bad else 'FAIL'} cases={count} source={os.path.relpath(manifest.conformance, manifest.root)}"
            + (f" failed={','.join(bad)}" if bad else ""))
        failures += len(bad)
    guard = None
    guard_label = "skipped-no-guard"
    if args.no_guard:
        out("GUARD SKIP --no-guard: network isolation NOT exercised")
    else:
        guard, why = build_guard(manifest)
        if guard:
            ok, audit, canary = guard_canary(guard)
            out(f"GUARD {'PASS' if ok else 'FAIL'} backend={GUARD_ENV} canary=python-connect-192.0.2.1 audit={audit!r} canary_out={canary!r}")
            if not ok:
                out("RESULT FAIL guard canary did not prove denial")
                sys.exit(2)
        else:
            guard_label = "skipped-unavailable"
            out(f"GUARD SKIP {why}")
    if guard:
        guard_label = "canary-pass"
    launched = []
    for target in live_targets:
        try:
            launched.append(launch_live(manifest, target))
        except RuntimeError as error:
            out(f"RESULT FAIL {error}")
            for proc in launched:
                if proc:
                    proc.kill()
            sys.exit(2)
        out(f"SOCKET platform={target} address={manifest.platforms[target]['socket']} live session: state carries across journeys, "
            "exit codes and network isolation are NOT checked")
    unchecked = sorted({j["id"] for j in journeys if j.get("network", "clean") != "clean"}) if not guard else []
    for journey_id in unchecked:
        out(f"NETWORK UNCHECKED journey={journey_id} expects network={next(j for j in journeys if j['id'] == journey_id)['network']} "
            "but the run is unguarded, so this expectation is not tested")
    xfails = 0
    announced = set()
    transcripts = {}
    cold = {t: [] for t in targets}
    for target in targets:
        for iteration in range(args.repeat):
            run = []
            started = time.perf_counter()
            for journey in journeys:
                began = time.perf_counter()
                records, code, network, end = run_journey(manifest, target, journey, guard, args.strict)
                cold[target].append((time.perf_counter() - began) * 1000)
                end_status = classify(records, end, journey, target, args.strict)
                run.append((journey, records, code, network))
                if iteration and target not in live_targets:
                    continue
                if target not in announced and records and records[0]["step"] == 0 and isinstance(records[0]["resp"], dict):
                    announced.add(target)
                    hello = records[0]["resp"]
                    out(f"HANDSHAKE platform={target} protocol={hello.get('protocol')} sample={hello.get('sample')} kit={hello.get('kit')}")
                for r in records:
                    detail = "; ".join(r["problems"])
                    if r["status"] == "FAIL":
                        failures += 1
                        out(f"FAIL platform={target} journey={journey['id']} step={r['step']} action={r['action']} send={r['wire']} {detail}")
                    elif r["status"] == "XFAIL":
                        xfails += 1
                        out(f"XFAIL platform={target} journey={journey['id']} step={r['step']} action={r['action']} finding={r['xfail'] or journey['xfail'][target]} {detail}")
                    elif r["status"] == "XPASS":
                        failures += 1
                        out(f"XPASS platform={target} journey={journey['id']} step={r['step']} action={r['action']} finding={r['xfail']} passes now: remove the xfail")
                if end_status == "FAIL":
                    failures += 1
                    out(f"FAIL platform={target} journey={journey['id']} end {'; '.join(end)}")
                elif end_status == "XFAIL":
                    xfails += 1
                    out(f"XFAIL platform={target} journey={journey['id']} end finding={journey['xfail'][target]} {'; '.join(end)}")
                elif end_status == "XPASS":
                    failures += 1
                    out(f"XPASS platform={target} journey={journey['id']} finding={journey['xfail'][target]} passes now: remove the xfail")
                bad = sum(r["status"] in ("FAIL", "XPASS") for r in records) + (end_status in ("FAIL", "XPASS"))
                out(f"JOURNEY {'PASS' if not bad else 'FAIL'} platform={target} journey={journey['id']} steps={len(records)} "
                    f"exit={code} network={network}")
            elapsed = time.perf_counter() - started
            if iteration == 0:
                transcripts[target] = run
                if args.evidence:
                    folder = Path(args.evidence); folder.mkdir(parents=True, exist_ok=True)
                    with open(folder / f"transcript-{manifest.sample}-{target}.ndjson", "w", encoding="utf-8") as handle:
                        for journey, records, code, network in run:
                            for r in records:
                                entry = {"journey": journey["id"], "step": r["step"], "sent": r["wire"], "received": r["raw"], "dead": r["dead"]}
                                if "polls" in r:
                                    entry["polls"] = r["polls"]
                                handle.write(dumps(entry) + "\n")
                            handle.write(dumps({"journey": journey["id"], "exit": code, "network": network}) + "\n")
            elif target not in live_targets:
                first = transcripts[target]
                drift = [j["id"] for (j, a, c1, n1), (_, b, c2, n2) in zip(first, run)
                         if c1 != c2 or n1 != n2 or [x["raw"] for x in a] != [y["raw"] for y in b]]
                if drift:
                    failures += 1
                    out(f"FAIL platform={target} repeat={iteration + 1} transcript differs from repeat 1 (non-deterministic): {', '.join(drift[:5])}")
            steps = sum(len(records) for _, records, _, _ in run)
            out(f"SUITE platform={target} repeat={iteration + 1}/{args.repeat} journeys={len(run)} steps={steps} wall_s={elapsed:.2f}")
    if len(targets) > 1:
        reference = targets[0]
        diffs = known = byte_diffs = compared = 0
        for other in targets[1:]:
            names = (reference, other)
            for (journey, a, c1, n1), (_, b, c2, n2) in zip(transcripts[reference], transcripts[other]):
                for x, y in zip(a, b):
                    compared += 1
                    left = x["resp"] if x["resp"] is not None else x["dead"]
                    right = y["resp"] if y["resp"] is not None else y["dead"]
                    if same(left, right):
                        if x["raw"] != y["raw"]:
                            # Both kits promise canonical bytes, so equal values with different bytes fail.
                            if x["parity"]:
                                known += 1
                                out(f"PARITY KNOWN journey={journey['id']} step={x['step']} action={x['action']} finding={x['parity']} bytes differ")
                            else:
                                byte_diffs += 1
                                left_b, right_b = x["raw"].encode("utf-8"), y["raw"].encode("utf-8")
                                at = next((i for i, (p, q) in enumerate(zip(left_b, right_b)) if p != q), min(len(left_b), len(right_b)))
                                window = slice(max(at - 24, 0), at + 40)
                                out(f"PARITY BYTES journey={journey['id']} step={x['step']} action={x['action']} first_diff_byte={at} "
                                    f"{reference}={left_b[window]!r} {other}={right_b[window]!r}")
                        continue
                    what = "; ".join(diff_paths(left, right, names)) if isinstance(left, dict) and isinstance(right, dict) \
                        else f"{reference}={left!r} {other}={right!r}"
                    if x["parity"]:
                        known += 1
                        out(f"PARITY KNOWN journey={journey['id']} step={x['step']} action={x['action']} finding={x['parity']} {what}")
                    else:
                        diffs += 1
                        out(f"PARITY DIFF journey={journey['id']} step={x['step']} action={x['action']} {what}")
                if len(a) != len(b) or c1 != c2 or n1 != n2:
                    diffs += 1
                    out(f"PARITY DIFF journey={journey['id']} steps {reference}={len(a)} {other}={len(b)} exit {c1}/{c2} network {n1}/{n2}")
        out(f"PARITY {'PASS' if not diffs and not byte_diffs else 'FAIL'} platforms={','.join(targets)} steps={compared} "
            f"unexpected_diffs={diffs} byte_diffs={byte_diffs} known_diffs={known} (raw reply bytes and full parsed JSON, strict types)")
        failures += diffs + byte_diffs
    if args.timings and manifest.warm:
        warm = str(manifest.root / manifest.warm)
        for target in targets:
            try:
                times, network, count = warm_p50(manifest, target, guard, warm, args.timings)
            except AssertionError as error:
                failures += 1
                out(f"FAIL {error}")
                continue
            if network not in ("clean", "unguarded"):
                failures += 1
            out(f"P50 platform={target} warm_ms={statistics.median(times):.3f} min={min(times):.3f} max={max(times):.3f} "
                f"n={len(times)} steps_per_journey={count} journey={manifest.warm} startup=excluded warmup=one-full-journey network={network}")
        for target in targets:
            out(f"COLD platform={target} per_journey_ms_p50={statistics.median(cold[target]):.1f} n={len(cold[target])} startup=included")
    for proc in launched:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    if live_targets:
        guard = None
        guard_label = "live-socket"
    mode = "strict" if args.strict else "xfail-tracked"
    # An unguarded run never reports a plain PASS: it proves behaviour, not network isolation.
    word = "FAIL" if failures else ("PASS" if guard else "PASS-UNGUARDED")
    out(f"RESULT {word} mode={mode} unexpected_failures={failures} xfail={xfails} "
        f"platforms={','.join(targets)} repeat={args.repeat} sample={manifest.sample} guard={guard_label}"
        + ("" if guard else f" network_isolation=NOT-exercised network_unchecked={len(unchecked)}"))
    if word == "PASS-UNGUARDED" and not args.allow_unguarded:
        out(f"NOTE exit {EXIT_UNGUARDED}: the run was not guarded. Pass --allow-unguarded to accept that and exit 0.")
        sys.exit(EXIT_UNGUARDED)
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
