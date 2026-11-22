"""Exercise the client-document commands through the public CLI."""

import importlib.util
import json
import os
from html.parser import HTMLParser
import re
import shutil
import subprocess
import sys
import unicodedata
import unittest

from checkflow_case import CLI, ROOT, SKILL, CheckflowCase, snapshot
from clean_bakery import (
    CLIENT, DOCUMENT_DATE, DOCUMENT_VERSION, PREPARER, SECURITY_DETAIL, UNCONFIRMED,
    make_clean_bakery,
)


CREDIT = "Made with checkflow, a WorkSpace Labs skill"
TITLE = "Project Delivery Document"
DOCUMENT_DETAILS = (
    "--prepared-by", PREPARER,
    "--version", DOCUMENT_VERSION,
    "--document-date", DOCUMENT_DATE,
)
SECTIONS = (
    "Summary",
    "What you asked for and what you got",
    "What changed since you approved it",
    "What was not built",
    "Project dates",
    "How it was tested",
    "What you receive",
    "What happens next",
    "Sign-off",
)
NETWORK_GUARD = """
from pathlib import Path
import runpy
import sys

def block_network(event, args):
    if event.startswith("socket."):
        raise AssertionError("Network access attempted.")

sys.addaudithook(block_network)
script = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
runpy.run_path(script, run_name="__main__")
"""


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).replace("\u00ad", "").split())


