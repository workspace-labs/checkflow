"""Check native Arabic and translated English from Arabic-approved project files."""

import importlib.util
import json
import re
import shutil
import unittest

from test_project_document import DocumentCase, DocumentHtml, normalize


ARABIC_PRD = """# متطلبات المنتج: دفتر المواعيد
> الإصدار 1 · معتمد 2026-11-22

## ما هو
أداة بسيطة لجدولة المواعيد.

## لماذا
يعرف صاحب المشروع المواعيد القادمة.

## ما يجب أن يفعله
- **M1.** يسجّل صاحب المشروع موعدًا.

## الافتراضات والمخاطر
- يعتمد المشروع على ساعة الحاسوب.
"""
ARABIC_TRD = """# الوثيقة الفنية: دفتر المواعيد
> الإصدار 1 · معتمد 2026-11-22

## الواجهة
- تُعرض المواعيد في قائمة.

## أين يعمل
- يعمل على حاسوب صاحب المشروع.
"""
ARABIC_HANDOVER = """# التسليم: دفتر المواعيد
> الإصدار 1 · معتمد 2026-11-22

## ما يُسلَّم
- يتسلّم العميل دليل التشغيل.

## تشغيله
- يفتح صاحب المشروع دفتر المواعيد.
"""
ENGLISH = {
    "دفتر المواعيد": "Appointment Book",
    "صاحب المشروع": "The project owner",
    "منيرة سالم": "Munira Salim",
    "أداة بسيطة لجدولة المواعيد.": "A simple appointment scheduling tool.",
    "يعرف صاحب المشروع المواعيد القادمة.": "The project owner knows the upcoming appointments.",
    "يسجّل صاحب المشروع موعدًا.": "The project owner records an appointment.",
    "ظهر الموعد الجديد في القائمة.": "The new appointment appeared in the list.",
    "يتسلّم العميل دليل التشغيل.": "The client receives the operating guide.",
    "استلم العميل دليل التشغيل.": "The client received the operating guide.",
    "يفتح صاحب المشروع دفتر المواعيد.": "The project owner opens the appointment book.",
    "تُعرض المواعيد في قائمة.": "Appointments appear in a list.",
    "يعمل على حاسوب صاحب المشروع.": "It runs on the project owner's computer.",
    "يعتمد المشروع على ساعة الحاسوب.": "The project depends on the computer clock.",
}
FILES = (
    "project-document", "technical-document", "project-document-ar", "technical-document-ar",
)


class ReverseTranslationTests(DocumentCase):
    def approved_arabic(self):
        self.prd.parent.mkdir()
        self.prd.write_text(ARABIC_PRD, encoding="utf-8")
        for name, text in (("trd.md", ARABIC_TRD), ("handover.md", ARABIC_HANDOVER)):
            (self.prd.parent / name).write_text(text, encoding="utf-8")
        self.success("start")
        check = self.read_current()
        proofs = {"M1": "ظهر الموعد الجديد في القائمة.", "H1": "استلم العميل دليل التشغيل."}
        self.assertEqual([point["id"] for point in check["points"]], list(proofs))
        for point in check["points"]:
            point.update(mark="covered", proof=proofs[point["id"]])
        for row in check["checks"]:
            row.update(result="pass", reason="جرى التحقق.")
        check["dates"] = [
            {"id": f"D{index}", "kind": kind, "date": day, "confirmed": True, "source": "المالك"}
            for index, (kind, day) in enumerate((
                ("start", "2026-11-22"), ("planned end", "2026-11-24"), ("real end", "2026-11-24"),
            ), 1)
        ]
        self.write_current(check)

    def choose_arabic_details(self, language):
        self.success("choose", flags=("--client", "صاحب المشروع", "--prepared-by", "منيرة سالم",
                                      "--language", language))

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "ReportLab is required to draw both documents.")
    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler pdftotext is required to read rendered PDF text.")
    def test_arabic_approved_draws_native_arabic_and_confirmed_english(self):
        self.approved_arabic()
        self.choose_arabic_details("ar")
        self.success("document", offline=True)
        native_notice = "هذه الوثيقة ترجمة"
        for name in FILES[2:]:
            source = (self.output / f"{name}.html").read_text(encoding="utf-8")
            self.assertIn('lang="ar" dir="rtl"', source)
            self.assertNotIn(native_notice, source)
            self.assertIn("دفتر المواعيد", source)
            self.assertIn("أداة بسيطة لجدولة المواعيد.", source)
        self.assertFalse((self.output / "project-document.html").exists())

        self.choose_arabic_details("both")
        self.refuse("document", "translation-en.json", "missing")
        self.success("translate", flags=("--language", "en"), offline=True)
        path = self.output / "translation-en.json"
        draft = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(draft["confirmed"])
        self.assertEqual({row["source"] for row in draft["rows"]}, set(ENGLISH))
        for row in draft["rows"]:
            row["text"] = ENGLISH[row["source"]]
        path.write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
        self.refuse("document", "confirm")
        self.success("confirm-translation", flags=("--language", "en"), offline=True)
        self.success("document", offline=True)
        self.assertEqual(
            {path.name for path in self.output.glob("*-document*")},
            {f"{name}.{extension}" for name in FILES for extension in ("pdf", "html")},
        )
        for name in FILES[:2]:
            source = (self.output / f"{name}.html").read_text(encoding="utf-8")
            self.assertIn('lang="en" dir="ltr"', source)
            html_text = normalize(" ".join(DocumentHtml(source).body))
            pdf_text = normalize(" ".join(self.pdf_pages(name)))
            for text in (html_text, pdf_text):
                self.assertNotRegex(text, r"[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]")
                self.assertIn("This is a translation. The approved documents are the official source.", text)
                self.assertIn("Appointment Book", text)
        technical = (self.output / "technical-document.html").read_text(encoding="utf-8")
        self.assertIn("Appointments appear in a list.", technical)
        self.assertTrue(re.search(r"12\. Known limits", technical))
