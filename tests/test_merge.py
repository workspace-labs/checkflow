"""Try the second-checker workflow through the checkflow CLI."""

from copy import deepcopy
from itertools import product
import importlib.util
import json
import re
import shutil
import unittest

from checkflow_case import CheckflowCase, FIXTURES, snapshot
from test_build3 import letters
from test_project_document import DocumentCase, DocumentHtml, normalize


POINT_ORDER = (("missing", ""), ("partly", "wrong"), ("changed", ""),
               ("partly", "untried"), ("covered", ""))
CHECK_ORDER = ("fail", "pass", "does not apply")


def change(identifier, words, point=""):
    return {"id": identifier, "kind": "different" if point else "extra", "what": words,
            "point": point, "decision": "not decided", "done": False}


def problem(identifier, words):
    return {"id": identifier, "group": "Secrets", "line": words, "state": "still open"}


class MergeTests(CheckflowCase):
    @property
    def second(self):
        return self.output / "second-check.json"

    def write_second(self, data):
        self.second.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_missing_second_check_refuses_without_writes(self):
        self.finished_answer()
        self.refusal("merge", "second-check.json")

    def test_invalid_and_unfinished_second_check_refuse_without_writes(self):
        data = self.finished_answer()
        for contents in (b"{", b"[]", b"\xff", b'{"project": {}, "project": {}}'):
            with self.subTest(contents=contents):
                self.second.write_bytes(contents)
                self.refusal("merge", "second-check.json")
        unfinished = deepcopy(data)
        unfinished["points"][0]["proof"] = ""
        self.write_second(unfinished)
        self.refusal("merge", "second-check.json", "proof")

    def test_round_ids_text_and_source_mismatches_refuse_without_writes(self):
        first = self.finished_answer()
        for key, value in (("round", 2), ("id", "M101"), ("text", "Different wording."),
                           ("source", "docs/other.md, Different heading")):
            with self.subTest(key=key):
                second = deepcopy(first)
                target = second["project"] if key == "round" else second["points"][0]
                target[key] = value
                self.write_second(second)
                self.refusal("merge", "round" if key == "round" else "point")

    def test_a_second_merge_in_the_same_round_refuses_without_writes(self):
        first = self.finished_answer()
        second = deepcopy(first)
        second["checks"][0]["reason"] = "The other check separately confirmed there is no login path."
        self.write_second(second)
        self.success("merge")
        self.refusal("merge", "already merged")

        # A restored first check does not erase the fact that the round was merged.
        self.write_current(first)
        self.refusal("merge", "already merged")

    def test_identical_results_and_evidence_refuse_without_writes(self):
        base = self.finished_answer()
        for round_number, difference in enumerate(("none", "format and order", "other rows"), start=1):
            with self.subTest(difference=difference):
                first = deepcopy(base)
                first["project"]["round"] = round_number
                self.write_current(first)
                if difference == "none":
                    self.second.write_bytes(self.current.read_bytes())
                else:
                    second = deepcopy(first)
                    if difference == "format and order":
                        second["points"][0].pop("gap")
                        second["points"].reverse()
                        second["checks"].reverse()
                    else:
                        second["project"]["bar"] = "ASVS level 2"
                        second["changes"].append(change("C102", "A separate extra feature."))
                        second["problems"].append(problem("P102", "A separate security problem."))
                    reformatted = json.dumps(second, ensure_ascii=False, indent=4, sort_keys=True)
                    self.second.write_text(reformatted, encoding="utf-8")
                    self.assertNotEqual(self.current.read_bytes(), self.second.read_bytes())
                self.refusal("merge", "identical")

    def test_report_refuses_if_second_input_is_replaced_with_a_copy(self):
        first = self.finished_answer()
        first_bytes = self.current.read_bytes()
        second = deepcopy(first)
        second["checks"][0]["reason"] = "The other check separately confirmed there is no login path."
        self.write_second(second)
        self.success("merge")
        self.success("report")
        self.second.write_bytes(first_bytes)
        self.refusal("report", "identical")

    def test_a_different_partly_gap_is_a_distinct_point_result(self):
        first = self.finished_answer()
        second = deepcopy(first)
        point = next(row for row in second["points"] if row["gap"] == "untried")
        point["gap"] = "wrong"
        self.write_second(second)
        self.success("merge")
        merged_point = next(row for row in self.read_current()["points"] if row["id"] == point["id"])
        self.assertEqual((merged_point["mark"], merged_point["gap"]), ("partly", "wrong"))

    def test_a_higher_bar_from_either_check_prevents_clean(self):
        base = self.finished_answer()
        for point in base["points"]:
            point.update(mark="covered", gap="")
        for check in base["checks"]:
            check.update(result="pass")
        base["changes"] = []
        base["problems"] = []
        scenarios = (
            ("ASVS level 2", "basic", ("ASVS level 2",)),
            ("basic", "ASVS level 2", ("ASVS level 2",)),
            ("ASVS level 2", "WCAG 2.2 AA", ("ASVS level 2", "WCAG 2.2 AA")),
        )
        for round_number, (left, right, expected) in enumerate(scenarios, start=1):
            with self.subTest(first=left, second=right):
                first, second = deepcopy(base), deepcopy(base)
                first["project"].update(round=round_number, bar=left)
                second["project"].update(round=round_number, bar=right)
                second["checks"][0]["reason"] = "The other checker carried out the check separately."
                self.write_current(first)
                self.write_second(second)
                self.success("merge")
                bar = self.read_current()["project"]["bar"]
                self.success("report")
                report = self.report.read_text(encoding="utf-8")
                verdict = report.split("## Verdict\n", 1)[1].split("## Who checked", 1)[0]
                self.assertIn("Not clean", verdict)
                self.assertIn("not supported", verdict.lower())
                for name in expected:
                    self.assertIn(name, verdict)
                    self.assertIn(name, bar)
                if len(expected) == 1:
                    self.assertEqual(bar, expected[0])

    def test_owner_decisions_refuse_merge_without_writes(self):
        first = self.finished_answer()
        self.write_second(first)
        for decision in ("keep", "fix back", "done", "accepted problem", "confirmed date", "language"):
            with self.subTest(decision=decision):
                decided = deepcopy(first)
                if decision in ("keep", "fix back"):
                    decided["changes"][0]["decision"] = decision
                elif decision == "done":
                    decided["changes"][0]["done"] = True
                elif decision == "accepted problem":
                    decided["problems"][0].update(state="still open", accepted="Owner's written reason.")
                elif decision == "confirmed date":
                    decided["dates"].append({"id": "D1", "kind": "start", "date": "2026-11-30",
                                             "source": "the owner", "confirmed": True})
                else:
                    decided["project"]["language"] = "en"
                self.write_current(decided)
                self.refusal("merge", "decision")

    def test_known_secret_in_either_file_is_refused_and_never_printed(self):
        first = self.finished_answer()
        value = "synthetic_merge_secret_981ab4"
        (self.project / ".env").write_text(f"CHECKFLOW_API_KEY={value}\n", encoding="utf-8")
        unsafe = deepcopy(first)
        unsafe["points"][0]["proof"] = f"A synthetic known value {value}."
        for field in ("first", "second"):
            with self.subTest(file=field):
                self.write_current(unsafe if field == "first" else first)
                self.write_second(unsafe if field == "second" else first)
                message = self.refusal("merge", "secret")
                self.assertNotIn(value, message)

    def test_point_order_for_every_pair_in_both_directions(self):
        base = self.finished_answer()
        pairs = list(product(range(len(POINT_ORDER)), repeat=2))
        batch_size = len(base["points"])
        for round_number, offset in enumerate(range(0, len(pairs), batch_size), 1):
            first, second = deepcopy(base), deepcopy(base)
            batch = pairs[offset:offset + batch_size]
            expected = {}
            for side, payload in enumerate((first, second)):
                payload["project"]["round"] = round_number
                payload["changes"] = []
                for index, row in enumerate(payload["points"]):
                    pair = batch[index] if index < len(batch) else (4, 4)
                    mark, gap = POINT_ORDER[pair[side]]
                    row.update(mark=mark, gap=gap, round=round_number)
                    expected[row["id"]] = POINT_ORDER[min(pair)]
                    if mark == "changed":
                        payload["changes"].append(change(f"C{index + 1}", "A different method was used.",
                                                         row["id"]))
            second["checks"][0]["reason"] = "The other check separately confirmed there is no login path."
            self.write_current(first)
            second["points"].reverse()
            self.write_second(second)
            self.success("merge")
            merged = self.read_current()
            linked = {row.get("point") for row in merged["changes"] if row["kind"] == "different"}
            for row in merged["points"]:
                with self.subTest(round=round_number, point=row["id"]):
                    self.assertEqual((row["mark"], row.get("gap", "")), expected[row["id"]])
                    if row["mark"] == "changed":
                        self.assertIn(row["id"], linked)
            self.success("check")

    def test_check_order_for_every_pair_in_both_directions(self):
        first = self.finished_answer()
        second = deepcopy(first)
        # Use a fixture without linked security decisions while changing check results.
        first["problems"] = second["problems"] = []
        pairs = product(range(len(CHECK_ORDER)), repeat=2)
        expected = {}
        for left, right, (left_rank, right_rank) in zip(first["checks"], second["checks"], pairs):
            left["result"] = CHECK_ORDER[left_rank]
            right["result"] = CHECK_ORDER[right_rank]
            expected[left["group"], left["check"]] = CHECK_ORDER[min(left_rank, right_rank)]
        self.assertEqual(len(expected), 9)
        self.write_current(first)
        second["checks"].reverse()
        self.write_second(second)
        self.success("merge")
        merged = {(row["group"], row["check"]): row["result"] for row in self.read_current()["checks"]}
        self.assertEqual({key: merged[key] for key in expected}, expected)
        self.success("check")

    def test_merge_keeps_unique_rows_and_preserves_links_ids_and_owner_state(self):
        first = self.finished_answer()
        second = deepcopy(first)
        left, right = first["points"][0], second["points"][0]
        left.update(mark="partly", gap="untried")
        right.update(mark="changed", gap="")
        second["changes"][0]["id"] = "C99"
        second["changes"].extend((change("C1", "Another extra feature."),
                                  change("C98", "An order uses a different input.", right["id"])))
        second["problems"][0]["id"] = "P99"
        second["problems"].append(problem(first["problems"][0]["id"], "A separate security problem."))
        self.write_current(first)
        self.write_second(second)
        before_files = snapshot(self.project, exclude=("docs/checkflow",))
        self.success("merge")
        merged = self.read_current()
        self.assertEqual(snapshot(self.project, exclude=("docs/checkflow",)), before_files)
        self.assertEqual(merged["points"][0]["mark"], "changed")
        self.assertEqual(merged["changes"][:len(first["changes"])], first["changes"])
        self.assertEqual({row["what"] for row in merged["changes"]}, {row["what"] for row in second["changes"]})
        self.assertEqual(merged["problems"][:len(first["problems"])], first["problems"])
        self.assertEqual({row["line"] for row in merged["problems"]}, {row["line"] for row in second["problems"]})
        for name in ("changes", "problems"):
            self.assertEqual(len(merged[name]), len(second[name]))
            self.assertEqual(len({row["id"] for row in merged[name]}), len(merged[name]))
            original_ids = {row["id"] for source in (first, second) for row in source[name]}
            self.assertFalse({row["id"] for row in merged[name][len(first[name]):]} & original_ids)
        for row in merged["changes"]:
            self.assertEqual((row["decision"], row["done"]), ("not decided", False))
        linked = next(row for row in merged["changes"] if row["what"] == "An order uses a different input.")
        self.assertEqual((linked["kind"], linked["point"]), ("different", right["id"]))
        self.success("check")

    def test_reports_mark_only_outcome_disagreements_and_keep_each_distinct_proof(self):
        first = self.finished_answer()
        second = deepcopy(first)
        first["points"][0].update(proof="The menu was checked with the primary command.")
        second["points"][0].update(mark="partly", gap="wrong", proof="The menu price was wrong.")
        second["points"][1]["proof"] = "Alternate proof for the same outcome."
        first["checks"][0].update(result="pass", reason="The standard trial passed.")
        second["checks"][0].update(result="fail", reason="The second trial failed.")
        second["checks"][1]["reason"] = "Additional evidence for the same outcome."
        self.write_current(first)
        self.write_second(second)
        self.success("merge")
        merged = self.read_current()
        for index in (0, 1):
            proof = merged["points"][index]["proof"]
            for text in ("First checker:", "Second checker:", first["points"][index]["proof"],
                         second["points"][index]["proof"]):
                self.assertIn(text, proof)
        self.assertEqual(merged["checks"][0]["reason"],
                         "First checker: The standard trial passed.\nSecond checker: The second trial failed.")
        self.assertEqual(merged["checks"][1]["reason"],
                         f"First checker: {first['checks'][1]['reason']}\n"
                         f"Second checker: {second['checks'][1]['reason']}")
        self.assertEqual(merged["points"][2]["proof"], first["points"][2]["proof"])
        self.assertEqual(merged["checks"][2]["reason"], first["checks"][2]["reason"])
        self.success("report")
        report = self.report.read_text(encoding="utf-8")
        self.assertIn("Two independent checkers ran. The worse result is shown for each point.", report)
        self.assertIn("A Clean result means no gap was found. Bugs may still exist.", report)
        self.assertIn("Disagreements: 1 client point and 1 project check.", report)
        marked = [line for line in report.splitlines() if "Checkers disagreed" in line]
        self.assertEqual(len(marked), 2)
        self.assertIn("**M1**", marked[0])
        self.assertIn(first["checks"][0]["check"], marked[1])
        for collection, field in (("points", "proof"), ("checks", "reason")):
            for row in (first[collection][0], second[collection][0]):
                self.assertIn(row[field], report)

    def test_archive_exact_bytes_and_next_round_resets_checker_count_only(self):
        first = self.finished_answer()
        first["project"].pop("checkers", None)  # Legacy checks mean one checker.
        original = json.dumps(first, ensure_ascii=False, indent=4).replace("\n", "\r\n")
        original_bytes = (original + "\r\n").encode("utf-8-sig")
        self.current.write_bytes(original_bytes)
        second = deepcopy(first)
        second["checks"][0]["reason"] = "The other check separately confirmed there is no login path."
        self.write_second(second)
        second_bytes = self.second.read_bytes()
        self.success("merge")
        archive = self.output / "check.before-merge-1.json"
        self.assertEqual(archive.read_bytes(), original_bytes)
        self.assertEqual(self.second.read_bytes(), second_bytes)
        merged = self.read_current()
        self.assertEqual(merged["project"]["checkers"], 2)
        merged_bytes = self.current.read_bytes()
        self.success("report")
        self.assertIn("Disagreements: 0 client points and 0 project checks.",
                      self.report.read_text(encoding="utf-8"))

        self.success("next-round")
        advanced = self.read_current()
        self.assertEqual(advanced["project"], dict(merged["project"], round=2, checkers=1))
        for name in ("points", "checks", "changes", "dates", "problems"):
            self.assertEqual(advanced[name], merged[name])
        self.assertEqual((self.output / "check.round-1.json").read_bytes(), merged_bytes)
        self.assertEqual(archive.read_bytes(), original_bytes)
        self.assertEqual(self.second.read_bytes(), second_bytes)
        self.success("report")
        self.assertNotIn("Two independent checkers ran.", self.report.read_text(encoding="utf-8"))

    def test_single_checker_full_report_snapshot_even_with_legacy_project_data(self):
        data = self.finished_answer()
        data["project"].pop("checkers", None)
        self.write_current(data)
        self.success("report")
        expected = (FIXTURES / "full-check-baseline.md").read_bytes()
        self.assertEqual(self.report.read_bytes(), expected)


