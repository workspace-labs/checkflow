from checkflow_case import CheckflowCase


class SecretGuardTests(CheckflowCase):
    def test_ordinary_password_word_does_not_block_the_bakery(self):
        self.assert_bakery_passes_with_setting("DB_PASSWORD=bakery")

    def test_single_letter_key_does_not_block_the_bakery(self):
        self.assert_bakery_passes_with_setting("API_KEY=a")

    def test_punctuation_does_not_hide_a_token_from_start(self):
        self.copy_bakery()
        value, line = self.put_punctuated_token_in_prd()
        self.assert_prd_refusal("start", value, line, value[:7], value[-7:])
        self.assertFalse(self.output.exists())

    def test_punctuation_does_not_hide_a_token_from_next_round(self):
        self.finished_answer()
        self.success("report")
        value, line = self.put_punctuated_token_in_prd()
        self.assert_prd_refusal("next-round", value, line, value[:7], value[-7:])
        self.assertFalse((self.output / "check.round-1.json").exists())

    def test_explicit_word_password_assignment_in_prd_is_refused(self):
        self.copy_bakery()
        assignment = "DB_PASSWORD=bakery"
        self.set_env(assignment)
        line = self.append_to_m1(f" The setting is `{assignment}`.")
        self.assert_prd_refusal("start", assignment, line, "bakery")

    def test_explicit_single_letter_key_assignment_in_prd_is_refused(self):
        self.finished_answer()
        assignment = "API_KEY=a"
        self.set_env(assignment)
        line = self.append_to_m1(f" The setting is `{assignment}`.")
        self.assert_prd_refusal("next-round", assignment, line)

    def test_word_inside_a_longer_setting_value_is_not_a_match(self):
        self.copy_bakery()
        self.set_env("DB_PASSWORD=bakery")
        self.append_to_m1(" This example compares DB_PASSWORD=bakery.example with OTHER_DB_PASSWORD=bakery.")
        self.success("start")

    def test_quoted_short_value_beside_a_named_field_is_refused(self):
        self.copy_bakery()
        self.set_env("API_KEY=a")
        line = self.append_to_m1(' The field is **API_KEY**: "a".')
        self.assert_prd_refusal("start", 'API_KEY**: "a"', line)

    def test_setting_label_followed_by_ordinary_prose_is_not_a_match(self):
        self.copy_bakery()
        self.set_env("API_KEY=a")
        self.append_to_m1(" Use API_KEY: a value from the project settings.")
        self.success("start")

    def test_token_copied_into_proof_cannot_reach_a_report(self):
        content = self.finished_answer()
        self.success("report")
        value = "tok_9f8e7d6c5b4a"
        self.set_env(f"API_KEY={value}")
        content["points"][0]["proof"] = f"Displayed the value ({value})."
        self.write_current(content)
        for command in ("check", "report"):
            with self.subTest(command=command):
                message = self.refusal(command, "secret")
                self.assertNotIn(value, message)
                self.assertNotIn(value[:7], message)
                self.assertNotIn(value[-7:], message)

    def test_explicit_word_password_assignment_in_proof_is_refused(self):
        content = self.finished_answer()
        self.success("report")
        assignment = "DB_PASSWORD=bakery"
        self.set_env(assignment)
        content["points"][0]["proof"] = f"Displayed the setting `{assignment}`."
        self.write_current(content)
        for command in ("check", "report"):
            with self.subTest(command=command):
                message = self.refusal(command, "secret")
                self.assertNotIn(assignment, message)
                self.assertNotIn("bakery", message)

    def assert_bakery_passes_with_setting(self, assignment):
        self.set_env(assignment)
        self.finished_answer()
        self.success("check")
        self.success("report")
        round_one = self.current.read_bytes()

        self.success("next-round")
        self.assertEqual((self.output / "check.round-1.json").read_bytes(), round_one)
        self.assertEqual(self.read_current()["project"]["round"], 2)
        self.success("check")
        self.success("report")
        self.assertIn("Round: 2", self.report.read_text(encoding="utf-8"))

    def set_env(self, assignment):
        (self.project / ".env").write_text(assignment + "\n", encoding="utf-8")

    def put_punctuated_token_in_prd(self):
        value = "tok_9f8e7d6c5b4a"
        self.set_env(f"API_KEY={value}")
        return value, self.append_to_m1(f" A value is ({value}), as shown.")

    def append_to_m1(self, suffix):
        lines = self.prd.read_text(encoding="utf-8").splitlines(keepends=True)
        for index, line in enumerate(lines):
            if line.startswith("- **M1.**"):
                lines[index] = line.rstrip("\n") + suffix + "\n"
                break
        else:
            self.fail("The sample PRD is missing M1")
        self.prd.write_text("".join(lines), encoding="utf-8")
        return index + 1

    def assert_prd_refusal(self, command, sensitive_text, line, *fragments):
        message = self.refusal(command, "docs/prd.md", f"line {line}", "replace", "approv", "again")
        for value in (sensitive_text, *fragments):
            self.assertNotIn(value, message)
