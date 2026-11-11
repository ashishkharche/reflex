"""Unit tests for the runner’s host checks: a host that was never built, a crash cause, kit warnings and state that never changes."""
import json
import os
import subprocess
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


class FrozenState(unittest.TestCase):
    DO = '{"action":"Add","op":"do"}'
    LS = '{"op":"ls"}'
    MISS = "$.node.state.count expected=1 (integer) actual=0 (integer) response={}"

    @staticmethod
    def record(step, wire, count, problems=(), action="Add", polls=None):
        record = {"step": step, "wire": wire, "action": action, "problems": list(problems),
                  "resp": {"ok": True, "node": {"name": "List", "state": {"count": count}}}}
        if polls is not None:
            record["polls"] = polls
        return record

    def test_action_that_left_state_alone_warns(self):
        records = [self.record(0, self.LS, 0, action="ls"), self.record(1, self.DO, 0, [self.MISS])]
        self.assertEqual(rr.frozen_state(records), (1, "action Add"))

    def test_polls_that_never_saw_a_change_warn(self):
        miss = "eventually not met within 2000 ms after 85 ls poll(s), action not re-sent: $.node.state.objects expected=2 items actual=0 items"
        records = [self.record(0, self.LS, 0, action="hello"), self.record(1, self.LS, 0, [miss], "eventually", 85)]
        self.assertEqual(rr.frozen_state(records), (1, "85 ls polls"))

    def test_state_that_moved_does_not_warn(self):
        records = [self.record(0, self.LS, 0, action="ls"),
                   self.record(1, self.DO, 1, ["$.node.state.count expected=2 (integer) actual=1 (integer)"])]
        self.assertIsNone(rr.frozen_state(records))

    def test_passing_steps_and_other_failures_do_not_warn(self):
        self.assertIsNone(rr.frozen_state([self.record(0, self.LS, 5, action="ls"), self.record(1, self.DO, 5)]))
        self.assertIsNone(rr.frozen_state([self.record(0, self.LS, 0, action="ls"), self.record(1, self.DO, 0, ["$.error.code expected=x"])]))
        self.assertIsNone(rr.frozen_state([self.record(0, self.LS, 0, action="ls"), self.record(1, self.LS, 0, [self.MISS], "ls")]))
        self.assertIsNone(rr.frozen_state([self.record(0, self.DO, 0, [self.MISS])]))

    def test_runner_prints_the_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "host.py").write_text(
                "import json, sys\n"
                "for line in sys.stdin:\n"
                "    op = json.loads(line).get('op')\n"
                "    reply = {'ok': True, 'node': {'name': 'List', 'state': {'count': 0}}}\n"
                "    if op == 'hello':\n"
                "        reply.update(protocol=1, sample='frozen')\n"
                "    print(json.dumps(reply), flush=True)\n")
            (root / "j.json").write_text(json.dumps({"name": "add", "steps": [
                {"ls": True, "expect": {"node": {"state": {"count": 0}}}},
                {"do": "Add", "expect": {"node": {"state": {"count": 1}}}}]}))
            (root / "reflex.json").write_text(json.dumps({
                "sample": "frozen", "protocol": 1, "root": ".", "defaultFixture": "default",
                "platforms": {"py": {"command": [sys.executable, "{root}/host.py"]}}, "journeys": ["j.json"]}))
            run = subprocess.run([sys.executable, str(Path(rr.__file__)), str(root / "reflex.json"), "--no-guard", "--allow-unguarded"],
                                 capture_output=True, text=True, timeout=60)
            self.assertIn("WARN platform=py journey=j.json#add step=2 node.state never changed over action Add", run.stdout)
            self.assertIn("no Main dispatcher", run.stdout)


if __name__ == "__main__":
    unittest.main()