@unittest.skipUnless(importlib.util.find_spec("reportlab"),
                     "ReportLab is required to draw the merged documents.")
@unittest.skipUnless(shutil.which("pdftotext"), "Poppler pdftotext is required to read rendered PDF text.")
class MergedDocumentTests(DocumentCase):
    EMAIL_PROOF = "An email reaches the bakery owner for each order."
    LOCAL_PROOF = "Each order writes a local notice, no email is sent."
    AR_EMAIL_PROOF = "تصل رسالة بالبريد الإلكتروني إلى صاحب المخبز عن كل طلب."
    AR_LOCAL_PROOF = "يكتب كل طلب إشعارًا محليًا، ولا يُرسل أي بريد إلكتروني."

    def merge_inputs(self):
        self.clean(choose=False)
        first = self.read_current()
        dates, first["dates"] = first["dates"], []
        for row in first["changes"]:
            row.update(decision="not decided", done=False)
        return first, deepcopy(first), dates

    def merge_and_record_decisions(self, first, second, dates):
        self.write_current(first)
        (self.output / "second-check.json").write_text(json.dumps(second), encoding="utf-8")
        self.success("merge")
        current = self.read_current()
        self.assertEqual(current["project"]["checkers"], 2)
        current["dates"] = dates
        for row in current["changes"]:
            row.update(decision="keep" if row["kind"] == "different" else "fix back", done=True)
        self.write_current(current)

    def rendered_texts(self, name):
        html = (self.output / f"{name}.html").read_text(encoding="utf-8")
        return {
            "html": normalize(" ".join(DocumentHtml(html).body)),
            "pdf": normalize(" ".join(self.pdf_pages(name))),
        }

    def test_both_client_proofs_appear_without_checker_labels_in_html_and_pdf(self):
        first, second, dates = self.merge_inputs()
        first_proof = "The menu test verified the posted prices."
        second_proof = "A separate menu run verified the bread names."
        first["points"][0]["proof"] = first_proof
        second["points"][0]["proof"] = second_proof
        self.merge_and_record_decisions(first, second, dates)
        self.choose()
        self.success("document")
        for name in ("project-document", "technical-document"):
            for medium, output in self.rendered_texts(name).items():
                with self.subTest(document=name, medium=medium):
                    self.assertIsNone(re.search(r"\bcheckers?\b", output, re.IGNORECASE))
                    if name == "project-document":
                        self.assertIn(first_proof, output)
                        self.assertIn(second_proof, output)

    def merge_conflicting_email_proofs(self, *, winner):
        first, second, dates = self.merge_inputs()
        winning, losing = (first, second) if winner == "first" else (second, first)
        next(row for row in winning["points"] if row["id"] == "M3")["proof"] = self.LOCAL_PROOF
        next(row for row in losing["points"] if row["id"] == "M3").update(
            mark="covered", proof=self.EMAIL_PROOF)
        losing["changes"] = [row for row in losing["changes"] if row.get("point") != "M3"]
        self.merge_and_record_decisions(first, second, dates)
        point = next(row for row in self.read_current()["points"] if row["id"] == "M3")
        self.assertEqual(point["mark"], "changed")

    def translate_bakery_with_email_proofs(self):
        language = ("--language", "ar")
        self.success("translate", flags=language)
        path = self.output / "translation-ar.json"
        draft = json.loads(path.read_text(encoding="utf-8"))
        sources = [row["source"] for row in draft["rows"]]
        with self.subTest(stage="Arabic translation source"):
            self.assertFalse(any("An email reaches" in row for row in sources))
            self.assertIn(self.LOCAL_PROOF, sources)
        fixture = json.loads((FIXTURES / "corner-bakery-translation-ar.json").read_text(encoding="utf-8"))
        translated = {row["source"]: row["text"] for row in fixture["rows"]}
        translated.update({
            self.LOCAL_PROOF: self.AR_LOCAL_PROOF,
            f"{self.EMAIL_PROOF} {self.LOCAL_PROOF}": f"{self.AR_EMAIL_PROOF} {self.AR_LOCAL_PROOF}",
            f"{self.LOCAL_PROOF} {self.EMAIL_PROOF}": f"{self.AR_LOCAL_PROOF} {self.AR_EMAIL_PROOF}",
        })
        for row in draft["rows"]:
            row["text"] = translated[row["source"]]
        path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        self.success("confirm-translation", flags=language)

    def assert_only_changed_proof_reaches_client(self):
        self.choose("both")
        self.translate_bakery_with_email_proofs()
        self.success("document")
        for document in ("project-document", "technical-document"):
            for suffix in ("", "-ar"):
                for medium, output in self.rendered_texts(document + suffix).items():
                    with self.subTest(document=document, suffix=suffix, medium=medium):
                        self.assertNotIn("An email reaches", output)
                        self.assertIsNone(re.search(r"\bcheckers?\b", output, re.IGNORECASE))
                        if suffix == "-ar" and medium == "pdf":
                            # Arabic PDF extraction can reverse letter order within a word.
                            words = [letters(word) for word in output.split()]
                            self.assertNotIn(letters("تصل"), words)
                            if document == "project-document":
                                self.assertIn(letters("محليًا"), words)
                        elif suffix == "-ar":
                            self.assertNotIn(self.AR_EMAIL_PROOF, output)
                            if document == "project-document":
                                self.assertIn(self.AR_LOCAL_PROOF, output)
                        elif document == "project-document":
                            self.assertIn(self.LOCAL_PROOF, output)

    def test_client_displays_only_the_second_checkers_changed_proof(self):
        self.merge_conflicting_email_proofs(winner="second")
        self.assert_only_changed_proof_reaches_client()

    def test_client_displays_only_the_first_checkers_changed_proof_after_next_round(self):
        self.merge_conflicting_email_proofs(winner="first")
        (self.output / "second-check.json").rename(self.scratch / "removed-second-check.json")
        self.success("next-round")
        self.assertEqual(self.read_current()["project"]["checkers"], 1)
        self.assert_only_changed_proof_reaches_client()
