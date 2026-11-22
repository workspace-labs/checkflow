import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "checkflow"
CLI = SKILL / "scripts" / "checkflow.py"
FIXTURES = ROOT / "tests" / "fixtures"
ASSET = SKILL / "assets" / "checks" / "basic.json"
GROUP_COUNTS = {
    "Who gets in": 7,
    "Secrets": 6,
    "Bad input": 6,
    "The connection": 7,
    "Data and privacy": 5,
    "The release": 3,
    "Accessibility": 5,
    "Easy to use": 5,
    "Speed": 3,
    "People who run it": 5,
}


def reads_with_poppler():
    """Tell Poppler's pdftotext from Xpdf's, which shares its name and options."""
    if not shutil.which("pdftotext"):
        return False
    version = subprocess.run(["pdftotext", "-v"], capture_output=True, timeout=10)
    return b"poppler" in (version.stdout + version.stderr).lower()


POPPLER = reads_with_poppler()
NEEDS_POPPLER = "These Arabic PDF text checks are written for Poppler's pdftotext, and this reader is not Poppler."


def snapshot(folder, exclude=()):
    """Record both empty directories and file bytes."""
    files = {}
    for path in folder.rglob("*"):
        relative = path.relative_to(folder).as_posix()
        if any(relative == item or relative.startswith(item + "/") for item in exclude):
            continue
        if path.is_symlink():
            files[relative] = ("link", os.readlink(path))
        else:
            files[relative] = None if path.is_dir() else path.read_bytes()
    return files


class CheckflowCase(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(dir=ROOT, prefix=".checkflow-test-")
        self.addCleanup(scratch.cleanup)
        self.scratch = Path(scratch.name)
        self.project = self.scratch / "project"
        self.project.mkdir()
        self.output = self.project / "docs" / "checkflow"
        self.current = self.output / "check.json"
        self.report = self.output / "full-check.md"
        self.prd = self.project / "docs" / "prd.md"

    def copy_bakery(self, destination=None):
        target = self.project if destination is None else destination
        shutil.copytree(
            FIXTURES / "corner-bakery",
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "checkflow"),
        )

    def run_tool(self, command, *, project=None, interpreter_args=(), wrapper=()):
        return subprocess.run(
            [
                sys.executable,
                *interpreter_args,
                *wrapper,
                str(CLI),
                command,
                str(self.project if project is None else project),
            ],
            cwd=ROOT,
            encoding="utf-8",
            capture_output=True,
            timeout=15,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": ""},
        )

    def success(self, command, **kwargs):
        run = self.run_tool(command, **kwargs)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return run

    def refusal(self, command, *fragments, project=None):
        target = self.project if project is None else project
        before = snapshot(target)
        run = self.run_tool(command, project=project)
        self.assertNotEqual(run.returncode, 0)
        text = run.stdout + run.stderr
        self.assertRegex(text, r"(?m)^1[.)]\s+\S")
        self.assertNotIn("Traceback", text)
        for fragment in fragments:
            self.assertIn(fragment.lower(), text.lower())
        self.assertEqual(snapshot(target), before, "Refusal changed the project folder")
        return text

    def read_current(self):
        return json.loads(self.current.read_text(encoding="utf-8"))

    def write_current(self, content):
        self.current.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    def start_bakery(self):
        self.copy_bakery()
        self.success("start")
        return self.read_current()

    def finished_answer(self):
        content = self.start_bakery()
        answer = json.loads(
            (FIXTURES / "corner-bakery.expected.json").read_text(encoding="utf-8")
        )
        content["points"] = answer["points"]
        content["changes"] = answer["changes"]
        content["problems"] = answer["problems"]

        # The answer key only fixes outcomes deducible from the fixture.
        # Complete the other rows with test data to exercise validation and rendering.
        expected_checks = {
            (row["group"], row["check"]): row for row in answer["checks"]
        }
        for row in content["checks"]:
            fixed = expected_checks.pop((row["group"], row["check"]), None)
            row["result"] = fixed["result"] if fixed else "pass"
            row["reason"] = fixed["reason"] if fixed else "Evidence supplied for this test."
        self.assertEqual(expected_checks, {})
        self.write_current(content)
        return content

    def insert_known_secret(self):
        value = "fixture_test_setting_94a70"
        (self.project / ".env").write_text(
            f"BAKERY_API_KEY={value}\n", encoding="utf-8"
        )
        lines = self.prd.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines):
            if line.startswith("- **M1.**"):
                lines[number] = f"{line} {value}"
                break
        else:
            self.fail("The sample PRD is missing M1")
        self.prd.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return value, number + 1
