"""Verify the paired documents and translation commands through the public CLI."""

from collections import Counter
import importlib.util
import json
import re
import shutil
import subprocess
import unicodedata
import unittest

from checkflow_case import FIXTURES, NEEDS_POPPLER, POPPLER, snapshot
from clean_bakery import SECURITY_DETAIL
from test_project_document import CREDIT, SECTIONS, TITLE, DocumentCase, DocumentHtml, normalize


TECHNICAL_SECTIONS = (
    "What it is built with", "How it is put together", "The database",
    "Install and run", "The settings it needs", "Who can do what",
    "Outside services", "Backup and getting data back", "Watching it",
    "Updating it and going back", "Security status", "Known limits",
)


ARABIC_SECTIONS = (
    "الملخص", "ما طلبته وما تسلّمته", "ما تغيّر بعد موافقتك", "ما بقي خارج نطاق التنفيذ",
    "مواعيد المشروع", "كيف اختُبر المشروع", "ما تتسلّمه", "الخطوات التالية", "التوقيع والقبول",
)
ARABIC_TECHNICAL_SECTIONS = (
    "بماذا بُني المشروع", "كيف يتكوّن المشروع", "قاعدة البيانات", "التثبيت والتشغيل",
    "الإعدادات المطلوبة", "صلاحيات الوصول", "الخدمات الخارجية", "النسخ الاحتياطي واستعادة البيانات",
    "مراقبة التشغيل", "التحديث والرجوع إلى إصدار سابق", "الحالة الأمنية", "القيود المعروفة",
)
ARABIC_LATIN = set(
    "bakery.py test_bakery.py messages.txt README.md orders.json BAKERY_API_KEY P1 C1 "
    "M1 M2 M3 M4 M5 N1 W1 W2 L1 L2 H1 H2 Python pickup orders reference bread cancelled".split()
)
ARABIC_NAME = "مخبز الزاوية"
ARABIC_NOTICE = "هذه الوثيقة ترجمة. الوثائق المعتمدة هي المصدر الرسمي."
ENGLISH_NOTICE = "This is a translation. The approved documents are the official source."


def letters(text):
    return Counter(char for char in unicodedata.normalize("NFKC", text).casefold() if char.isalnum())


def arabic_letters(value):
    return any(char.isalpha() and "ARABIC" in unicodedata.name(char, "") for char in value)


@unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is required to draw both documents.")
@unittest.skipUnless(shutil.which("pdftotext"), "Poppler pdftotext is required to read rendered PDF text.")
class PairedDocumentsTests(DocumentCase):
    def test_technical_sections_use_approved_sources_and_keep_only_setting_names(self):
        self.clean()
        (self.project / ".env.example").write_text("export MAIL_SERVER=fixture_example_Y71g\n", encoding="utf-8")
        (self.project / ".env.local").write_text("MAIL_PASSWORD=fixture_local_N30m\n", encoding="utf-8")
        before = self.planted_key()
        self.success("document", offline=True)
        html = (self.output / "technical-document.html").read_text(encoding="utf-8")
        sections = DocumentHtml(html).sections
        self.assertEqual(len(sections), 12)
        for i, title in enumerate(TECHNICAL_SECTIONS, 1):
            self.assertTrue(normalize(" ".join(sections[i])).startswith(f"{i}. {title}"))
        settings = normalize(" ".join(sections[5]))
        for name in ("MAIL_SERVER", "BAKERY_API_KEY", "MAIL_PASSWORD"):
            self.assertIn(name, settings)
        all_text = normalize(" ".join(DocumentHtml(html).body))
        for text in ("The bakery owner starts it from the terminal.", SECURITY_DETAIL):
            self.assertIn(text, all_text)
        database = normalize(" ".join(sections[3]))
        self.assertIn("cancelled", database)
        self.assertNotIn("Example", database)
        self.assertNotIn("sourdough", database)
        for value in (before, "fixture_example_Y71g", "fixture_local_N30m"):
            for path, raw in snapshot(self.output).items():
                if isinstance(raw, bytes):
                    self.assertNotIn(value.encode(), raw, path)
            for name in ("project-document", "technical-document"):
                self.assertNotIn(value, "".join(self.pdf_pages(name)))

    def test_english_bakery_matches_build_two_snapshot(self):
        self.clean()
        pages, html, _ = self.render()
        cases = (
            ("project-document-en-baseline.txt", normalize(" ".join(DocumentHtml(html).body))),
            ("project-document-en-baseline-pdf.txt", normalize(" ".join(pages))),
        )
        for name, actual in cases:
            self.assertEqual(actual, (FIXTURES / name).read_text(encoding="utf-8").strip())

    def test_client_gets_one_count_and_technical_gets_problem_and_next_step(self):
        self.clean()
        self.maxDiff = None
        check = self.read_current()
        reason = "The owner will replace the device at the next service."
        detail = "The service device still needs an update."
        next_step = "Apply the supplier update."
        check["checks"][10]["result"] = "fail"
        check["problems"].append({
            "id": "P2", "group": check["checks"][10]["group"], "line": detail,
            "state": "still open", "next": next_step, "accepted": reason,
            "check": check["checks"][10]["check"],
        })
        self.write_current(check)
        self.success("document")
        client = normalize(" ".join(DocumentHtml(self.html_text()).body))
        status = "1 problem remains open. See the technical document."
        self.assertEqual(client.count(status), 1)
        for text in (detail, reason, next_step):
            self.assertNotIn(text, client)
        technical = normalize(" ".join(DocumentHtml(
            (self.output / "technical-document.html").read_text(encoding="utf-8")).body))
        for text in (detail, reason, next_step, "still open"):
            self.assertIn(text, technical)

    def test_both_refuses_before_writing_when_translation_is_missing(self):
        self.clean()
        self.choose("both")
        self.refuse("document", "translation-ar.json", "missing")


    @unittest.skipUnless(POPPLER, NEEDS_POPPLER)
    def test_both_draws_eight_language_isolated_files_with_matching_sections(self):
        self.clean()
        self.choose("both")
        language = ("--language", "ar")
        self.success("translate", flags=language)
        name = "corner-bakery-translation-ar.json"
        shutil.copyfile(FIXTURES / name, self.output / "translation-ar.json")
        self.success("confirm-translation", flags=language)
        self.success("document")
        stems = ("project-document", "technical-document")
        expected = {f"{stem}{suffix}.{ext}" for stem in stems for suffix in ("", "-ar")
                    for ext in ("pdf", "html")}
        self.assertEqual({path.name for path in self.output.iterdir()
                          if path.suffix in (".pdf", ".html")}, expected)

        for stem, en_title, ar_title, en_titles, ar_titles in (
            (stems[0], TITLE, "وثيقة تسليم المشروع", SECTIONS, ARABIC_SECTIONS),
            (stems[1], "Technical Document", "الوثيقة الفنية", TECHNICAL_SECTIONS, ARABIC_TECHNICAL_SECTIONS),
        ):
            for locale, title, headings in (("en", en_title, en_titles), ("ar", ar_title, ar_titles)):
                with self.subTest(stem=stem, locale=locale):
                    basename = stem + ("-ar" if locale == "ar" else "")
                    source = (self.output / f"{basename}.html").read_text(encoding="utf-8")
                    markup = DocumentHtml(source)
                    mode = "-layout" if locale == "ar" else "-raw"
                    pdf = subprocess.check_output(
                        ["pdftotext", "-enc", "UTF-8", mode, str(self.output / f"{basename}.pdf"), "-"],
                        encoding="utf-8", timeout=20,
                    )
                    body = normalize(" ".join(markup.body))
                    if locale == "en":
                        self.assertFalse(arabic_letters(body))
                        self.assertFalse(arabic_letters(pdf))
                        self.assertNotIn(ENGLISH_NOTICE, body)
                    else:
                        self.assertIn('lang="ar" dir="rtl"', source)
                        self.assertIn(ARABIC_NOTICE, body)
                        self.assertEqual(letters(pdf.split("\f")[0]) & letters(ARABIC_NOTICE),
                                         letters(ARABIC_NOTICE))
                        self.assertTrue(any("\ufe70" <= ch <= "\ufefc" for ch in pdf))
                        for text in (body, pdf):
                            tokens = re.findall(r"[A-Za-z][A-Za-z0-9_./-]*",
                                                text.replace(CREDIT, " "))
                            self.assertLessEqual({word.rstrip(".") for word in tokens}, ARABIC_LATIN)
                    self.compare_sections(pdf, markup, title, headings, locale)
                    self.assertEqual(pdf.count(CREDIT), 1)
                    self.assertIn(CREDIT, pdf.rstrip("\f").split("\f")[-1])

    def compare_sections(self, pdf, html, title, headings, language):
        self.assertEqual(list(html.sections), list(range(1, len(headings) + 1)))
        titles = {number: letters(f"{number}. {heading}") for number, heading in enumerate(headings, 1)}
        found = {}
        current = None
        project = ARABIC_NAME if language == "ar" else "Corner Bakery"
        chrome = "سري صفحة من" if language == "ar" else "Confidential Page of"
        pages = [page for page in pdf.split("\f") if page.strip()]
        for number, page in enumerate(pages[1:], 2):
            footer = letters(f"{title} {chrome} {number} {len(pages)}")
            for line in page.splitlines():
                plain = letters(line)
                if not plain or plain in (letters(CREDIT), letters(f"{project} {title}"), footer):
                    continue
                match = next((n for n, heading in titles.items() if plain == heading), None)
                if match:
                    current = match
                    self.assertNotIn(current, found)
                    found[current] = Counter()
                self.assertIsNotNone(current, line)
                found[current].update(plain)
        self.assertEqual(list(found), list(html.sections))
        # The PDF extractor walks mirrored columns in geometric order. Compare
        # each section's normalized letters and digits without assuming column order.
        for number in found:
            with self.subTest(section=number):
                self.assertEqual(found[number], letters(" ".join(html.sections[number])))