class DocumentHtml(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.section = None
        self.sections = {}
        self.headers = {}
        self.header = False
        self.link = None
        self.contents = {}
        self.in_body = False
        self.body = []
        self.feed(html)

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == "body":
            self.in_body = True
        elif tag == "section" and (section := re.fullmatch(r"section-(\d+)", attrs.get("id", ""))):
            self.section = int(section[1])
            self.sections[self.section] = []
            self.headers[self.section] = []
        elif tag == "thead":
            self.header = True
            self.headers[self.section].append([])
        elif tag == "a" and (link := re.fullmatch(r"#section-(\d+)", attrs.get("href", ""))):
            self.link = int(link[1])
            self.contents[self.link] = []

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False
        elif tag == "section":
            self.section = None
        elif tag == "thead":
            self.header = False
        elif tag == "a":
            self.link = None

    def handle_data(self, data):
        if self.in_body:
            self.body.append(data)
        if self.section is not None:
            self.sections[self.section].append(data)
        if self.header and self.section is not None:
            self.headers[self.section][-1].append(data)
        if self.link is not None:
            self.contents[self.link].append(data)


class DocumentCase(CheckflowCase):
    def run_tool(self, command, *, project=None, flags=(), offline=False):
        launcher = [sys.executable]
        if offline:
            launcher.extend(("-c", NETWORK_GUARD))
        return subprocess.run(
            [*launcher, str(CLI), command, str(project or self.project), *flags],
            cwd=ROOT,
            capture_output=True,
            encoding="utf-8",
            timeout=30,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": ""},
        )

    def refuse(self, command, *fragments, flags=()):
        before = snapshot(self.project)
        run = self.run_tool(command, flags=flags)
        self.assertNotEqual(run.returncode, 0)
        message = run.stdout + run.stderr
        self.assertRegex(message, r"^1\. [^\r\n]+\n\Z")
        self.assertNotIn("Traceback", message)
        for fragment in fragments:
            self.assertIn(fragment.lower(), message.lower())
        self.assertEqual(snapshot(self.project), before, "Refusal changed the project folder")
        return message

    def choose(self, language="en", *pieces):
        return self.success("choose", flags=("--language", language, "--client", CLIENT,
                                             *DOCUMENT_DETAILS, *pieces))

    def clean(self, design="bakery", extra_points=0, choose=True):
        make_clean_bakery(self.project, design=design, extra_points=extra_points)
        if choose:
            self.choose()

    def render(self):
        result = self.success("document")
        return self.pdf_pages("project-document"), self.html_text(), result.stdout

    def html_text(self):
        return (self.output / "project-document.html").read_text(encoding="utf-8")

    def pdf_pages(self, name):
        file = self.output / f"{name}.pdf"
        self.assertTrue(file.read_bytes().startswith(b"%PDF"))
        result = subprocess.run(
            ["pdftotext", "-raw", str(file), "-"], capture_output=True, encoding="utf-8",
            timeout=20, check=True,
        )
        return [page for page in result.stdout.split("\f") if page.strip()]

    def planted_key(self):
        env = (self.project / ".env").read_text(encoding="utf-8")
        return env.split("=", 1)[1].strip()


class FirstPageChoiceTests(DocumentCase):
    def test_start_and_report_print_one_plain_success_line_each(self):
        self.copy_bakery()
        start = self.success("start")
        self.assertRegex(start.stdout, r"^[A-Za-z][^\n]+\n$")
        self.assertEqual(start.stderr, "")
        make_clean_bakery(self.scratch / "finished")
        report = self.success("report", project=self.scratch / "finished")
        self.assertRegex(report.stdout, r"^[A-Za-z][^\n]+\n$")
        self.assertEqual(report.stderr, "")

    def test_choose_saves_first_page_and_project_language(self):
        self.start_bakery()
        self.choose("en", "--frame", "side", "--name-position", "start", "--details-style", "list",
                    "--details", "client,prepared-by", "--no-credit")
        saved = json.loads((self.output / "first-page.json").read_text(encoding="utf-8"))
        self.assertEqual(
            saved,
            {"frame": "side", "name_position": "start", "details_style": "list",
             "details": ["client", "prepared-by"], "credit": False,
             "prepared_by": PREPARER, "version": DOCUMENT_VERSION, "date": DOCUMENT_DATE},
        )
        self.assertEqual(self.read_current()["project"]["language"], "en")
        self.assertEqual(self.read_current()["project"]["client"], CLIENT)

        self.success("choose", flags=("--language", "en", "--client", CLIENT, "--credit"))
        after = json.loads((self.output / "first-page.json").read_text(encoding="utf-8"))
        self.assertEqual(after, {**saved, "credit": True})

    def test_choose_refuses_unknown_pieces_and_never_echoes_client_secret(self):
        self.clean(choose=False)
        key = self.planted_key()
        for flags in (
            ("--frame", key),
            ("--name-position", key),
            ("--details-style", key),
            ("--details", key),
            ("--prepared-by", key),
            ("--version", key),
            ("--document-date", key),
        ):
            with self.subTest(piece=flags[0]):
                result = self.refuse("choose", flags=("--language", "en", "--client", CLIENT, *flags))
                self.assertFalse(key in result, "A planted value appeared in a command refusal.")
        result = self.refuse("choose", "secret", flags=("--language", "en", "--client", key))
        self.assertFalse(key in result, "A planted value appeared in a command refusal.")

    def test_choose_refuses_obsolete_details_and_invalid_document_dates(self):
        self.start_bakery()
        base = ("--language", "en", "--client", CLIENT, "--prepared-by", PREPARER)
        for field in ("round", "verdict", "real-end"):
            with self.subTest(field=field):
                self.refuse("choose", flags=(*base, "--details", field))
        self.refuse("choose", "date", flags=(*base, "--document-date", "2027-02-30"))

    def test_legacy_cover_requires_a_preparer_and_keeps_its_layout_when_chosen_again(self):
        self.clean(choose=False)
        self.success("choose", flags=("--language", "en", "--client", CLIENT))
        path = self.output / "first-page.json"
        old = {"frame": "side", "name_position": "center", "details_style": "list",
               "details": ["client", "round", "verdict", "real-end"], "credit": False}
        path.write_text(json.dumps(old), encoding="utf-8")
        self.refuse("document", "preparer")

        self.success("choose", flags=("--language", "en", "--client", CLIENT,
                                      "--prepared-by", PREPARER))
        upgraded = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(upgraded, {
            **old, "details": ["client", "prepared-by", "version", "date", "status"],
            "prepared_by": PREPARER, "version": "", "date": "",
        })


@unittest.skipUnless(importlib.util.find_spec("reportlab"),
                     "ReportLab is required to draw the preview and document.")
@unittest.skipUnless(shutil.which("pdftotext"), "Poppler pdftotext is required to read rendered PDF text.")
class ProjectDocumentTests(DocumentCase):
    def test_preview_shows_c_first_and_uses_the_requested_change(self):
        self.clean()
        self.success("preview")
        pages = self.pdf_pages("first-page-preview")
        self.assertGreaterEqual(len(pages), 2)
        self.assertRegex(pages[0], r"(?i)\bC\b[^\n]*register")
        self.assertIn("Prepared for", pages[0])

        saved = (self.output / "first-page.json").read_bytes()
        self.success("preview", flags=("--frame", "register", "--details", "prepared-by"))
        changed = self.pdf_pages("first-page-preview")
        self.assertRegex(changed[0], r"(?i)\bC\b[^\n]*register")
        self.assertNotIn("Prepared for", changed[0])
        self.assertIn("Prepared by", changed[0])
        self.assertIn(PREPARER, changed[0])
        self.assertEqual((self.output / "first-page.json").read_bytes(), saved)

    def test_document_contains_confirmed_dates_and_only_kept_changes(self):
        self.clean()
        pages, html, _ = self.render()
        for content in ("\n".join(pages), html):
            with self.subTest(format="HTML" if content == html else "PDF"):
                for text in ("2026-11-30", "2026-12-18", "2027-01-02", "+6", "+9", CLIENT):
                    self.assertIn(text, content)
                self.assertNotIn(UNCONFIRMED, content)
                self.assertNotIn("The unrequested dark menu switch was removed.", content)
                self.assertNotIn(SECURITY_DETAIL, content)
                self.assertNotIn("30 days", content)
        dates = normalize(" ".join(DocumentHtml(html).sections[5]))
        self.assertRegex(dates, r"2026-12-18.+\+6.+\+9.+2027-01-02")
        changes = normalize(" ".join(DocumentHtml(html).sections[3]))
        self.assertIn("Each new order writes a notice to messages.txt.", changes)

    def test_document_refuses_without_choice_or_required_translation(self):
        self.clean(choose=False)
        self.refuse("document", "first page")
        for selected in ("ar", "both"):
            with self.subTest(language=selected):
                self.choose(selected)
                self.refuse("document", "translation-ar.json", "missing")

    def test_not_clean_document_refusal_preserves_existing_document(self):
        self.clean()
        self.render()
        content = self.read_current()
        content["points"][3]["mark"] = "missing"
        self.write_current(content)
        self.refuse("document", "Not clean")

    def test_date_refusals_name_missing_fields_and_do_not_write(self):
        self.clean()
        original = self.read_current()
        for row_index, field in ((2, "days_added"), (3, "days_added"), (5, "days_added"),
                                 (2, "asked_by"), (3, "reason"), (3, "what")):
            with self.subTest(row=row_index, field=field):
                content = self.read_current()
                row = content["dates"][row_index]
                row.pop(field)
                self.write_current(content)
                self.refuse("document", row["id"], field)
                self.write_current(original)
        self.assertFalse((self.output / "project-document.pdf").exists())
        self.assertFalse((self.output / "project-document.html").exists())

    def test_event_date_range_applies_only_when_confirmed(self):
        self.clean()
        content = self.read_current()
        row = content["dates"][5]
        row["date"] = "2030-01-01"
        self.write_current(content)

        pages, html, _ = self.render()
        for format_name, document in (("PDF", "\n".join(pages)), ("HTML", html)):
            with self.subTest(format=format_name):
                self.assertNotIn(row["date"], document)
                self.assertNotIn(UNCONFIRMED, document)

        row["confirmed"] = True
        self.write_current(content)
        self.refuse("document", "dates row 6 (D6)", row["date"], "outside the project dates")

    def test_date_refusals_report_both_end_dates_for_a_mismatch(self):
        self.clean()
        original = self.read_current()
        content = self.read_current()
        content["dates"][2]["days_added"] = 5
        self.write_current(content)
        self.refuse("document", "2027-01-01", "2027-01-02")
        original["dates"][0]["confirmed"] = False
        self.write_current(original)
        self.refuse("document", "start")

    def test_pdf_and_html_agree_section_by_section_with_real_page_numbers(self):
        self.clean()
        pages, source, _ = self.render()
        html = DocumentHtml(source)
        self.assertEqual(list(html.sections), list(range(1, 10)))
        self.assertEqual(list(html.contents), list(range(1, 10)))
        pdf_text = {number: [] for number in range(1, 10)}
        section = None
        for page_number, page in enumerate(pages, start=1):
            self.assertIn(TITLE.lower(), page.lower())
            self.assertIn("Confidential", page)
            self.assertIn(f"Page {page_number} of {len(pages)}", page)
            if page_number == 1:
                continue
            for line in page.splitlines():
                line = line.strip()
                if not line or self.page_chrome(line):
                    continue
                heading = re.fullmatch(r"(\d+)\. (.+)", line)
                if heading and heading[2] in SECTIONS:
                    section = int(heading[1])
                    self.assertEqual(heading[2], SECTIONS[section - 1])
                    item = normalize(" ".join(html.contents[section]))
                    self.assertRegex(item, rf"\b{page_number}$")
                    self.assertRegex(normalize(pages[0]), rf"{re.escape(heading[2])}\s+{page_number}\b")
                if section is not None:
                    pdf_text[section].append(line)
        for section, title in enumerate(SECTIONS, start=1):
            with self.subTest(section=title):
                # The PDF sets headers in uppercase directly. HTML does so through CSS.
                observed = normalize(" ".join(pdf_text[section])).casefold()
                expected = normalize(" ".join(html.sections[section])).casefold()
                for words in html.headers[section]:
                    header = normalize(" ".join(words)).casefold()
                    first, separator, rest = observed.partition(header)
                    observed = normalize(first + separator + rest.replace(header, " "))
                self.assertEqual(observed, expected)

    @staticmethod
    def page_chrome(line):
        lower = line.lower()
        return (
            lower in {TITLE.lower(), "confidential", CREDIT.lower()}
            or re.fullmatch(r"(?:project delivery document confidential )?page \d+ of \d+", lower)
            or re.fullmatch(r"(?:corner bakery )?[^\w]*project delivery document(?:[^\w]+confidential)?", lower)
        )

    def test_project_theme_and_both_contrast_fallbacks(self):
        for name in ("bakery", "neutral", "pale"):
            with self.subTest(design=name):
                target = self.scratch / name
                make_clean_bakery(target, design=name)
                self.success("choose", project=target, flags=("--language", "en", "--client", CLIENT,
                                                              *DOCUMENT_DETAILS))
                result = self.success("document", project=target)
                html = (target / "docs/checkflow/project-document.html").read_text(encoding="utf-8")
                colors = re.search(r"--main:\s*(#[a-f0-9]{6})", html, re.IGNORECASE)
                self.assertIsNotNone(colors)
                main = colors[1].upper()
                if name == "bakery":
                    self.assertEqual(main, "#783E22")
                    self.assertTrue(re.search(r"(?i)\bmonospace\b", html), "Expected a monospace font.")
                    self.assertTrue(re.search(r"(?:radius|corner)[^\n]*4px", html), "Expected 4px corners.")
                elif name == "neutral":
                    self.assertRegex(result.stdout, r"(?i)neutral")
                    self.assertNotEqual(main, "#783E22")
                else:
                    self.assertRegex(result.stdout, r"(?i)darken")
                    self.assertNotEqual(main, "#FFEECC")

    def test_html_is_self_contained_and_document_contains_no_key(self):
        self.clean()
        pages, html, notice = self.render()
        self.assertTrue(re.search(r"(?i)PDF[^<\n.]*official copy", html), "Missing official-copy notice.")
        self.assertFalse(re.search(r"(?i)<(?:script|img|picture|svg|canvas)\b", html), "Unexpected script or image.")
        self.assertFalse(re.search(r"(?i)(?:https?://|@import\b)", html), "Unexpected external reference.")
        key = self.planted_key()
        for file, raw in snapshot(self.output).items():
            if isinstance(raw, bytes):
                self.assertFalse(key.encode("utf-8") in raw, f"A planted value appeared in {file}.")
        self.assertFalse(key in "\n".join(pages) + notice, "A planted value appeared in document output.")

    def test_document_refuses_a_known_secret_found_in_approved_output_text(self):
        self.clean()
        key = self.planted_key()
        prd = self.prd.read_text(encoding="utf-8")
        self.prd.write_text(prd.replace("A small bread menu and pickup order tool.",
                                        f"A small bread menu and pickup order tool. ({key})"),
                            encoding="utf-8")
        result = self.refuse("document", "secret")
        self.assertFalse(key in result, "A planted value appeared in a command refusal.")

    def test_approved_cover_is_used_and_unchecking_credit_only_removes_credit(self):
        self.clean(choose=False)
        pieces = ("--frame", "side", "--name-position", "start",
                  "--details-style", "list", "--details", "prepared-by")
        self.choose("en", *pieces)
        pages, html, _ = self.render()
        self.assertNotIn("Prepared for", pages[0])
        self.assertIn("Prepared by", pages[0])
        self.assertTrue(re.search(r'(?is)<[^>]+class="[^"]*side[^"]*"', html), "Expected the side cover.")
        self.assertEqual(sum(page.count(CREDIT) for page in pages), 1)
        self.assertNotIn(CREDIT, "\n".join(pages[:-1]))
        self.assertIn(CREDIT, pages[-1])
        self.assertEqual(html.count(CREDIT), 1)

        self.success("choose", flags=("--language", "en", "--client", CLIENT, "--no-credit"))
        off, uncredited, _ = self.render()
        self.assertNotIn(CREDIT, uncredited)
        self.assertEqual([normalize(page.replace(CREDIT, "")) for page in pages], list(map(normalize, off)))
        self.assertEqual(normalize(" ".join(DocumentHtml(html).body).replace(CREDIT, "")),
                         normalize(" ".join(DocumentHtml(uncredited).body)))

    def test_long_table_repeats_header_and_never_splits_a_row(self):
        count = 65
        self.clean(extra_points=count)
        pages, _, _ = self.render()
        touched = set()
        for number in range(count):
            first = re.compile(rf"\bFirst marker{number:03d}\b")
            last = re.compile(rf"\bLast marker{number:03d}\b")
            start = [i for i, page in enumerate(pages) if first.search(normalize(page))]
            end = [i for i, page in enumerate(pages) if last.search(normalize(page))]
            self.assertEqual(len(start), 1, f"Long table lost or duplicated row {number}.")
            self.assertEqual(start, end, f"Long table split row {number} across pages.")
            touched.update(start)
        self.assertGreaterEqual(len(touched), 3)
        for page in touched:
            self.assertIn("WHERE TO SEE IT", normalize(pages[page]).upper())

    def test_document_commands_do_not_use_network_or_write_outside_output_folder(self):
        self.clean(choose=False)
        omitted = ("project/docs/checkflow",)
        before = snapshot(self.scratch, exclude=omitted)
        skill_before = snapshot(SKILL)
        self.success("choose", flags=("--language", "en", "--client", CLIENT, *DOCUMENT_DETAILS),
                     offline=True)
        self.success("preview", offline=True)
        self.success("document", offline=True)
        self.assertEqual(snapshot(self.scratch, exclude=omitted), before)
        self.assertEqual(snapshot(SKILL), skill_before)

    def test_signoff_shows_both_named_parties_with_three_fields_each(self):
        self.clean()
        pages, source, _ = self.render()
        last_page = normalize(pages[-1]).casefold().partition("9. sign-off")[2]
        signoff = normalize(" ".join(DocumentHtml(source).sections[9])).casefold()
        for text in (last_page, signoff):
            for expected in ("prepared by", PREPARER.casefold(), "accepted by", CLIENT.casefold()):
                self.assertIn(expected, text)
            for party in (text.partition("accepted by")[0], text.partition("accepted by")[2]):
                self.assertEqual(re.findall(r"\b(?:name|signature|date)\b", party),
                                 ["name", "signature", "date"])

    def test_document_refuses_when_the_saved_cover_lacks_a_preparer(self):
        self.clean(choose=False)
        self.success("choose", flags=("--language", "en", "--client", CLIENT))
        self.refuse("document", "preparer")

    def test_cover_shows_formal_details_and_no_internal_status_words(self):
        self.clean()
        pages, source, _ = self.render()
        html = DocumentHtml(source)
        pdf_text = normalize(" ".join(pages))
        html_text = normalize(" ".join(html.body))
        for text in (normalize(pages[0]), html_text):
            for detail in ("Prepared for", CLIENT, "Prepared by", PREPARER, "Version",
                           DOCUMENT_VERSION, "Date", DOCUMENT_DATE, "Status", "Final"):
                self.assertIn(detail, text)
        for text in (pdf_text, html_text):
            self.assertNotRegex(text, r"(?i)\b(?:round|verdict)\b")

        data = self.read_current()
        data["points"][3]["mark"] = "missing"
        self.write_current(data)
        self.success("preview")
        self.assertNotRegex(" ".join(self.pdf_pages("first-page-preview")), r"\bFinal\b")

    def test_cover_omits_unsupplied_version_and_document_date(self):
        self.clean(choose=False)
        self.success("choose", flags=("--language", "en", "--client", CLIENT,
                                      "--prepared-by", PREPARER))
        pages, source, _ = self.render()
        html_cover = source.partition("</header>")[0]
        for text in (pages[0], " ".join(DocumentHtml(html_cover).body)):
            self.assertNotRegex(text, r"(?i)\b(?:version|date)\b")
            self.assertIn("Final", text)

    def test_all_12_approved_point_rows_have_results_and_match_the_count(self):
        self.clean()
        pages, source, _ = self.render()
        html = DocumentHtml(source)
        sections = {k: normalize(" ".join(html.sections[k])) for k in (2, 4)}
        delivery_ids = "M1 M2 M3 M4 M5 W1 W2 L1 L2 H1 H2".split()
        pattern = r"\b(?:M[1-5]|N1|W[12]|L[12]|H[12])\b"
        pdf_body = normalize(" ".join(pages[1:]))
        self.assertCountEqual(re.findall(pattern, sections[2]), delivery_ids)
        self.assertEqual(re.findall(pattern, sections[4]), ["N1"])
        # M3 legitimately appears a second time as the reference in the kept-changes table.
        self.assertCountEqual(re.findall(pattern, pdf_body), [*delivery_ids, "N1", "M3"])
        html_cover = source.partition("</header>")[0]
        for cover in (pages[0], " ".join(DocumentHtml(html_cover).body)):
            count = re.search(r"(\d+) approved points", normalize(cover))
            self.assertIsNotNone(count)
            self.assertEqual(int(count[1]), 12)
            self.assertEqual(int(count[1]), sum(len(re.findall(pattern, s)) for s in sections.values()))
        badges = re.findall(r"\b(?:DELIVERED|CHANGED, APPROVED)\b", sections[2].upper())
        self.assertCountEqual(badges, ["DELIVERED"] * 10 + ["CHANGED, APPROVED"])
        self.assertRegex(sections[4], r"(?i)N1 .*\bLeft out as agreed\b")
        self.assertIn("Out of scope", sections[4])
        self.assertIn("Later", sections[4])
        self.assertNotIn("The check records proof", normalize(" ".join(html.sections[6])))

    def test_document_refuses_dates_outside_the_project_and_names_each_row(self):
        self.clean()
        self.render()
        original = self.read_current()
        cases = (
            (0, "2026-12-19", "D1"),  # After the planned end, before the real end.
            (0, "2027-03-01", "D1"),  # After both ends.
            (4, "2026-11-29", "D1"),  # Real end before the start, planned end after it.
            (2, "2026-11-29", "D3"),
            (2, "2030-01-01", "D3"),
            (3, "2026-11-29", "D4"),
            (3, "2030-01-01", "D4"),
        )
        for index, day, row_id in cases:
            with self.subTest(day=day, row=row_id):
                self.write_current(original)
                edited = self.read_current()
                edited["dates"][index]["date"] = day
                self.write_current(edited)
                self.refuse("document", row_id)

    def test_names_of_70_90_and_120_characters_draw_on_each_frame(self):
        self.clean()
        title = self.prd.read_text(encoding="utf-8")
        for length in (70, 90, 120):
            # A 120-character single word exercises a wrap without any natural breaking points.
            name = ("Corner Bakery International Services " * 4)[:length].ljust(length, "x")
            if length == 120:
                name = "InternationalBakeryX" * 6
            self.assertEqual(len(name), length)
            self.prd.write_text(title.replace("# PRD: Corner Bakery", f"# PRD: {name}", 1),
                                encoding="utf-8")
            data = self.read_current()
            data["project"]["name"] = name
            self.write_current(data)
            for frame in ("register", "band", "side"):
                with self.subTest(length=length, frame=frame):
                    self.choose("en", "--frame", frame)
                    pages, source, _ = self.render()
                    self.assertIn("".join(name.split()), "".join(normalize(pages[0]).split()))
                    self.assertIn(name, normalize(" ".join(DocumentHtml(source).body)))

    def test_oversized_cover_refusal_is_one_numbered_line_and_preserves_outputs(self):
        self.clean()
        self.render()
        prd = self.prd.read_text(encoding="utf-8")
        self.prd.write_text(
            prd.replace("A small bread menu and pickup order tool.",
                        "An ordinary description of the bakery service. " * 150, 1),
            encoding="utf-8",
        )
        self.refuse("document", "first-page", "available space")
