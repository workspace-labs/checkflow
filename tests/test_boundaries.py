import json

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
