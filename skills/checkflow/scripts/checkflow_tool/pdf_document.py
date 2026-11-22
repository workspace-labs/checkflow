"""Draw a paginated copy of the shared project document using ReportLab."""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, LongTable, PageBreak,
                                PageTemplate, Table, TableStyle)
from reportlab.platypus.doctemplate import LayoutError

from .document_language import load
from .document_theme import for_language
from .pdf_cover import CoverOverflow, HEIGHT, MARGIN, WIDTH, draw_cover
from .pdf_style import Badge, Heading, Signoff, Style, timeline
from .storage import Refusal


BODY_WIDTH = WIDTH - MARGIN * 2


class ProjectPDF(BaseDocTemplate):
    def __init__(self, output, page_start, page_end):
        super().__init__(output, pagesize=(WIDTH, HEIGHT), invariant=1,
                         allowSplitting=1, pageCompression=1)
        frame = Frame(MARGIN, 78, BODY_WIDTH, HEIGHT - 141, leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate("body", [frame], onPage=page_start,
                                           onPageEnd=page_end))
        self.headings = {}

    def afterFlowable(self, flowable):
        if isinstance(flowable, Heading):
            self.headings[flowable.number] = self.page


def table(block, style):
    width_total = sum(block.widths)
    columns = [BODY_WIDTH * fraction / width_total for fraction in block.widths]
    rows = [[style.label(style.caps(title), color=style.on_main, size=7.7,
                         align=TA_RIGHT if index in block.numeric else style.start)
             for index, title in enumerate(block.headers)]]
    for row in block.rows:
        rows.append([Badge(value, style) if index in block.badges else
                     style.text(value, size=8.6, align=TA_RIGHT if index in block.numeric else style.start)
                     for index, value in enumerate(row)])
    if style.rtl:
        columns.reverse()
        rows = [list(reversed(row)) for row in rows]
    cell_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), style.main),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), (colors.white, style.tint)),
        ("GRID", (0, 1), (-1, -1), 0.75, style.line),
        ("LINEBELOW", (0, -1), (-1, -1), 1.45, style.main),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT" if style.rtl else "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), max(5, style.space)),
        ("RIGHTPADDING", (0, 0), (-1, -1), max(5, style.space)),
        ("TOPPADDING", (0, 0), (-1, -1), max(4, style.space - 1)),
        ("BOTTOMPADDING", (0, 0), (-1, -1), max(4, style.space - 1)),
    ])
    grid = LongTable(rows, colWidths=columns, style=cell_style, repeatRows=1,
                     splitByRow=1, splitInRow=0)
    grid.spaceAfter = 7
    first_rows = Table(rows[:2], colWidths=columns, style=cell_style)
    minimum = first_rows.wrap(BODY_WIDTH, HEIGHT)[1]
    return grid, minimum


def content(block, style):
    if block.kind == "table":
        return [table(block, style)[0]]
    if block.kind == "timeline":
        return timeline(block.rows, style)
    if block.kind == "signoff":
        return [Signoff(block.rows, block.headers, style)]
    if block.kind == "subheading":
        labels = [style.label(value, size=9.5) for (value,) in block.rows]
        for label in labels:
            label.spaceBefore = 5
            label.spaceAfter = 6
            label.keepWithNext = True
        return labels
    lines = []
    for (value,) in block.rows:
        text = style.text(value, face=style.bold if block.kind == "callout" else style.body)
        text.spaceAfter = 5
        if block.kind == "callout":
            text.style.backColor = style.tint
            text.style.borderPadding = 2
        lines.append(text)
    return lines


