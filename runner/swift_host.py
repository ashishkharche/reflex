#!/usr/bin/env python3
"""Builds a Swift host. Tries the Mac first. When that fails because a package is iOS only, builds for
the iOS simulator instead. Either way the host ends up at <package>/.build/reflex/<product>, so a
manifest names one path and the runner picks the Mac or a simulator from the binary.

Usage: python3 runner/swift_host.py <package> <product> [--simulator]
Prints BUILT <path> platform=macos|ios-simulator, or FAIL with the first error. Standard library only."""
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

# Lines that mean "this code needs iOS", not "this code is wrong".
IOS_ONLY = [
    r"requires macos [\d.]+, but depends on the product",
    r"no such module '(UIKit|SwiftUI.*|ActivityKit|WidgetKit|AppIntents)'" ,
    r"is unavailable in macOS",
    r"is only available in iOS",
    r"cannot find type 'UI[A-Z]\w*' in scope",
]


def ios_only_reason(output):
    """The first build output line that says the package is iOS only, or None."""
    for line in output.splitlines():
        if any(re.search(pattern, line) for pattern in IOS_ONLY):
            return line.strip()[:240]
    return None


def first_error(output):
    lines = [line.strip() for line in output.splitlines() if "error:" in line]
    # A compiler error in a source file says more than the driver line that follows it, such as emit-module failed.
    lines.sort(key=lambda line: not re.search(r"\.swift:\d+:\d+: error:", line))
    return lines[0][:240] if lines else output.strip()[-240:]


def ios_version(package):
    """The iOS version the package declares, for the simulator triple. 17.0 when it declares none."""
    done = subprocess.run(["swift", "package", "--package-path", str(package), "dump-package"],
                          capture_output=True, text=True)
    try:
        platforms = json.loads(done.stdout).get("platforms") or []
    except json.JSONDecodeError:
        platforms = []
    version = next((p.get("version") for p in platforms if p.get("platformName") == "ios"), None) or "17.0"
    return version if "." in version else version + ".0"


def build(package, product, simulator=False):
    """Returns (path, platform name, reason) or raises RuntimeError with the first error."""
    package = Path(package).resolve()
    reason = "--simulator" if simulator else None
    if not simulator:
        mac = subprocess.run(["swift", "build", "--package-path", str(package), "--product", product],
                             capture_output=True, text=True)
        if mac.returncode == 0:
            built = package / ".build/debug" / product
            return link(package, product, built), "macos", None
        reason = ios_only_reason(mac.stdout + mac.stderr)
        if not reason:
            raise RuntimeError(first_error(mac.stdout + mac.stderr))
    sdk = subprocess.run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"], capture_output=True, text=True)
    if sdk.returncode:
        raise RuntimeError("no iOS simulator SDK: install Xcode")
    arch = "arm64" if platform.machine() == "arm64" else "x86_64"
    scratch = package / ".build/ios-sim"
    sim = subprocess.run(["swift", "build", "--package-path", str(package), "--product", product,
                          "--scratch-path", str(scratch), "--triple", f"{arch}-apple-ios{ios_version(package)}-simulator",
                          "--sdk", sdk.stdout.strip()], capture_output=True, text=True)
    if sim.returncode:
        raise RuntimeError(first_error(sim.stdout + sim.stderr))
    return link(package, product, scratch / "debug" / product), "ios-simulator", reason


def link(package, product, built):
    """A stable path for the manifest: <package>/.build/reflex/<product>."""
    stable = package / ".build/reflex" / product
    stable.parent.mkdir(parents=True, exist_ok=True)
    if stable.is_symlink() or stable.exists():
        stable.unlink()
    stable.symlink_to(os.path.relpath(built, stable.parent))
    return stable


def main(argv):
    args = [a for a in argv if a != "--simulator"]
    if len(args) != 2:
        print(__doc__.split("\n\n")[1])
        return 2
    try:
        path, name, reason = build(args[0], args[1], "--simulator" in argv)
    except RuntimeError as error:
        print(f"FAIL {error}")
        return 1
    note = f" because the Mac build said: {reason}" if reason and reason != "--simulator" else ""
    print(f"BUILT {os.path.relpath(path)} platform={name}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
