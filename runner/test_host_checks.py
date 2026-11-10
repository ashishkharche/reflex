"""Unit tests for the runner’s host checks: a host that was never built, a crash cause and kit warnings."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflex_runner as rr  # noqa: E402


class MissingInputs(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.root = Path(self.dir.name)
        (self.root / "lib").mkdir()
        (self.root / "lib" / "app.jar").write_text("")
        (self.root / "empty").mkdir()
        (self.root / "cp.txt").write_text("-cp\n.\n")
        (self.root / "host.js").write_text("")

    def tearDown(self):
        self.dir.cleanup()

    def path(self, name):
        return str(self.root / name)

    def test_built_hosts_pass(self):
        self.assertIsNone(rr.missing_inputs(["java", "-cp", self.path("lib/*"), "app.MainKt", "default"]))
        self.assertIsNone(rr.missing_inputs(["java", "@" + self.path("cp.txt"), "app.MainKt"]))
        self.assertIsNone(rr.missing_inputs(["node", self.path("host.js"), "default"]))
        self.assertIsNone(rr.missing_inputs([self.path("cli"), "default"]))

    def test_classpath_folder_without_jars(self):
        self.assertEqual(rr.missing_inputs(["java", "-cp", self.path("empty/*"), "app.MainKt"]), self.path("empty/*"))
        self.assertEqual(rr.missing_inputs(["java", "-cp", self.path("gone/*"), "app.MainKt"]), self.path("gone/*"))

    def test_classpath_list_reports_the_first_missing_entry(self):
        cp = os.pathsep.join([self.path("lib/app.jar"), self.path("classes")])
        self.assertEqual(rr.missing_inputs(["java", "-cp", cp, "app.MainKt"]), self.path("classes"))

    def test_argfile_jar_and_script(self):
        self.assertEqual(rr.missing_inputs(["java", "@" + self.path("none.txt"), "app.MainKt"]), self.path("none.txt"))
        self.assertEqual(rr.missing_inputs(["java", "-jar", self.path("none.jar")]), self.path("none.jar"))
        self.assertEqual(rr.missing_inputs(["node", self.path("none.js")]), self.path("none.js"))

    def test_fixture_names_and_main_classes_are_not_paths(self):
        self.assertIsNone(rr.missing_inputs(["java", "-cp", self.path("lib/*"), "app.MainKt", "empty.js"]))


class HostOutput(unittest.TestCase):
    TRACE = ('Picked up JAVA_TOOL_OPTIONS: -Dreflex=1\n'
             'Exception in thread "main" java.lang.NullPointerException: getString(...) must not be null\n'
             '\tat org.example.Calculator.equals(Calculator.kt:203)\n'
             '\tat reflexcli.MainKt.main(Main.kt)')

    def test_crash_keeps_the_cause_line(self):
        summary = rr.crash_summary(self.TRACE)
        self.assertTrue(summary.startswith('Exception in thread "main" java.lang.NullPointerException'))
        self.assertTrue(summary.endswith("at reflexcli.MainKt.main(Main.kt)"))

    def test_plain_stderr_is_a_tail(self):
        self.assertEqual(rr.crash_summary("x" * 300), "x" * 200)

    def test_jvm_option_note_is_not_host_output(self):
        self.assertEqual(rr.host_stderr("Picked up JAVA_TOOL_OPTIONS: -Dx\n\nreal line\n"), ["real line"])

    def test_kit_warning_prefix_matches_the_kotlin_kit(self):
        kit = Path(__file__).resolve().parent.parent / "kit/kotlin/src/main/kotlin/reflex/kit/MainDispatcher.kt"
        self.assertIn(f'"{rr.KIT_WARNING} Dispatchers.Main is missing', kit.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
