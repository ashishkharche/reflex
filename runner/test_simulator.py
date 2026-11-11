"""Unit tests for iOS simulator hosts: spotting a simulator binary, the child environment, picking a device
and the build helper’s iOS-only check. No simulator is started."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import simulator as sim  # noqa: E402
import swift_host  # noqa: E402


def macho(platform_id):
    """A minimal 64-bit Mach-O header with one LC_BUILD_VERSION command."""
    command = struct.pack("<IIIIII", sim.LC_BUILD_VERSION, 24, platform_id, 0x110000, 0x1A0000, 0)
    header = struct.pack("<IiiIIIII", sim.MH_MAGIC_64, 0x0100000C, 0, 2, 1, len(command), 0, 0)
    return header + command


class Binaries(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def write(self, name, data):
        path = self.root / name
        path.write_bytes(data)
        return str(path)

    def test_thin_binaries(self):
        self.assertEqual(sim.macho_platform(self.write("sim", macho(7))), sim.IOS_SIMULATOR)
        self.assertEqual(sim.macho_platform(self.write("mac", macho(1))), 1)

    def test_universal_binary_reports_its_slice(self):
        slice_data = macho(7)
        fat = struct.pack(">II", sim.FAT_MAGIC, 1) + struct.pack(">iiIII", 0x0100000C, 0, 4096, len(slice_data), 12)
        data = fat.ljust(4096, b"\0") + slice_data
        self.assertEqual(sim.macho_platform(self.write("fat", data)), sim.IOS_SIMULATOR)

    def test_scripts_and_missing_files_are_not_simulator_hosts(self):
        self.assertIsNone(sim.macho_platform(self.write("host.py", b"print(1)\n")))
        self.assertIsNone(sim.macho_platform(str(self.root / "gone")))

    def test_manifest_choice_wins(self):
        host = self.write("sim", macho(7))
        mac = self.write("mac", macho(1))
        self.assertTrue(sim.wants_simulator({}, host))
        self.assertFalse(sim.wants_simulator({}, mac))
        self.assertFalse(sim.wants_simulator({"simulator": False}, host))
        self.assertTrue(sim.wants_simulator({"simulator": {"device": "iPhone 16"}}, mac))


class Environment(unittest.TestCase):
    def test_only_prefixed_variables_reach_the_device(self):
        env = sim.child_env({"PATH": "/bin", "SIMCTL_CHILD_OLD": "x"}, {"HOME": "/tmp/h", "REFLEX_NETWORK_LOG": "/tmp/n"})
        self.assertEqual(env["PATH"], "/bin")
        self.assertNotIn("SIMCTL_CHILD_OLD", env)
        self.assertEqual(env["SIMCTL_CHILD_HOME"], "/tmp/h")
        self.assertEqual(env["SIMCTL_CHILD_REFLEX_NETWORK_LOG"], "/tmp/n")

    def test_guard_source_has_a_simulator_storage_check(self):
        source = (Path(__file__).resolve().parent.parent / "scripts/network_guard.c").read_text(encoding="utf-8")
        self.assertIn("TARGET_OS_SIMULATOR", source)
        self.assertIn("STORAGE simulator-home", source)


class Devices(unittest.TestCase):
    OPTIONS = {"runtimes": [
        {"platform": "iOS", "isAvailable": True, "version": "18.3", "identifier": "rt18", "name": "iOS 18.3",
         "supportedDeviceTypes": [{"name": "iPhone 16", "identifier": "d16"}]},
        {"platform": "iOS", "isAvailable": True, "version": "26.5", "identifier": "rt26", "name": "iOS 26.5",
         "supportedDeviceTypes": [{"name": "iPad Air", "identifier": "pad"}, {"name": "iPhone 17", "identifier": "d17"}]},
        {"platform": "watchOS", "isAvailable": True, "version": "99.0", "identifier": "w", "name": "watchOS 99"},
        {"platform": "iOS", "isAvailable": False, "version": "27.0", "identifier": "rt27", "name": "iOS 27.0"}]}

    def test_newest_available_ios_and_first_iphone(self):
        self.assertEqual(sim.pick(self.OPTIONS), ("rt26", "d17", "26.5", "iPhone 17"))

    def test_requested_runtime_and_device(self):
        self.assertEqual(sim.pick(self.OPTIONS, "iPhone 16", "18.3")[:2], ("rt18", "d16"))

    def test_missing_runtime_or_device_says_so(self):
        with self.assertRaisesRegex(RuntimeError, "no available iOS simulator runtime"):
            sim.pick({"runtimes": []})
        with self.assertRaisesRegex(RuntimeError, "no device type iPhone 99"):
            sim.pick(self.OPTIONS, "iPhone 99")


class Leftovers(unittest.TestCase):
    def test_only_devices_of_dead_runs_are_stale(self):
        devices = {"rt26": [{"name": "reflex-host-111", "udid": "A"}, {"name": "reflex-host-222", "udid": "B"},
                            {"name": "iPhone 17 Pro", "udid": "C"}, {"name": "reflex-host-x", "udid": "D"}]}
        self.assertEqual(sim.stale(devices, lambda pid: pid == 222), ["A"])

    def test_this_process_is_running(self):
        self.assertTrue(sim.running(sim.os.getpid()))


class IOSOnly(unittest.TestCase):
    def test_platform_and_framework_errors_mean_ios_only(self):
        for line in ["error: the library 'Timeline' requires macos 10.13, but depends on the product 'Bodega' which requires macos 11.0",
                     "main.swift:1:8: error: no such module 'UIKit'",
                     "x.swift:3:5: error: cannot find type 'UIColor' in scope",
                     "x.swift:9:1: error: 'ActivityAttributes' is unavailable in macOS"]:
            self.assertIsNotNone(swift_host.ios_only_reason("Building\n" + line), line)

    def test_code_errors_do_not_switch_to_the_simulator(self):
        self.assertIsNone(swift_host.ios_only_reason("x.swift:1:1: error: cannot find 'count' in scope"))
        self.assertIsNone(swift_host.ios_only_reason("Build complete!"))


if __name__ == "__main__":
    unittest.main()
