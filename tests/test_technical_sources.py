"""Exercise the technical document's source boundaries through the CLI."""

import importlib.util
import unittest

from checkflow_case import snapshot
from test_project_document import DocumentCase, DocumentHtml, normalize


@unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is unavailable for drawing tests.")
class TechnicalSourceTests(DocumentCase):
    def technical_html(self):
        self.success("document")
        return DocumentHtml((self.output / "technical-document.html").read_text(encoding="utf-8"))

    def test_kept_changes_precede_and_qualify_approved_technical_text(self):
        self.clean()
        check = self.read_current()
        extra = "The tool includes a printed order count."
        check["changes"].append({
            "id": "C3", "kind": "extra", "what": extra, "decision": "keep", "done": True,
        })
        check["changes"].append({
            "id": "C4", "kind": "different", "point": "M4",
            "what": "The cut-off is 17:00.", "decision": "keep", "done": True,
        })
        next(point for point in check["points"] if point["id"] == "M4")["mark"] = "changed"
        self.write_current(check)
        tools_quote = "The email and cancellation settings follow C1 and M4."
        support_quote = "The email address is used for support requests."
        trd = self.project / "docs/trd.md"
        trd.write_text(trd.read_text(encoding="utf-8").replace(
            "- Run on the bakery's computer.",
            f"- Run on the bakery's computer.\n- {tools_quote}",
        ).replace(
            "- An email service sends one notice per order.",
            f"- An email service sends one notice per order.\n- {support_quote}",
        ), encoding="utf-8")
        document = self.technical_html()
        architecture = normalize(" ".join(document.sections[2]))
        approved = "The bakery owner gets an email for every new order."
        built = "Each new order writes a notice to messages.txt."
        for expected in ("Kept changes", "C1 M3", approved, built, "C3",
                         "No approved point is recorded.", extra, "C4 M4", "The cut-off is 17:00."):
            self.assertIn(expected, architecture)
        self.assertNotIn("C2", architecture)
        note = "See kept change C1 in section 2."
        self.assertIn(f"{tools_quote} {note} See kept change C4 in section 2.", architecture)
        self.assertNotIn(tools_quote, normalize(" ".join(document.sections[1])))
        services = normalize(" ".join(document.sections[7]))
        self.assertIn(support_quote, document.sections[7])
        for quoted in ("An email service sends one notice per order.",
                       "The email service receives the order reference and pickup date."):
            self.assertIn(f"{quoted} {note}", services)
        body = normalize(" ".join(document.body))
        self.assertLess(body.index(built), body.index(note))
        self.assertNotIn("See kept change C1", normalize(" ".join(document.sections[4])))

    def test_unapproved_document_is_identified_as_unused_and_supplies_no_text(self):
        self.clean()
        path = self.project / "docs/security.md"
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace("Approved", "Draft", 1) + "\n- UNUSED_DRAFT_SETTING\n",
                        encoding="utf-8")
        self.success("next-round")
        document = self.technical_html()
        body = normalize(" ".join(document.body))
        self.assertIn("Unapproved document, not used: docs/security.md", body)
        self.assertNotIn("UNUSED_DRAFT_SETTING", body)
        self.assertNotIn("Anyone using the bakery computer can open the tool.", body)
        self.assertIn("No source is recorded.", normalize(" ".join(document.sections[6])))

    def test_install_section_reports_no_source_without_readme_or_approved_running_text(self):
        self.clean()
        (self.project / "README.md").rename(self.scratch / "bakery-readme.md")
        handover = self.project / "docs/handover.md"
        handover.write_text(handover.read_text(encoding="utf-8").replace(
            "- The bakery owner starts it from the terminal.\n", "",
        ), encoding="utf-8")
        document = self.technical_html()
        self.assertEqual(normalize(" ".join(document.sections[4])),
                         "4. Install and run No source is recorded.")

    def test_settings_output_uses_names_and_ignores_value_shaped_tokens(self):
        self.clean()
        (self.project / ".env.example").write_text(
            "CITY_MODE=LOCAL_VALUE_763745\nexport DISPLAY_NICKNAME='EXAMPLE_73Y8XP'\n"
            "# IGNORED=comment\n"
            'MULTILINE_SETTING="first line\nVALUE_SHAPED_NAME=next line"\nLAST_SETTING=end\n',
            encoding="utf-8",
        )
        trd = self.project / "docs/trd.md"
        trd.write_text(trd.read_text(encoding="utf-8") + "\n## Settings\n"
                       '- "DOC_REPORT_MODE": "DOC_VALUE_72N8YP"\n'
                       "- Use `DOC_LOG_LEVEL` for reporting.\n",
                       encoding="utf-8")
        security = self.project / "docs/security.md"
        security.write_text(security.read_text(encoding="utf-8").replace(
            "- Keep the mail settings outside the code.",
            "- Keep the mail settings outside the code.\n- **SERVICE_MAPPER:** OTHER_VALUE_D90K36",
        ), encoding="utf-8")
        document = self.technical_html()
        settings = normalize(" ".join(document.sections[5]))
        for name in ("CITY_MODE", "DISPLAY_NICKNAME", "DOC_REPORT_MODE",
                     "DOC_LOG_LEVEL", "SERVICE_MAPPER", "MULTILINE_SETTING", "LAST_SETTING"):
            self.assertIn(name, settings)
        for raw in snapshot(self.output).values():
            if isinstance(raw, bytes):
                for excluded in (b"LOCAL_VALUE_763745", b"EXAMPLE_73Y8XP", b"DOC_VALUE_72N8YP",
                                 b"OTHER_VALUE_D90K36", b"IGNORED", b"VALUE_SHAPED_NAME"):
                    self.assertNotIn(excluded, raw)

    def test_data_example_column_is_omitted_before_content_is_guarded(self):
        self.clean()
        secret = self.planted_key()
        data = self.project / "docs/data.md"
        data.write_text(data.read_text(encoding="utf-8").replace(
            "| bread | Bread name | sourdough | – |",
            f"| bread | Bread name | {secret} | important |",
        ), encoding="utf-8")
        document = self.technical_html()
        data_section = normalize(" ".join(document.sections[3]))
        self.assertIn("column holds mark", data_section.casefold())
        self.assertIn("bread Bread name important", data_section)
        self.assertNotIn("Example", data_section)
        self.assertNotIn(secret, normalize(" ".join(document.body)))
