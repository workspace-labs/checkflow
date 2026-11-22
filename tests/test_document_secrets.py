"""Check that document commands keep credential-bearing inputs out of delivery."""

import importlib.util
import json
import shutil
import unittest

from checkflow_case import FIXTURES, snapshot
from test_project_document import DocumentCase, DocumentHtml


BEARER = "sk_live_ABC" + "def1234567890"
PASSWORD = "hunter" + "2secret"


class DocumentSecretTests(DocumentCase):
    def refusal_at(self, path, number, value):
        message = self.refuse("document", path, f"line {number}.")
        self.assertTrue(value not in message, "A credential was echoed in the refusal.")

    def test_approved_trd_text_is_refused_at_its_own_line(self):
        self.clean()
        path = self.project / "docs/trd.md"
        original = path.read_text(encoding="utf-8")
        anchor = "- An email service sends one notice per order."
        number = original.splitlines().index(anchor) + 1
        for label, content, value in (
            ("authorization scheme", f"Authorization: Basic {BEARER}", BEARER),
            ("bearer header", f'curl -H "Bearer {BEARER}"', BEARER),
            ("lowercase setting", f"mail_password={PASSWORD}", PASSWORD),
            ("long option", f'--mail-password "{PASSWORD}"', PASSWORD),
        ):
            with self.subTest(label=label):
                path.write_text(original.replace(anchor, f"{anchor}\n  Use `{content}`."), encoding="utf-8")
                self.refusal_at("docs/trd.md", number + 1, value)

    def test_project_summary_refuses_credentials_without_copying_the_line(self):
        self.clean()
        path = self.project / "docs/prd.md"
        anchor = "A small bread menu and pickup order tool."
        original = path.read_text(encoding="utf-8")
        number = next(i for i, line in enumerate(original.splitlines(), 1) if anchor in line)
        path.write_text(original.replace(anchor, f"{anchor} Connect to https://admin:{PASSWORD}@db.example/"),
                        encoding="utf-8")
        self.refusal_at("docs/prd.md", number, PASSWORD)

    def test_json_credentials_report_the_actual_file_and_line(self):
        self.clean()
        for relative, update in (
            ("docs/checkflow/check.json", lambda obj: obj["project"].update(client=f"Bearer {BEARER}")),
            ("docs/checkflow/first-page.json", lambda obj: obj.update(prepared_by=f"Bearer {BEARER}")),
        ):
            with self.subTest(file=relative):
                path = self.project / relative
                original = path.read_text(encoding="utf-8")
                data = json.loads(original)
                update(data)
                # Emit one credential character as an ordinary JSON Unicode escape.
                content = json.dumps(data, ensure_ascii=False, indent=2).replace(BEARER, "\\u0073" + BEARER[1:])
                path.write_text(content, encoding="utf-8")
                number = next(i for i, line in enumerate(content.splitlines(), 1) if "Bearer " in line)
                self.refusal_at(relative, number, BEARER)
                path.write_text(original, encoding="utf-8")

    def test_translation_text_is_checked_before_drawing(self):
        self.clean()
        self.choose("both")
        self.success("translate", flags=("--language", "ar"))
        relative = "docs/checkflow/translation-ar.json"
        path = self.project / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        data["rows"][0]["text"] = f"Bearer: {BEARER}"
        content = json.dumps(data, ensure_ascii=False, indent=2)
        path.write_text(content, encoding="utf-8")
        number = next(i for i, line in enumerate(content.splitlines(), 1) if "Bearer:" in line)
        self.refusal_at(relative, number, BEARER)

    def test_escaped_line_break_does_not_hide_an_option_value_in_check_data(self):
        self.clean()
        relative = "docs/checkflow/check.json"
        path = self.project / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        data["points"][0]["proof"] = f"Tested with --password\n{PASSWORD}"
        content = json.dumps(data, ensure_ascii=False, indent=2)
        path.write_text(content, encoding="utf-8")
        number = next(i for i, line in enumerate(content.splitlines(), 1) if "--password" in line)
        self.refusal_at(relative, number, PASSWORD)


@unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is required to draw documents.")
@unittest.skipUnless(shutil.which("pdftotext"), "Poppler is required to inspect delivery PDFs.")
class ReadmeDeliveryTests(DocumentCase):
    def both_languages(self):
        self.choose("both")
        self.success("translate", flags=("--language", "ar"))

    def confirm_arabic(self):
        shutil.copyfile(FIXTURES / "corner-bakery-translation-ar.json", self.output / "translation-ar.json")
        self.success("confirm-translation", flags=("--language", "ar"))

    def test_readme_command_prose_and_code_span_stay_out_of_all_outputs(self):
        self.clean(choose=False)
        command, prose, code_span = "readmecommandmarker", "readmeprosemarker", "readmespanmarker"
        markers = (command, prose, code_span)
        with (self.project / "README.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\n```sh\npython3 bakery.py {command}\n```\n\n"
                         f"Note {prose}. Run `python3 bakery.py {code_span}`.\n")

        self.both_languages()
        draft = (self.output / "translation-ar.json").read_text(encoding="utf-8")
        for marker in markers:
            self.assertTrue(marker not in draft, "README text reached the translation draft.")
        self.confirm_arabic()
        run = self.success("document")
        self.assertTrue(all(marker not in run.stdout + run.stderr for marker in markers),
                        "README text reached the command output.")

        files = snapshot(self.output)
        expected_documents = {f"{stem}{suffix}.{extension}"
                              for stem in ("project-document", "technical-document")
                              for suffix in ("", "-ar") for extension in ("html", "pdf")}
        self.assertTrue(expected_documents.issubset(files))
        for name, raw in files.items():
            if isinstance(raw, bytes):
                self.assertTrue(all(marker.encode() not in raw for marker in markers),
                                f"README text reached {name}.")
            if name.endswith(".pdf"):
                text = "\n".join(self.pdf_pages(name[:-4]))
                self.assertTrue(all(marker not in text for marker in markers),
                                f"README text is visible in {name}.")

    def test_section_four_points_to_readme_only_when_it_exists_in_both_languages(self):
        self.clean(choose=False)
        self.both_languages()
        self.confirm_arabic()
        sections = (
            ("", ("4. Install and run", "The bakery owner starts it from the terminal."),
             "The commands to install and run the project are in README.md."),
            ("-ar", ("4. التثبيت والتشغيل", "يشغّل صاحب المخبز الأداة من الطرفية."),
             "أوامر تثبيت المشروع وتشغيله موجودة في ملف README.md."),
        )

        for has_readme in (True, False):
            with self.subTest(has_readme=has_readme):
                if not has_readme:
                    (self.project / "README.md").rename(self.scratch / "bakery-readme.md")
                self.success("document")
                for suffix, approved, pointer in sections:
                    html = (self.output / f"technical-document{suffix}.html").read_text(encoding="utf-8")
                    # The RTL renderer splits the number and filename into inline bidi spans.
                    section = "".join(DocumentHtml(html).sections[4])
                    expected = "".join((*approved, pointer) if has_readme else approved)
                    self.assertTrue(section == expected, f"Unexpected section 4 text in {suffix or 'English'}.")
