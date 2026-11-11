"""iOS simulator hosts. A Swift host built for the simulator runs headless through `simctl spawn`: no app,
no UI and no Xcode project. The runner uses one throwaway device per run and deletes it at the end.
Standard library only."""
import atexit
import json
import os
import platform
import shutil
import struct
import subprocess
import time
from pathlib import Path

IOS_SIMULATOR = 7  # LC_BUILD_VERSION platform for the iOS simulator
LC_BUILD_VERSION = 0x32
MH_MAGIC_64 = 0xFEEDFACF
FAT_MAGIC = 0xCAFEBABE
CANARY_C = r"""#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <sys/socket.h>
int main(void) {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    fcntl(s, F_SETFL, O_NONBLOCK);
    struct sockaddr_in a = {0};
    a.sin_family = AF_INET;
    a.sin_port = htons(443);
    inet_pton(AF_INET, "192.0.2.1", &a.sin_addr);
    if (connect(s, (struct sockaddr *)&a, sizeof a) == 0) puts("CONNECTED"); else printf("ERR %d\n", errno);
    return 0;
}
"""


def _thin_platform(data):
    if len(data) < 32 or struct.unpack("<I", data[:4])[0] != MH_MAGIC_64:
        return None
    count = struct.unpack("<I", data[16:20])[0]
    offset = 32
    for _ in range(count):
        if offset + 12 > len(data):
            return None
        command, size = struct.unpack("<II", data[offset:offset + 8])
        if command == LC_BUILD_VERSION:
            return struct.unpack("<I", data[offset + 8:offset + 12])[0]
        if size == 0:
            return None
        offset += size
    return None


def macho_platform(path):
    """The LC_BUILD_VERSION platform of a Mach-O file, or None. A universal file reports its first known slice."""
    try:
        with open(path, "rb") as handle:
            head = handle.read(65536)
            if len(head) >= 8 and struct.unpack(">I", head[:4])[0] == FAT_MAGIC:
                for index in range(struct.unpack(">I", head[4:8])[0]):
                    _, _, start, _, _ = struct.unpack(">iiIII", head[8 + index * 20:28 + index * 20])
                    handle.seek(start)
                    found = _thin_platform(handle.read(65536))
                    if found is not None:
                        return found
                return None
            return _thin_platform(head)
    except (OSError, struct.error):
        return None


def wants_simulator(entry, executable):
    """A platform runs on the simulator when its manifest entry says `"simulator"` or its host binary
    was built for the iOS simulator. `"simulator": false` keeps it on the Mac."""
    choice = entry.get("simulator")
    if choice is not None:
        return bool(choice)
    return macho_platform(executable) == IOS_SIMULATOR


def child_env(base, child):
    """simctl passes SIMCTL_CHILD_X to the simulator process as X. Nothing else from the Mac reaches it."""
    env = {k: v for k, v in base.items() if not k.startswith("SIMCTL_CHILD_")}
    env.update({"SIMCTL_CHILD_" + key: value for key, value in child.items()})
    return env


def _simctl(*args, check=True, timeout=300):
    return subprocess.run(["xcrun", "simctl", *args], capture_output=True, text=True, check=check, timeout=timeout)


def available():
    """None when simctl works, else why not."""
    if shutil.which("xcrun") is None:
        return "no xcrun: install Xcode to run iOS simulator hosts"
    try:
        _simctl("help", timeout=30)
    except (subprocess.SubprocessError, OSError):
        return "xcrun simctl does not run: install Xcode and run xcode-select -s"
    return None


def pick(options, device=None, runtime=None):
    """Chooses (runtime id, device type id) from `simctl list -j` output. Newest available iOS runtime,
    then the requested device name or the first iPhone it supports."""
    runtimes = [r for r in options.get("runtimes", []) if r.get("platform") == "iOS" and r.get("isAvailable")]
    if runtime:
        runtimes = [r for r in runtimes if runtime in (r.get("name"), r.get("version"), r.get("identifier"))]
    if not runtimes:
        raise RuntimeError(f"no available iOS simulator runtime{' named ' + runtime if runtime else ''}. "
                           "Install one in Xcode, Settings, Components")
    best = max(runtimes, key=lambda r: [int(p) for p in r.get("version", "0").split(".") if p.isdigit()])
    supported = best.get("supportedDeviceTypes") or options.get("devicetypes", [])
    names = [d for d in supported if (d.get("name") == device if device else d.get("name", "").startswith("iPhone"))]
    if not names:
        raise RuntimeError(f"iOS {best.get('version')} has no device type {device or 'iPhone'}")
    return best["identifier"], names[0]["identifier"], best.get("version"), names[0]["name"]


