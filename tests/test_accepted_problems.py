"""Owner decisions waive named gaps while preserving the full check evidence."""

from test_project_document import DocumentCase


PROBLEM = "The bakery notice service needs an update."
REASON = "The owner will wait for the supplier to release an update."
SECRETS_CHECK = "Local settings files are ignored by git"
PACKAGES_CHECK = "The packages it uses have no known serious weakness"


class AcceptedProblemTests(DocumentCase):
    def make_open_problem(self, *, reason=REASON, failed=True, linked=True,
                          check_name=SECRETS_CHECK, problem_group=None):
        self.clean()
        data = self.read_current()
        check = next(row for row in data["checks"] if row["check"] == check_name)
        if failed:
            check.update(result="fail", reason="The trial still found a gap.")
        problem = {
            "id": "P2", "group": problem_group or check["group"], "line": PROBLEM,
            "state": "still open",
            "next": "Review the next supplier update.",
        }
        if reason is not None:
            problem["accepted"] = reason
        if linked:
            problem["check"] = check["check"]
        data["problems"].append(problem)
        return data

    def verdict(self, data):
        self.write_current(data)
        self.success("report")
        report = self.report.read_text(encoding="utf-8")
        return report.split("## Verdict\n\n", 1)[1].split("\n\n## Who checked", 1)[0], report

    def test_a_written_reason_waives_the_problem_and_named_failed_check(self):
        verdict, report = self.verdict(self.make_open_problem())
        self.success("check")
        self.assertEqual(verdict, "Clean, with 1 problem accepted by the owner")
        self.assertIn(f"still open: {PROBLEM}", report)
        self.assertIn(REASON, report)
        self.assertIn("**fail**", report)

    def test_the_packages_check_can_be_accepted_in_the_release_group(self):
        data = self.make_open_problem(check_name=PACKAGES_CHECK)
        self.assertEqual(data["problems"][-1]["group"], "The release")
        verdict, _ = self.verdict(data)
        self.assertEqual(verdict, "Clean, with 1 problem accepted by the owner")

    def test_backup_and_speed_failures_cannot_be_linked_to_an_accepted_problem(self):
        data = self.make_open_problem(check_name="A backup exists", problem_group="Secrets")
        problem = data["problems"][-1]
        for check_name in ("A backup exists", "It meets the speed the approved documents name"):
            check = next(row for row in data["checks"] if row["check"] == check_name)
            check.update(result="fail", reason="The trial still found a gap.")
            problem["check"] = check_name
            for group in ("Secrets", check["group"]):
                problem["group"] = group
                self.write_current(data)
                for command in ("check", "report", "document"):
                    with self.subTest(check=check_name, group=group, command=command):
                        self.refuse(command, ".check", "failed")
            check["result"] = "pass"

    def test_failed_secrets_check_cannot_be_linked_to_a_different_security_group(self):
        self.write_current(self.make_open_problem(problem_group="Who gets in"))
        for command in ("check", "report", "document"):
            with self.subTest(command=command):
                self.refuse(command, ".check", "same group")

    def test_multiple_problems_use_the_plural(self):
        data = self.make_open_problem()
        second = dict(data["problems"][-1], id="P3", line="A second problem remains open.")
        data["problems"].append(second)
        verdict, report = self.verdict(data)
        self.assertEqual(verdict, "Clean, with 2 problems accepted by the owner")
        self.assertIn(second["line"], report)

    def test_an_open_problem_without_reason_stays_not_clean(self):
        data = self.make_open_problem(reason=None)
        for reason in (None, "", " \t "):
            with self.subTest(reason=reason):
                if reason is not None:
                    data["problems"][-1]["accepted"] = reason
                verdict, _ = self.verdict(data)
                self.assertIn("Not clean", verdict)
                self.assertIn("1 open problems", verdict)
                self.assertIn("1 failed project checks", verdict)

    def test_accepted_reason_on_a_fixed_row_is_refused(self):
        data = self.make_open_problem(failed=False, linked=False)
        data["problems"][-1]["state"] = "fixed"
        self.write_current(data)
        self.refuse("report", "accepted", "still open")

    def test_link_must_name_a_real_failed_check(self):
        data = self.make_open_problem(failed=False)
        for check in (SECRETS_CHECK, "An unknown check"):
            with self.subTest(check=check):
                data["problems"][-1]["check"] = check
                self.write_current(data)
                self.refuse("report", "check", "failed")

    def test_a_failure_without_an_accepted_link_stays_not_clean(self):
        verdict, _ = self.verdict(self.make_open_problem(linked=False))
        self.assertIn("Not clean", verdict)
        self.assertIn("1 failed project checks", verdict)
        self.assertNotIn("open problems", verdict)

    def test_acceptance_without_a_failed_check_is_allowed(self):
        verdict, _ = self.verdict(self.make_open_problem(failed=False, linked=False))
        self.assertEqual(verdict, "Clean, with 1 problem accepted by the owner")

    def test_an_unsupported_bar_still_wins(self):
        data = self.make_open_problem()
        data["project"]["bar"] = "Fixture higher bar"
        verdict, _ = self.verdict(data)
        self.assertIn("Not clean", verdict)
        self.assertIn("higher bar", verdict)
