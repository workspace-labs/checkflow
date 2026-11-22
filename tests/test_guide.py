"""Check that public wording and success feedback stay within scope."""

import hashlib
import json
import re
import subprocess
import sys

from checkflow_case import ASSET, CLI, CheckflowCase, FIXTURES, ROOT, SKILL


class GuideTests(CheckflowCase):
    def test_readme_keeps_public_promises_and_names_real_commands(self):
        guide = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("/Users/", guide, "README contains a local home-directory path")
        lines = guide.splitlines()
        self.assertIn(
            "![checkflow: read what was approved, check the client points and the project, "
            "fix with the builder, deliver a client document and a technical document]"
            "(media/checkflow-hero.png)",
            lines,
            "README picture or alt text changed",
        )
        self.assertIn(
            "*Sample pages. Your documents follow your project's own design.*",
            lines,
            "README sample caption changed",
        )
        self.assertRegex(guide.lower(), r"\b(never deploys|does not deploy|will not deploy)\b")
        clean = guide.partition("\n## What Clean means\n")[2].partition("\n## ")[0]
        self.assertIn("found no gaps", clean)
        self.assertIn("There may still be bugs.", clean)
        self.assertIn("The tool cannot tell whether a proof is true.", " ".join(clean.split()))
        limits = guide.partition("\n## Limits\n")[2].partition("\n## ")[0]
        self.assertIn("not tested on windows yet", limits.lower())

        help_text = subprocess.run(
            [sys.executable, str(CLI), "--help"], cwd=ROOT,
            encoding="utf-8", capture_output=True, check=True, timeout=15,
        ).stdout
        choices = re.search(r"\{([^}]+)\}", help_text)
        self.assertIsNotNone(choices, help_text)
        known = set(choices.group(1).split(","))
        used = set(re.findall(r"\bcheckflow\.py[ \t]+([^\s`]+)", guide)) - {"-h", "--help"}
        usage = guide.partition("\n## Use it\n")[2].partition("\n## ")[0]
        used.update(re.findall(r"(?m)^\|\s*`([\w-]+)[^`]*`\s*\|", usage))
        self.assertTrue(used)
        self.assertEqual(used - known, set(), "README commands missing from checkflow.py --help")

    def test_start_and_report_say_when_they_succeed(self):
        fresh = self.scratch / "fresh"
        self.copy_bakery(fresh)
        self.assertEqual(self.success("start", project=fresh).stdout, "Check started.\n")
        self.finished_answer()
        self.assertEqual(self.success("report").stdout, "Full check written.\n")

    def test_answer_key_and_guide_cover_the_named_checks(self):
        groups = json.loads((SKILL / "assets/checks/basic.json").read_text(encoding="utf-8"))
        guide = (SKILL / "references/project-checks.md").read_text(encoding="utf-8")
        names = [row["check"] for group in groups for row in group["checks"]]
        self.assertEqual(len(set(names)), 52)
        self.assertEqual(re.findall(r"^- \*\*(.+)\*\*$", guide, re.MULTILINE), names)
        # The ordered check names before Build 4 (85926e9).
        self.assertEqual(
            hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest(),
            "701c9c244e26f2cbdeaabdc1262b381c2fea7e69ed7bdd18edb1022afad26238",
        )
        key = json.loads((FIXTURES / "corner-bakery.expected.json").read_text(encoding="utf-8"))
        self.assertEqual(len({(row["group"], row["check"]) for row in key["checks"]}), 13)

    def test_six_updated_rules_agree_between_the_guides(self):
        groups = json.loads(ASSET.read_text(encoding="utf-8"))
        rows = {row["check"]: row for group in groups for row in group["checks"]}
        guide = (SKILL / "references/project-checks.md").read_text(encoding="utf-8")
        rules = [
            ("File uploads are limited by type and size", "how", "How to check it",
             ("every way the project takes in files", "server upload", "opening a file",
              "cable transfer", "accepted types and size limits")),
            ("Settings come from the environment, and the example settings file holds names only",
             "how", "How to check it",
             ("no example file", "setting names listed in an approved document or the guide")),
            ("A backup exists", "how", "How to check it",
             ("record counts only if", "dated after the last change to the shape of the saved data")),
            ("Errors are recorded, with no password or key in the record", "not_applicable",
             "When it does not apply",
             ("one person is the only user", "sees every error on screen",
              "no approved document requires an error record")),
            ("Someone is told when it fails, and a named person owns that", "not_applicable",
             "When it does not apply",
             ("duty to tell someone about a software failure", "lost device or a leak",
              "do not count as a duty to tell")),
            ("Users have a way to report a problem", "not_applicable",
             "When it does not apply", ("owner is the only user", "builds through AI agents")),
        ]
        for name, field, label, fragments in rules:
            with self.subTest(check=name):
                section = guide.split(f"- **{name}**\n", 1)[1].split("\n\n", 1)[0]
                guide_rule = next(
                    line.removeprefix(f"  - {label}. ") for line in section.splitlines()
                    if line.startswith(f"  - {label}. ")
                )
                self.assertEqual(guide_rule, rows[name][field])
                for fragment in fragments:
                    self.assertIn(fragment, guide_rule)

    def test_delivery_copy_check_uses_the_same_record_rule_in_both_guides(self):
        name = "The copy that will go live is the copy that was tested"
        groups = json.loads(ASSET.read_text(encoding="utf-8"))
        release = next(group for group in groups if group["group"] == "The release")
        rule = next(row["how"] for row in release["checks"] if row["check"] == name)
        guide = (SKILL / "references/project-checks.md").read_text(encoding="utf-8")
        heading = f"- **{name}**\n  - How to check it. "
        self.assertEqual(guide.partition(heading)[2].partition("\n")[0], rule)
        self.assertIn("a record already kept with the project", rule)
        self.assertIn("by version, commit or checksum", rule)
        self.assertIn("ties that copy to a successful test run", rule)
        self.assertIn("supporting evidence only and cannot make this check pass", rule)
        self.assertIn("name the record the owner must supply in the reason", rule)

    def test_public_skill_branding_is_limited_to_the_approved_credit(self):
        credit = "Made with checkflow, a WorkSpace Labs skill"
        for path in SKILL.rglob("*"):
            if path.suffix in {".md", ".json", ".py", ".txt", ".css"} and path.is_file():
                text = path.read_text(encoding="utf-8").replace(credit, "")
                self.assertNotIn("workspace labs", text.casefold(), path.name)
