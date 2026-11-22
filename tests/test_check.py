from checkflow_case import CheckflowCase


class CheckTests(CheckflowCase):
    def test_finished_bakery_answer_passes(self):
        self.finished_answer()
        result = self.success("check")
        self.assertEqual(result.stdout, "Check complete.\n")
        self.assertEqual(result.stderr, "")

    def test_unknown_field_is_named(self):
        content = self.finished_answer()
        content["project"]["release"] = "later"
        self.write_current(content)
        self.refusal("check", "release")

    def test_missing_required_field_is_named(self):
        content = self.finished_answer()
        del content["project"]["client"]
        self.write_current(content)
        self.refusal("check", "client")

    def test_result_outside_allowed_list_is_refused(self):
        content = self.finished_answer()
        content["checks"][0]["result"] = "unknown"
        self.write_current(content)
        self.refusal("check", "result")

    def test_missing_mark_is_refused(self):
        content = self.finished_answer()
        content["points"][0]["mark"] = ""
        self.write_current(content)
        self.refusal("check", "mark")

    def test_partly_point_requires_a_gap(self):
        content = self.finished_answer()
        point = next(row for row in content["points"] if row["id"] == "M5")
        point["gap"] = ""
        self.write_current(content)
        self.refusal("check", "M5", "gap")
        del point["gap"]
        self.write_current(content)
        self.refusal("check", "M5", "gap")

    def test_gap_is_refused_on_other_marks(self):
        content = self.finished_answer()
        for point in (row for row in content["points"] if row["id"] in {"M1", "M3", "M4"}):
            with self.subTest(mark=point["mark"]):
                point["gap"] = "wrong"
                self.write_current(content)
                self.refusal("check", point["id"], "gap")
                point["gap"] = ""

    def test_unknown_gap_is_refused(self):
        content = self.finished_answer()
        point = next(row for row in content["points"] if row["id"] == "W1")
        for unknown in ("maybe", " "):
            with self.subTest(gap=unknown):
                point["gap"] = unknown
                self.write_current(content)
                self.refusal("check", "W1", "gap")

    def test_gap_must_be_a_string(self):
        content = self.finished_answer()
        content["points"][0]["gap"] = None
        self.write_current(content)
        self.refusal("check", "gap")

    def test_old_nonpartly_point_without_gap_still_validates(self):
        content = self.finished_answer()
        for point in content["points"]:
            if point["mark"] != "partly":
                del point["gap"]
        self.write_current(content)
        self.success("check")

    def test_missing_proof_is_refused(self):
        content = self.finished_answer()
        content["points"][0]["proof"] = ""
        self.write_current(content)
        self.refusal("check", "proof")

    def test_missing_check_result_is_refused(self):
        content = self.finished_answer()
        content["checks"][0]["result"] = ""
        self.write_current(content)
        self.refusal("check", "result")

    def test_missing_check_reason_is_refused(self):
        content = self.finished_answer()
        content["checks"][0]["reason"] = ""
        self.write_current(content)
        self.refusal("check", "reason")

    def test_dropped_point_is_refused(self):
        content = self.finished_answer()
        del content["points"][0]
        self.write_current(content)
        self.refusal("check", "M1")

    def test_repeated_point_is_refused(self):
        content = self.finished_answer()
        content["points"].append(content["points"][0].copy())
        self.write_current(content)
        self.refusal("check", "M1")

    def test_dropped_check_is_refused(self):
        content = self.finished_answer()
        removed = content["checks"].pop()
        self.write_current(content)
        self.refusal("check", removed["group"])

    def test_changed_point_without_change_row_is_refused(self):
        content = self.finished_answer()
        content["changes"] = [row for row in content["changes"] if row.get("point") != "M3"]
        self.write_current(content)
        self.refusal("check", "M3", "change")

    def test_change_linking_to_unknown_point_is_refused(self):
        content = self.finished_answer()
        extra = next(row for row in content["changes"] if row["kind"] == "extra")
        extra["point"] = "M999"
        self.write_current(content)
        self.refusal("check", extra["id"], "point")

    def test_problem_line_with_fence_is_refused(self):
        content = self.finished_answer()
        content["problems"][0]["line"] = "``` fenced example ```"
        self.write_current(content)
        self.refusal("check", "line")

    def test_problem_line_over_200_characters_is_refused(self):
        content = self.finished_answer()
        content["problems"][0]["line"] = "x" * 201
        self.write_current(content)
        self.refusal("check", "line", "200")

    def test_document_edit_after_start_names_next_round(self):
        content = self.finished_answer()
        old = content["points"][0]["text"]
        new = old.replace("bread", "pastry")
        self.assertNotEqual(old, new)
        document = self.prd.read_text(encoding="utf-8")
        self.prd.write_text(document.replace(old, new, 1), encoding="utf-8")
        self.refusal("check", "M1", "next-round")
