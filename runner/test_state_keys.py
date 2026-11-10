#!/usr/bin/env python3
"""Unit tests for the runner’s stateKeys map. Standard library only: python3 runner/test_state_keys.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reflex_runner as rr  # noqa: E402

PLATFORMS = {"swift": {}, "kotlin": {}}


def reply(state):
    return {"ok": True, "node": {"name": "Timer", "state": state, "actions": []}}


def shared(response, keys):
    """What the runner compares for one platform."""
    record = {"resp": response, "problems": []}
    rr.apply_keys(record, keys)
    return record


class StateKeysTest(unittest.TestCase):
    def test_mapped_rename_matches(self):
        keys = rr.state_keys({"kotlin": {"rename": {"started": "isRunning"}}}, PLATFORMS)
        ios = shared(reply({"isRunning": True}), keys.get("swift", ({}, [])))
        android = shared(reply({"started": True}), keys["kotlin"])
        self.assertTrue(rr.same(ios["compare"], android["compare"]))
        self.assertTrue(android["mapped"])
        self.assertFalse(ios["mapped"])
        self.assertIsNone(rr.mismatch(android["resp"], {"node": {"state": {"isRunning": True}}}))

    def test_mapped_value_mismatch_still_differs(self):
        keys = rr.state_keys({"kotlin": {"rename": {"started": "isRunning"}}}, PLATFORMS)
        ios = shared(reply({"isRunning": True}), ({}, []))
        android = shared(reply({"started": False}), keys["kotlin"])
        self.assertFalse(rr.same(ios["compare"], android["compare"]))
        self.assertEqual(rr.diff_paths(ios["compare"], android["compare"], ("swift", "kotlin")),
                         ["$.node.state.isRunning swift=true kotlin=false"])

    def test_strict_types_survive_a_rename(self):
        keys = rr.state_keys({"kotlin": {"rename": {"count": "total"}}}, PLATFORMS)
        android = shared(reply({"count": 1}), keys["kotlin"])
        self.assertFalse(rr.same(shared(reply({"total": True}), ({}, []))["compare"], android["compare"]))

    def test_one_platform_keys_are_skipped_and_reported(self):
        keys = rr.state_keys({"kotlin": {"only": ["moreCount", "session.expanded"]}}, PLATFORMS)
        ios = shared(reply({"title": "Run", "session": {"id": 1}}), ({}, []))
        android = shared(reply({"title": "Run", "moreCount": 3, "session": {"id": 1, "expanded": False}}), keys["kotlin"])
        self.assertTrue(rr.same(ios["compare"], android["compare"]))
        self.assertEqual(android["not_compared"], ["moreCount", "session.expanded"])
        self.assertEqual(android["resp"]["node"]["state"]["moreCount"], 3)

    def test_one_platform_key_on_both_platforms_is_still_compared(self):
        keys = rr.state_keys({"kotlin": {"only": ["moreCount"]}}, PLATFORMS)
        ios = shared(reply({"moreCount": 3}), ({}, []))
        android = shared(reply({"moreCount": 3}), keys["kotlin"])
        self.assertFalse(rr.same(ios["compare"], android["compare"]))

    def test_nested_paths_and_lists(self):
        keys = rr.state_keys({"kotlin": {"rename": {"session.started": "isRunning", "rows.done": "isDone"}}}, PLATFORMS)
        android = shared(reply({"session": {"started": True}, "rows": [{"done": True}, {"done": False}]}), keys["kotlin"])
        self.assertEqual(android["resp"]["node"]["state"],
                         {"session": {"isRunning": True}, "rows": [{"isDone": True}, {"isDone": False}]})

    def test_no_map_is_the_old_behaviour(self):
        self.assertEqual(rr.state_keys(None, PLATFORMS), {})
        original = reply({"isRunning": True})
        record = shared(original, ({}, []))
        self.assertIs(record["resp"], original)
        self.assertIs(record["compare"], original)
        self.assertFalse(record["mapped"])
        self.assertEqual(record["not_compared"], [])
        other = shared(reply({"started": True}), ({}, []))
        diff = rr.diff_paths(record["compare"], other["compare"], ("swift", "kotlin"))
        self.assertEqual(diff, ['$.node.state.isRunning swift=true kotlin="<absent>"',
                                '$.node.state.started swift="<absent>" kotlin=true'])

    def test_missing_key_hint(self):
        problem = rr.mismatch(reply({"started": True}), {"node": {"state": {"isRunning": True}}})
        self.assertIn("stateKeys", rr.absent_hint(problem))
        self.assertNotIn("stateKeys", rr.absent_hint("$.node.state.isRunning expected=true (boolean) actual=false (boolean)"))

    def test_rename_onto_an_existing_key_is_a_journey_error(self):
        keys = rr.state_keys({"kotlin": {"rename": {"started": "isRunning"}}}, PLATFORMS)
        record = shared(reply({"started": True, "isRunning": False}), keys["kotlin"])
        self.assertEqual(len(record["problems"]), 1)
        self.assertIn("journey error", record["problems"][0])

    def test_bad_maps_are_rejected(self):
        for spec in ([], {"android": {}}, {"kotlin": {"renames": {}}}, {"kotlin": {"rename": {"a": "b.c"}}},
                     {"kotlin": {"rename": {"a.": "b"}}}, {"kotlin": {"only": "a"}}):
            with self.assertRaises(ValueError, msg=spec):
                rr.state_keys(spec, PLATFORMS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
