#!/usr/bin/env python3
"""Compiles a Dart Reflex host to a kernel file that Flutter’s headless engine, flutter_tester, runs.

A Flutter ViewModel usually imports package:flutter (ChangeNotifier), which needs dart:ui, so plain
`dart run` can’t load it. flutter_tester has dart:ui and reads stdin, so the host runs with no refactor.

    python3 ../reflex/runner/flutter_kernel.py tool/reflex/main.dart build/reflex/host.dill

Run it from the Flutter app folder after `flutter pub get`. The manifest then runs:

    ["{flutter_tester}", "--non-interactive", "--disable-vm-service",
     "--dart-entrypoint-args={fixture}", "{root}/build/reflex/host.dill"]
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflex_runner as rr  # noqa: E402


def package_config(start):
    for folder in [start, *start.parents]:
        config = folder / ".dart_tool" / "package_config.json"
        if config.exists():
            return config
    return None


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip())
        return 2
    entry, out = Path(argv[0]).resolve(), Path(argv[1]).resolve()
    engine = rr.flutter_engine()
    if not engine:
        print("BLOCKED no flutter on PATH, or its engine folder is missing. Run flutter precache once.")
        return 2
    sdk = engine.parent.parent.parent.parent
    runtime = sdk / "cache" / "dart-sdk" / "bin" / "dartaotruntime"
    server = engine / "frontend_server_aot.dart.snapshot"
    patched = engine.parent / "common" / "flutter_patched_sdk"
    config = package_config(entry.parent)
    if not entry.exists():
        print(f"BLOCKED {entry} does not exist")
        return 2
    if not config:
        print(f"BLOCKED no .dart_tool/package_config.json above {entry}. Run flutter pub get first.")
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(runtime), str(server), "--sdk-root", f"{patched}/", "--target=flutter",
                             "--no-print-incremental-dependencies", "--packages", str(config),
                             "--output-dill", str(out), str(entry)], capture_output=True, text=True)
    errors = [line for line in result.stdout.splitlines() + result.stderr.splitlines() if "Error" in line or "error:" in line]
    if result.returncode != 0 or errors or not out.exists():
        print("FAIL kernel did not build")
        print("\n".join(errors or result.stdout.splitlines()[-20:]))
        return 1
    print(f"BUILT {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
