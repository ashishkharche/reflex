#!/usr/bin/env python3
"""Prove guarded macOS defaults are process-local without writing the account’s preferences."""
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import reflex_runner as rr


def require_storage_guard(guard):
    ok, audit, _ = rr.guard_canary(guard)
    if not ok or "STORAGE seatbelt" not in audit or "STORAGE launcher" not in audit:
        raise RuntimeError("BLOCKED native storage guard was not proved: " + audit)


def domains():
    out = subprocess.run(["defaults", "domains"], capture_output=True, text=True, check=True)
    return set(s.strip() for s in out.stdout.replace("\n", ",").split(",") if s.strip())


def main():
    if sys.platform != "darwin":
        print("PREFERENCES SKIP macOS-only native regression")
        return
    root = Path(__file__).resolve().parent.parent
    manifest = rr.Manifest(root / "tests/inventory/reflex.json")
    guard, why = rr.build_guard(manifest)
    if not guard:
        raise RuntimeError("BLOCKED " + why)
    # This check fails against the old guard before any preferences probe runs.
    require_storage_guard(guard)
    before = domains()
    domain = "com.reflex.canary." + uuid.uuid4().hex
    out = root / ".build/preferences-canary"
    out.mkdir(parents=True, exist_ok=True)
    binary = out / ("reflex-defaults-" + uuid.uuid4().hex)
    subprocess.run(["swiftc", str(root / "runner/swift/DefaultsCanary.swift"), "-o", str(binary)], check=True)
    names = [domain, binary.name]
    user_preferences = Path.home() / "Library/Preferences"
    assert all(not (user_preferences / (n + ".plist")).exists() for n in names)
    assert not (set(names) & before)

    class Probe:
        guard_library = manifest.guard_library

        def command(self, target, fixture):
            return [str(binary), domain]

    results = []
    for _ in range(2):
        host = rr.Host(Probe(), "swift", None, guard)
        try:
            [(line, dead)] = host.send(b"")
            assert not dead, dead
            data = json.loads(line)
        finally:
            code, network, rest = host.close()
        assert code == 0 and network == "clean" and not rest, (code, network, rest)
        assert data == {"before": None, "after": 42, "standardBefore": None,
                        "standardAfter": 73, "synchronized": False}, data
        results.append(data)
    # A hardened binary drops DYLD, but still inherits the launcher's kernel policy.
    subprocess.run(["codesign", "--force", "--sign", "-", "--options", "runtime", str(binary)], check=True)
    hardened = rr.Host(Probe(), "swift", None, guard)
    [(line, dead)] = hardened.send(b"")
    code, hardened_network, rest = hardened.close()
    assert not dead and code == 0 and not rest, (dead, code, rest)
    assert json.loads(line) == results[0], line
    assert hardened_network in ("clean", "guard-not-loaded"), hardened_network
    # Missing, invalid or permissive profiles stop before Swift main.
    for profile in [None, "invalid profile", "(version 1)(allow default)"]:
        with tempfile.TemporaryDirectory(prefix="reflex-prefs-failure-") as home:
            log = Path(home) / "network.log"
            log.touch()
            env = rr.isolated_env(home)
            env.update({rr.GUARD_ENV: str(guard), "REFLEX_NETWORK_LOG": str(log)})
            if profile is None:
                env.pop("REFLEX_STORAGE_PROFILE", None)
            else:
                env["REFLEX_STORAGE_PROFILE"] = profile
            command = rr.guarded_command([str(binary), domain], guard, env)
            done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
            assert done.returncode == 78 and not done.stdout, (done.returncode, done.stdout)
            assert "BLOCKED preferences sandbox" in log.read_text()
    after = domains()
    for name in names:
        assert name not in after and not (user_preferences / (name + ".plist")).exists(), name
        read = subprocess.run(["defaults", "read", name], capture_output=True, text=True)
        assert read.returncode != 0, name
    evidence = {"named_suite": domain, "standard_domain": binary.name, "runs": results,
                "host_domains_absent": names, "domain_additions": sorted(after - before),
                "missing_profile_blocked": True, "invalid_profile_blocked": True,
                "permissive_profile_blocked": True, "hardened_network_status": hardened_network}
    (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    binary.unlink()
    print("PREFERENCES PASS named + standard set/get, fresh twice, host domains absent, fail-closed profiles")
    print(json.dumps(evidence, sort_keys=True))


if __name__ == "__main__":
    main()
