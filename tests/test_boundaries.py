import json
import os
import subprocess
import sys

from checkflow_case import CheckflowCase, SKILL, snapshot


NO_SOCKETS = """
from pathlib import Path
import runpy
import sys
import types

class SocketUnavailable(types.ModuleType):
    def __getattr__(self, name):
        raise AssertionError("Socket access attempted.")

sys.modules["socket"] = SocketUnavailable("socket")
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""


class BoundaryTests(CheckflowCase):
    def test_project_path_refuses_paths_outside_root(self):
        # No CLI command accepts an arbitrary storage path.
        launcher = """
import sys

sys.path.insert(0, sys.argv[1])
from checkflow_tool.storage import Project, Refusal

project = Project(sys.argv[2])
operation, name = sys.argv[3:]
try:
    if operation == "write":
        project.write(name, b"changed")
    else:
        print(getattr(project, operation)(name))
except Refusal as exc:
    sys.exit(str(exc))
"""

        def run(operation, name):
            return subprocess.run(
                [sys.executable, "-B", "-c", launcher, str(SKILL / "scripts"),
                 str(self.project), operation, name],
                encoding="utf-8", capture_output=True, timeout=15,
                env={**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": ""},
            )

        def assert_refused(operation, name):
            result = run(operation, name)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(result.stderr.strip(), f"Use a regular path inside the project for {name}.")

        outside = self.scratch.resolve() / "outside.txt"
        outside.write_bytes(b"outside")
        (self.project / "docs").mkdir()
        (self.project / "inside.txt").write_bytes(b"inside")
        refused = [
            ("read", str(outside)),
            ("write", str(outside)),
            ("path", str(outside.parent)),
            ("path", "../outside.txt"),
            ("path", "docs/../../outside.txt"),
        ]
        if os.name == "nt":
            refused.extend(("path", name) for name in (
                r"C:\outside.txt", "C:outside.txt", r"\outside.txt",
                r"\\server\share\outside.txt", r"..\outside.txt",
            ))
            if self.project.drive.upper() != "C:":
                refused.append(("path", f"{self.project.drive}outside.txt"))
        for operation, name in refused:
            with self.subTest(operation=operation, name=name):
                assert_refused(operation, name)

        with self.subTest(case="outside file contents"):
            self.assertEqual(outside.read_bytes(), b"outside")
        with self.subTest(case="symlink to outside file"):
            link = self.project / "outside-link.txt"
            try:
                link.symlink_to(outside)
            except (NotImplementedError, OSError) as exc:
                self.skipTest(f"Cannot create a symlink in the test project: {exc}")
            assert_refused("path", link.name)

        for operation, name, expected in (
            ("path", ".", str(self.project.resolve())),
            ("read", "inside.txt", "b'inside'"),
        ):
            with self.subTest(operation=operation, name=name):
                result = run(operation, name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.rstrip("\n"), expected)

    def write_distinct_second_check(self):
        second = self.read_current()
        second["checks"][0]["reason"] = "The other check separately confirmed there is no login path."
        (self.output / "second-check.json").write_text(json.dumps(second), encoding="utf-8")

    def test_commands_write_only_inside_the_project_check_folder(self):
        self.copy_bakery()
        excluded = ("project/docs/checkflow",)
        before = snapshot(self.scratch, exclude=excluded)
        skill_before = snapshot(SKILL)
        self.finished_answer()
        self.write_distinct_second_check()
        self.success("check")
        self.success("merge")
        self.success("report")
        self.success("next-round")
        self.assertEqual(before, snapshot(self.scratch, exclude=excluded))
        self.assertEqual(skill_before, snapshot(SKILL))

    def test_all_commands_work_without_sockets_or_site_packages(self):
        self.finished_answer()
        self.write_distinct_second_check()
        guarded = {"interpreter_args": ("-S", "-c"), "wrapper": (NO_SOCKETS,)}
        clean_fixture = self.scratch / "clean"
        self.copy_bakery(clean_fixture)
        self.success("start", project=clean_fixture, **guarded)
        self.success("check", **guarded)
        self.success("merge", **guarded)
        self.success("report", **guarded)
        self.success("next-round", **guarded)
