"""Exercise what the owner can preview and what the confirmation covers."""

import importlib.util
import json
import shutil
import unicodedata
import unittest

from checkflow_case import FIXTURES, NEEDS_POPPLER, POPPLER
from test_project_document import DocumentCase


class TranslationReviewTests(DocumentCase):
    language = ("--language", "ar")

    def fill_draft(self):
        path = self.output / "translation-ar.json"
        content = json.loads(path.read_text(encoding="utf-8"))
        fixture_path = FIXTURES / "corner-bakery-translation-ar.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        translated = {row["source"]: row["text"] for row in fixture["rows"]}
        for row in content["rows"]:
            row["text"] = translated[row["source"]]
        self.save(path, content)
        return path

    @staticmethod
    def save(path, content):
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is required to draw.")
    def test_delivery_requires_confirmation_again_after_editing_translated_words(self):
        self.clean()
        self.choose("both")
        self.success("translate", flags=self.language)
        path = self.fill_draft()
        self.success("confirm-translation", flags=self.language)
        approved = json.loads(path.read_text(encoding="utf-8"))
        self.save(path, approved)
        self.success("document")  # JSON formatting alone does not alter the approved words.
        edited = json.loads(path.read_text(encoding="utf-8"))
        row = next(row for row in edited["rows"] if row["source"] == "Corner Bakery")
        row["text"] = "مخبز الزاوية الجديد"
        self.save(path, edited)
        self.refuse("document", "owner must confirm", "translation-ar.json")
        self.success("translate", flags=self.language)
        self.assertFalse(json.loads(path.read_text(encoding="utf-8"))["confirmed"])
        self.refuse("document", "owner must confirm", "translation-ar.json")
        self.success("confirm-translation", flags=self.language)
        self.success("document")
        self.assertIn(row["text"], (self.output / "project-document-ar.html").read_text(encoding="utf-8"))

    def test_source_edits_and_old_confirmations_without_a_digest_are_refused(self):
        self.clean()
        self.choose("both")
        self.success("translate", flags=self.language)
        path = self.fill_draft()
        self.success("confirm-translation", flags=self.language)
        approved = json.loads(path.read_text(encoding="utf-8"))
        edited = json.loads(path.read_text(encoding="utf-8"))
        edited["rows"][0]["source"] += " changed"
        self.save(path, edited)
        self.refuse("document", "source text changed", "translation-ar.json")
        approved.pop("confirmed_digest", None)
        self.save(path, approved)
        self.refuse("document", "owner must confirm", "translation-ar.json")

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is required to draw.")
    @unittest.skipUnless(POPPLER, NEEDS_POPPLER)
    def test_unconfirmed_arabic_preview_before_choosing_does_not_publish_delivery(self):
        self.clean(choose=False)
        choice = self.output / "first-page.json"
        self.assertFalse(choice.exists())
        self.success("translate", flags=self.language)
        path = self.fill_draft()
        self.assertFalse(json.loads(path.read_text(encoding="utf-8"))["confirmed"])
        self.success("preview", flags=self.language)
        self.assertFalse(choice.exists())
        pages = self.pdf_pages("first-page-preview")
        self.assertEqual(len(pages), 3)
        for page, layout in zip(pages, ("الإطار", "الشريط", "الجانب")):
            display = unicodedata.normalize("NFKC", page)
            self.assertIn(layout, display.splitlines()[0])
            for word in ("مسودة", "مخبز", "الزاوية"):
                self.assertIn(word, display)
        self.assertEqual({item.name for item in self.output.glob("*.pdf")}, {"first-page-preview.pdf"})
        self.assertFalse(list(self.output.glob("*document*.html")))
        self.choose("both")
        self.success("translate", flags=self.language)
        self.fill_draft()
        self.refuse("document", "owner must confirm")

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is required to draw.")
    def test_draft_arabic_preview_fits_every_frame_after_choosing(self):
        self.clean()
        self.choose("both")
        self.success("translate", flags=self.language)
        self.fill_draft()
        for extra in (("--frame", "register"), ("--frame", "band"), ("--frame", "side"), ("--details", "")):
            with self.subTest(extra=extra):
                self.success("preview", flags=(*self.language, *extra))
                if POPPLER:
                    pages = self.pdf_pages("first-page-preview")
                    self.assertEqual(len(pages), 3)
                    for page in pages:
                        self.assertIn("مسودة", unicodedata.normalize("NFKC", page))