class TranslationCommandTests(DocumentCase):
    language = ("--language", "ar")

    def setUp(self):
        super().setUp()
        self.clean()
        self.choose("both")
        self.file = self.output / "translation-ar.json"
        self.success("translate", flags=self.language, offline=True)

    def translated_fixture(self):
        fixture = json.loads((FIXTURES / "corner-bakery-translation-ar.json").read_text(encoding="utf-8"))
        fixture["confirmed"] = False
        current = json.loads(self.file.read_text(encoding="utf-8"))
        self.assertEqual([row["source"] for row in fixture["rows"]],
                         [row["source"] for row in current["rows"]])
        return fixture

    def write_translation(self, content):
        self.file.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    def test_prepare_names_sources_and_starts_unconfirmed_with_empty_rows(self):
        content = json.loads(self.file.read_text(encoding="utf-8"))
        self.assertEqual(content["language"], "ar")
        self.assertIs(content["confirmed"], False)
        sources = [row["source"] for row in content["rows"]]
        self.assertEqual(len(sources), len(set(sources)))
        self.assertIn("A small bread menu and pickup order tool.", sources)
        self.assertIn(SECURITY_DETAIL, sources)
        self.assertTrue(all(row["text"] == "" for row in content["rows"]))
        self.refuse("document", "translation-ar.json", "empty")
        self.refuse("confirm-translation", "empty", flags=self.language)

    def test_confirmation_does_not_survive_a_source_change(self):
        fixture = self.translated_fixture()
        self.write_translation(fixture)
        self.refuse("document", "owner must confirm", "translation-ar.json")
        self.success("confirm-translation", flags=self.language)
        self.assertIs(json.loads(self.file.read_text(encoding="utf-8"))["confirmed"], True)
        self.success("translate", flags=self.language)
        self.assertIs(json.loads(self.file.read_text(encoding="utf-8"))["confirmed"], True)
        old = "A small bread menu and pickup order tool."
        new = "A bread menu for scheduling pickup orders."
        self.prd.write_text(self.prd.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        self.refuse("document", "source text changed", "translation-ar.json")
        self.refuse("confirm-translation", "source text changed", flags=self.language)
        self.success("translate", flags=self.language)
        updated = json.loads(self.file.read_text(encoding="utf-8"))
        self.assertIs(updated["confirmed"], False)
        previous = {row["source"]: row["text"] for row in fixture["rows"]}
        revised = {row["source"]: row["text"] for row in updated["rows"]}
        self.assertNotIn(old, revised)
        self.assertEqual(revised.pop(new), "")
        del previous[old]
        self.assertEqual(revised, previous)

    def test_translation_guard_refuses_a_known_value_in_either_column(self):
        original = json.loads(self.file.read_text(encoding="utf-8"))
        secret = self.planted_key()
        for field in ("source", "text"):
            with self.subTest(field=field):
                content = json.loads(json.dumps(original))
                content["rows"][0][field] = secret
                self.write_translation(content)
                self.assertNotIn(secret, self.refuse("document", "secret"))
                self.assertNotIn(secret, self.refuse("translate", "secret", flags=self.language))
                self.assertNotIn(secret, self.refuse("confirm-translation", "secret", flags=self.language))


    def test_english_prose_in_an_arabic_translation_is_refused(self):
        content = self.translated_fixture()
        row = next(row for row in content["rows"] if row["source"].startswith("A small bread menu"))
        row["text"] = row["source"]
        content["confirmed"] = True
        self.write_translation(content)
        self.refuse("document", "still in the source language")
        self.refuse("confirm-translation", "still in the source language", flags=self.language)