def stale(devices, alive):
    """Devices a killed run left behind: named reflex-host-<pid> where that pid no longer runs.
    `devices` is the `devices` object of `simctl list -j devices`."""
    out = []
    for group in devices.values():
        for device in group:
            name = device.get("name", "")
            pid = name[len("reflex-host-"):]
            if name.startswith("reflex-host-") and pid.isdigit() and not alive(int(pid)):
                out.append(device["udid"])
    return out


def running(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Simulator:
    """One throwaway device for a run. `delete` runs at exit even when the run stops early."""

    def __init__(self, device=None, runtime=None):
        self.device, self.runtime = device, runtime
        self.udid = None
        self.label = ""

    def start(self):
        options = json.loads(_simctl("list", "-j", "runtimes", "devicetypes", "devices").stdout)
        # atexit cannot run when a run is killed, so the next run deletes what that one left.
        for udid in stale(options.get("devices", {}), running):
            _simctl("shutdown", udid, check=False, timeout=120)
            _simctl("delete", udid, check=False, timeout=120)
        runtime, kind, version, name = pick(options, self.device, self.runtime)
        started = time.monotonic()
        self.udid = _simctl("create", f"reflex-host-{os.getpid()}", kind, runtime).stdout.strip()
        atexit.register(self.delete)
        _simctl("boot", self.udid, check=False)
        _simctl("bootstatus", self.udid, "-b", timeout=600)
        self.label = f"device={name.replace(' ', '-')} ios={version} boot_s={time.monotonic() - started:.1f}"
        return self

    def command(self, command):
        return ["xcrun", "simctl", "spawn", self.udid, *command]

    def delete(self):
        if not self.udid:
            return
        udid, self.udid = self.udid, None
        _simctl("shutdown", udid, check=False, timeout=120)
        _simctl("delete", udid, check=False, timeout=120)


def build_guard(source, library):
    """The network guard built for the simulator, next to the Mac one."""
    library = Path(library)
    library.parent.mkdir(parents=True, exist_ok=True)
    if not library.exists() or library.stat().st_mtime < Path(source).stat().st_mtime:
        arch = "arm64" if platform.machine() == "arm64" else "x86_64"
        subprocess.run(["xcrun", "--sdk", "iphonesimulator", "clang", "-target", f"{arch}-apple-ios15.0-simulator",
                        "-dynamiclib", "-O2", "-Wall", "-Werror", str(source), "-o", str(library)],
                       capture_output=True, text=True, check=True)
    return library


def canary(simulator, guard, home):
    """Positive control on the device: a simulator binary under the guard must be denied an Internet connect.
    Returns (ok, audit, output)."""
    home = Path(home)
    source, binary = home / "canary.c", Path(guard).parent / "sim-canary"
    source.write_text(CANARY_C)
    arch = "arm64" if platform.machine() == "arm64" else "x86_64"
    subprocess.run(["xcrun", "--sdk", "iphonesimulator", "clang", "-target", f"{arch}-apple-ios15.0-simulator",
                    str(source), "-o", str(binary)], capture_output=True, text=True, check=True)
    audit = home / "network.log"
    audit.touch()
    env = child_env(os.environ, {"HOME": str(home), "CFFIXED_USER_HOME": str(home), "TMPDIR": str(home) + "/",
                                 "DYLD_INSERT_LIBRARIES": str(guard), "REFLEX_NETWORK_LOG": str(audit)})
    out = subprocess.run(simulator.command([str(binary)]), env=env, capture_output=True, text=True, timeout=60)
    text = audit.read_text()
    ok = all(word in text for word in ("STORAGE simulator-home", "READY", "DENIED")) and out.stdout.strip() == "ERR 1"
    return ok, text.strip().replace("\n", " | "), out.stdout.strip()