def story(model, style):
    flowables = [PageBreak()]
    for section in model.sections:
        pending = [Heading(section.number, section.title, style)]
        for block in section.blocks:
            if block.kind == "subheading":
                pending.extend(content(block, style))
                continue
            if block.kind == "table" and pending:
                grid, minimum = table(block, style)
                # Keep the titles with the header and one row so long tables can split.
                for heading in pending:
                    minimum += (heading.wrap(BODY_WIDTH, HEIGHT)[1]
                                + heading.getSpaceBefore() + heading.getSpaceAfter())
                    heading.keepWithNext = False
                flowables.extend((CondPageBreak(minimum), *pending, grid))
            else:
                flowables.extend(pending)
                flowables.extend(content(block, style))
            pending.clear()
        flowables.extend(pending)
    return flowables


def foot(page, title, style, number, total, credit="", left=MARGIN, right=WIDTH - MARGIN):
    page.setStrokeColor(style.line)
    page.setLineWidth(0.55)
    page.line(left, 48, right, 48)
    page.setFillColor(style.quiet)
    size = 7.1
    page.setFont(style.body, size)
    start, end = (right, left) if style.rtl else (left, right)
    middle = (left + right) / 2
    numbering = style.words["Page {number} of {total}"].format(number=number, total=total)
    style.single_line(page, title, start, 35, align=style.start, size=size)
    style.single_line(page, style.words["Confidential"], middle, 35, align=TA_CENTER, size=size)
    style.single_line(page, numbering, end, 35, align=style.end, size=size)
    if credit:
        style.single_line(page, credit, middle, 60, align=TA_CENTER, size=size)


def inside_header(page, model, style):
    line = style.label(f"{model.name} · {model.title}", size=7.8)
    _, height = line.wrap(BODY_WIDTH, 35)
    line.drawOn(page, MARGIN, HEIGHT - 25 - height)
    page.setStrokeColor(style.main)
    page.setLineWidth(0.55)
    page.line(MARGIN, HEIGHT - 49, WIDTH - MARGIN, HEIGHT - 49)


def build(model, style, page_start, page_end):
    output = BytesIO()
    document = ProjectPDF(output, page_start, page_end)
    document.title = model.title
    document.author = ""
    try:
        document.build(story(model, style))
    except CoverOverflow:
        raise Refusal("The first-page content exceeds the available space.") from None
    except LayoutError:
        raise Refusal("Shorten the document's oversized text or table row and try again.") from None
    return output.getvalue(), document.page, document.headings


def measured_pages(model, style):
    def no_decoration(page, document):
        pass

    _, total, page_numbers = build(model, style, no_decoration, no_decoration)
    return total, page_numbers


def foot_edges(style, side):
    start = 148 if side else MARGIN
    return (MARGIN, WIDTH - start) if style.rtl else (start, WIDTH - MARGIN)


def render_document(model, theme):
    style = Style(for_language(theme, model.language), model.direction, load(model.language))
    total, page_numbers = measured_pages(model, style)

    def page_start(page, document):
        if document.page == 1:
            draw_cover(page, model, style, model.choice, page_numbers)
        else:
            inside_header(page, model, style)

    def page_end(page, document):
        number = document.page
        left, right = foot_edges(style, number == 1 and model.choice["frame"] == "side")
        foot(page, model.title, style, number, total, model.credit if number == total else "",
             left=left, right=right)

    pdf, _, _ = build(model, style, page_start, page_end)
    return pdf, page_numbers


def render_preview(model, theme, options):
    style = Style(for_language(theme, model.language), model.direction, load(model.language))
    page_numbers = measured_pages(model, style)[1] if any(s.blocks for s in model.sections) else {}
    output = BytesIO()
    page = canvas.Canvas(output, pagesize=(WIDTH, HEIGHT), pageCompression=1, invariant=1)
    page.setTitle(style.words["First-page preview"])
    for number, (label, choice) in enumerate(options, 1):
        draw_cover(page, model, style, choice, page_numbers, label)
        left, right = foot_edges(style, choice["frame"] == "side")
        foot(page, model.title, style, number, len(options), left=left, right=right)
        page.showPage()
    page.save()
    return output.getvalue()
