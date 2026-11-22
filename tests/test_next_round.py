import json
import os
import subprocess
import sys

from checkflow_case import CheckflowCase, FIXTURES


class NextRoundTests(CheckflowCase):
    def test_round_two_rechecks_cancel_and_preserves_decisions(self):
        content = self.finished_answer()
        for change in content["changes"]:
            change["decision"] = "keep"
            change["done"] = True
        self.write_current(content)
        first = self.current.read_bytes()

        patch = subprocess.run(
            ["git", "apply", str(FIXTURES / "round2.patch")],
            cwd=self.project,
            env={**os.environ, "GIT_CEILING_DIRECTORIES": str(self.scratch)},
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        self.assertEqual(patch.returncode, 0, patch.stdout + patch.stderr)
        self.success("next-round")
        archive = self.output / "check.round-1.json"
        self.assertEqual(archive.read_bytes(), first)
        second = self.read_current()
        self.assertEqual(second["project"]["round"], 2)
        self.assertEqual(second["changes"], content["changes"])
        self.assertEqual(second["checks"], content["checks"])
        previous = {row["id"]: row for row in content["points"]}
        current = {row["id"]: row for row in second["points"]}
        self.assertEqual(current, previous)
        run = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover"],
            cwd=self.project,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("Ran 3 tests", run.stderr)

        current["M4"].update(
            mark="covered",
            proof="Fixture cancellation test passed, including the cutoff.",
            round=2,
        )
        self.write_current(second)
        self.success("report")
        report = self.report.read_text(encoding="utf-8")
        self.assertRegex(report, r"(?i)round[^\n]*\b2\b")
        self.assertEqual(current["M1"]["round"], 1)
        self.assertEqual(current["M4"]["round"], 2)
        self.assertEqual(archive.read_bytes(), first)

    def test_new_changed_and_removed_points_roll_forward(self):
        content = self.finished_answer()
        previous = {row["id"]: row for row in content["points"]}
        changed = previous["M5"]["text"].replace("in one list", "in one screen", 1)
        self.assertNotEqual(changed, previous["M5"]["text"])
        added = "- **M6.** The customer can see the shop address.\n  - Check: open the address."
        document = self.prd.read_text(encoding="utf-8")
        document = document.replace(previous["M5"]["text"], changed, 1)
        document = document.replace(previous["M2"]["text"], added, 1)
        self.prd.write_text(document, encoding="utf-8")
        self.success("next-round")
        current = {row["id"]: row for row in self.read_current()["points"]}
        self.assertEqual(current["M1"], previous["M1"])
        self.assertNotIn("M2", current)
        self.assertEqual(current["M6"]["text"], added)
        self.assertEqual(current["M5"]["text"], changed)
        self.assertEqual(current["W1"], previous["W1"])
        self.assertEqual(current["W1"]["gap"], "untried")
        for name in ("M6", "M5"):
            self.assertEqual(
                (current[name]["mark"], current[name]["gap"], current[name]["proof"],
                 current[name]["round"]),
                ("", "", "", 2),
            )

    def test_removed_point_unlinks_change_and_preserves_owner_decision(self):
        content = self.finished_answer()
        change = next(row for row in content["changes"] if row.get("point") == "M3")
        change.update(decision="keep", done=True)
        self.write_current(content)
        previous_bytes = self.current.read_bytes()

        point = next(row for row in content["points"] if row["id"] == "M3")
        prd = self.prd.read_text(encoding="utf-8")
        self.prd.write_text(prd.replace(point["text"] + "\n", "", 1), encoding="utf-8")
        self.success("next-round")
        archive = self.output / "check.round-1.json"
        self.assertEqual(archive.read_bytes(), previous_bytes)
        archived = json.loads(archive.read_bytes())
        self.assertEqual(archived["changes"], content["changes"])
        updated = self.read_current()
        self.assertEqual(
            updated["changes"],
            [dict(row, point="") if row["id"] == change["id"] else row
             for row in content["changes"]],
        )
        self.assertNotIn("M3", {row["id"] for row in updated["points"]})
        self.success("check")

    def test_secret_in_approved_prd_refuses_next_round_without_leaking(self):
        self.finished_answer()
        value, line = self.insert_known_secret()
        message = self.refusal("next-round", "docs/prd.md", f"line {line}", "replace", "approv", "again")
        self.assertNotIn(value, message)
        self.assertFalse((self.output / "check.round-1.json").exists())
        self.assertNotIn(value.encode(), self.current.read_bytes())

    def test_reused_ordinal_does_not_take_an_old_change_link(self):
        content = self.finished_answer()
        first, next_point = [row for row in content["points"] if row["id"].startswith("W")]
        extra = next(row for row in content["changes"] if row["kind"] == "extra")
        extra.update(point=first["id"], decision="keep", done=True)
        self.write_current(content)

        prd = self.prd.read_text(encoding="utf-8")
        self.prd.write_text(prd.replace(first["text"] + "\n", "", 1), encoding="utf-8")
        self.success("next-round")
        updated = self.read_current()
        shifted = next(row for row in updated["points"] if row["id"] == first["id"])
        self.assertEqual(shifted, dict(next_point, id=first["id"]))
        revised_extra = next(row for row in updated["changes"] if row["id"] == extra["id"])
        self.assertEqual(revised_extra, dict(extra, point=""))
        self.success("check")
