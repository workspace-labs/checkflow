import re

from checkflow_case import CheckflowCase, GROUP_COUNTS, snapshot


class ReportTests(CheckflowCase):
    def test_bakery_report_contains_every_result_and_no_key(self):
        content = self.finished_answer()
        self.success("report")
        report = self.report.read_text(encoding="utf-8")
        verdict = self.section(report, 2, "Verdict")
        self.assertIn("Not clean", verdict)
        self.assertIn("1 client point with something wrong", verdict)
        self.assertRegex(verdict, r"1 client point that works so far and needs the owner['’]s try")
        points = re.search(r"(?ms)^## Client points\n(.*?)^## Changes$", report)
        self.assertIsNotNone(points)
        self.assertEqual(re.findall(r"(?m)^### (.+)$", points[1]), [
            "Missing", "Partly: something is wrong", "Partly: works so far, needs your try",
            "Changed", "Covered",
        ])
        self.assertIn("M4", self.section(report, 3, "Missing"))
        wrong = self.section(report, 3, "Partly: something is wrong")
        untried = self.section(report, 3, "Partly: works so far, needs your try")
        self.assertIn("M5", wrong)
        self.assertNotIn("W1", wrong)
        self.assertIn("W1", untried)
        self.assertNotIn("M5", untried)
        self.assertIn("M3", self.section(report, 3, "Changed"))
        changes = self.section(report, 2, "Changes")
        for change in content["changes"]:
            self.assertIn(change["kind"], changes)
            self.assertIn(change["what"], changes)
            self.assertIn(change["decision"], changes)
        for group in GROUP_COUNTS:
            section = self.section(report, 3, group)
            for check in (row for row in content["checks"] if row["group"] == group):
                with self.subTest(check=check["check"]):
                    self.assertIn(check["check"], section)
                    self.assertIn(check["reason"], section)
                    self.assertIn(check["result"], section)
        self.assertRegex(report, r"(?i)bar[^\n]*basic")
        problems = self.section(report, 2, "Problems found")
        for problem in content["problems"]:
            self.assertIn(problem["line"], problems)
            self.assertIn(problem["state"], problems)
        for raw in snapshot(self.output).values():
            if isinstance(raw, bytes):
                self.assertNotIn(b"bakery_live_PLANTED_7f3a91c2", raw)

    def test_clean_when_everything_is_closed(self):
        self.write_clean_content()
        self.success("report")
        verdict = self.section(self.report.read_text(encoding="utf-8"), 2, "Verdict")
        self.assertRegex(verdict, r"(?m)^\**Clean\**\s*$")
        self.assertNotIn("Not clean", verdict)

    def test_either_kind_of_partly_on_its_own_blocks_clean(self):
        content = self.write_clean_content()
        for gap in ("wrong", "untried"):
            with self.subTest(gap=gap):
                content["points"][0].update(mark="partly", gap=gap)
                self.write_current(content)
                self.success("report")
                verdict = self.section(self.report.read_text(encoding="utf-8"), 2, "Verdict")
                self.assertIn("Not clean", verdict)

    def test_requested_higher_bar_is_reported_first_and_blocks_clean(self):
        content = self.write_clean_content()
        content["project"]["bar"] = "Fixture accessibility standard"
        self.write_current(content)
        self.success("report")
        report = self.report.read_text(encoding="utf-8")
        verdict = self.section(report, 2, "Verdict")
        self.assertIn("Not clean", verdict)
        self.assertIn("Fixture accessibility standard", verdict)
        self.assertIn("not supported yet", verdict.lower())
        self.assertRegex(report, r"(?i)bar[^\n]*basic")
        self.assertIn("Who gets in", report)

    def test_invalid_check_cannot_overwrite_report(self):
        content = self.finished_answer()
        self.report.write_text("Existing report.\n", encoding="utf-8")
        content["points"][0]["proof"] = ""
        self.write_current(content)
        self.refusal("report", "proof")

    def write_clean_content(self):
        content = self.finished_answer()
        for point in content["points"]:
            point.update(mark="covered", gap="")
        for check in content["checks"]:
            if check["result"] == "fail":
                check["result"] = "pass"
                check["reason"] = "The sample defect was treated as resolved for this verdict test."
        for change in content["changes"]:
            change["decision"] = "keep"
            change["done"] = True
        for problem in content["problems"]:
            problem["state"] = "fixed"
        self.write_current(content)
        return content

    def section(self, report, level, heading):
        hashes = "#" * level
        pattern = rf"(?m)^{hashes} {re.escape(heading)}\s*$"
        start = re.search(pattern, report)
        self.assertIsNotNone(start, f"Missing {heading!r} section")
        return re.split(rf"(?m)^#{{1,{level}}} ", report[start.end():], maxsplit=1)[0]
