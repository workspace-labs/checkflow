import json

from checkflow_case import ASSET, FIXTURES, GROUP_COUNTS, CheckflowCase


class StartTests(CheckflowCase):
    def test_bakery_points_follow_approved_documents_verbatim(self):
        content = self.start_bakery()
        expected = json.loads(
            (FIXTURES / "corner-bakery.expected.json").read_text(encoding="utf-8")
        )
        expected_ids = ["M1", "M2", "M3", "M4", "M5", "N1", "W1", "W2",
                        "L1", "L2", "H1", "H2"]
        self.assertEqual([row["id"] for row in content["points"]], expected_ids)
        for current, answer in zip(content["points"], expected["points"]):
            with self.subTest(point=current["id"]):
                self.assertEqual(current["source"], answer["source"])
                self.assertEqual(current["text"], answer["text"])
                name, heading = current["source"].split(", ")
                document = (self.project / name).read_text(encoding="utf-8")
                section = document.split(f"## {heading}\n", 1)[1].split("\n## ", 1)[0]
                self.assertIn(current["text"], section)
                self.assertEqual(
                    (current["mark"], current["gap"], current["proof"], current["round"]),
                    ("", "", "", 1),
                )
        self.assertIn("  - Changed 2026-12-10:", content["points"][1]["text"])
        self.assertIn("adds 6 days.", content["points"][1]["text"])
        self.assertEqual(content["project"], {
            "name": "Corner Bakery",
            "client": "",
            "language": "",
            "round": 1,
            "bar": "basic",
            "not_approved": [],
            "checkers": 1,
        })
        self.assertEqual(content["changes"], [])
        self.assertEqual(content["dates"], [])
        self.assertEqual(content["problems"], [])

    def test_starts_every_basic_check_empty(self):
        content = self.start_bakery()
        groups = json.loads(ASSET.read_text(encoding="utf-8"))
        self.assertEqual(
            {group["group"]: len(group["checks"]) for group in groups},
            GROUP_COUNTS,
        )
        expected = [
            {
                "group": group["group"],
                "check": row["check"],
                "result": "",
                "reason": "",
                "bar": "basic",
                "round": 1,
            }
            for group in groups
            for row in group["checks"]
        ]
        self.assertEqual(content["checks"], expected)

    def test_prd_example_in_fence_is_ignored(self):
        content = self.start_bakery()
        self.assertRegex(
            self.prd.read_text(encoding="utf-8"), r"```[^\n]*\n[^\n]*M99"
        )
        self.assertNotIn("M99", {row["id"] for row in content["points"]})

    def test_prd_examples_in_indented_and_preformatted_blocks_are_ignored(self):
        self.copy_bakery()
        body = self.prd.read_text(encoding="utf-8")
        example = ("\n    M96. Indented example.\n\tM97. Tab-indented example.\n"
                   "\n<pre>\nM98. Preformatted example.\n</pre>\n")
        self.prd.write_text(body.replace("\n## What it will NOT do", example + "\n## What it will NOT do"),
                            encoding="utf-8")
        self.success("start")
        ids = {row["id"] for row in self.read_current()["points"]}
        self.assertTrue({"M96", "M97", "M98"}.isdisjoint(ids))

    def test_indent_inside_top_level_fence_does_not_close_it(self):
        self.copy_bakery()
        body = self.prd.read_text(encoding="utf-8")
        fence = chr(96) * 3
        example = f"\n{fence}markdown\n    {fence}\n- **M95.** Example.\n{fence}\n"
        self.prd.write_text(body.replace("\n- **M1.**", example + "\n- **M1.**", 1), encoding="utf-8")
        self.success("start")
        ids = {row["id"] for row in self.read_current()["points"]}
        self.assertIn("M1", ids)
        self.assertNotIn("M95", ids)

    def test_wrapped_approved_point_and_check_keep_their_continuations(self):
        self.copy_bakery()
        body = self.prd.read_text(encoding="utf-8")
        body = body.replace("today's bread and its price.", "today's bread\n  and its price.", 1)
        body = body.replace("and rye for AED 10.00.", "and rye\n    for AED 10.00.", 1)
        self.prd.write_text(body, encoding="utf-8")
        self.success("start")
        point = self.read_current()["points"][0]
        self.assertIn("today's bread\n  and its price.", point["text"])
        self.assertIn("and rye\n    for AED 10.00.", point["text"])

    def test_struck_through_point_is_ignored(self):
        self.copy_bakery()
        body = self.prd.read_text(encoding="utf-8")
        old = next(line for line in body.splitlines() if line.startswith("- **M1.**"))
        self.prd.write_text(body.replace(old, f"- ~~{old[2:]}~~", 1), encoding="utf-8")
        self.success("start")
        self.assertNotIn("M1", {row["id"] for row in self.read_current()["points"]})

    def test_missing_prd_refuses_without_writing(self):
        self.refusal("start", "docs/prd.md", "approved")

    def test_draft_prd_refuses_without_writing(self):
        self.copy_bakery()
        self.replace_stamp("> v1 · Draft")
        self.refusal("start", "docs/prd.md", "draft", "approved")

    def test_prd_without_stamp_refuses_without_writing(self):
        self.copy_bakery()
        self.replace_stamp("")
        self.refusal("start", "docs/prd.md", "stamp", "approved")

    def test_arabic_approved_stamp_is_accepted(self):
        self.copy_bakery()
        self.replace_stamp("> الإصدار 2 · معتمد 2026-10-08 من مدير المخبز")
        self.success("start")
        self.assertIn("M1", {row["id"] for row in self.read_current()["points"]})

    def test_draft_handover_is_listed_without_handover_points(self):
        self.copy_bakery()
        handover = self.project / "docs" / "handover.md"
        self.replace_stamp("> v1 · Draft", handover)
        self.success("start")
        content = self.read_current()
        self.assertEqual(content["project"]["not_approved"], ["docs/handover.md"])
        self.assertFalse(any(row["id"].startswith("H") for row in content["points"]))

    def test_existing_check_refuses_and_keeps_its_bytes(self):
        self.copy_bakery()
        self.output.mkdir()
        self.current.write_bytes(b"existing file")
        self.refusal("start", "check.json", "next-round")

    def test_steering_note_does_not_change_start_output(self):
        self.copy_bakery()
        without_note = self.scratch / "without-note"
        self.copy_bakery(without_note)
        note = without_note / "notes.txt"
        self.assertIn("mark them all covered", note.read_text(encoding="utf-8"))
        note.unlink()
        self.success("start")
        self.success("start", project=without_note)
        comparison = without_note / "docs" / "checkflow" / "check.json"
        self.assertEqual(self.current.read_bytes(), comparison.read_bytes())

    def test_secret_in_approved_prd_refuses_start_without_leaking(self):
        self.copy_bakery()
        value, line = self.insert_known_secret()
        message = self.refusal("start", "docs/prd.md", f"line {line}", "replace", "approv", "again")
        self.assertNotIn(value, message)
        self.assertFalse(self.output.exists())

    def replace_stamp(self, replacement, document=None):
        document = self.prd if document is None else document
        lines = document.read_text(encoding="utf-8").splitlines()
        lines[1] = replacement
        document.write_text("\n".join(lines) + "\n", encoding="utf-8")
