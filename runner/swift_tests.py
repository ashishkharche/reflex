#!/usr/bin/env python3
"""Run existing Swift package unit tests without persisting account preferences."""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import reflex_runner as rr


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("package", help="Swift package directory inside the current app repo")
    args = p.parse_args()
    if sys.platform != "darwin":
        p.error("this preferences boundary requires macOS")
    package = Path(args.package).resolve()
    if not package.is_relative_to(Path.cwd().resolve()) or not (package / "Package.swift").is_file():
        p.error("package must be inside the current app repo and contain Package.swift")
    root = Path(__file__).resolve().parent.parent
    manifest = rr.Manifest(root / "tests/inventory/reflex.json")
    guard, why = rr.build_guard(manifest)
    if not guard:
        p.error("BLOCKED " + why)
    ok, audit, _ = rr.guard_canary(guard)
    if not ok:
        p.error("BLOCKED storage/network guard canary failed: " + audit)
    # Compile without executing tests. SwiftPM keeps its own manifest sandbox.
    swift = subprocess.check_output(["/usr/bin/xcrun", "--find", "swift"], text=True).strip()
    built = subprocess.run([swift, "build", "--package-path", str(package), "--build-tests"])
    if built.returncode:
        return built.returncode
    bin_path = Path(subprocess.check_output([swift, "build", "--package-path", str(package),
                                            "--show-bin-path"], text=True).strip())
    bundles = sorted(bin_path.glob("*.xctest"))
    if not bundles or not bin_path.resolve().is_relative_to(package / ".build"):
        p.error("BLOCKED no repo-local XCTest bundle; this helper supports XCTest suites")
    xctest = subprocess.check_output(["/usr/bin/xcrun", "--find", "xctest"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="reflex-swift-tests-") as home:
        log = Path(home) / "network.log"
        log.touch()
        env = rr.isolated_env(home)
        env.update({rr.GUARD_ENV: str(guard), "REFLEX_NETWORK_LOG": str(log)})
        print("SWIFT TESTS storage=seatbelt network=NOT-proved", flush=True)
        for bundle in bundles:
            command_env = dict(env)
            command = rr.guarded_command([xctest, str(bundle)], guard, command_env)
            done = subprocess.run(command, env=command_env)
            if "STORAGE launcher" not in log.read_text():
                p.error("BLOCKED native tests did not enter the preferences sandbox")
            if done.returncode:
                return done.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
