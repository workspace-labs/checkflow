"""Type and reusable elements of the ReportLab document."""

from hashlib import sha256
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.platypus import Flowable, Paragraph

from .arabic import display
from .pdf_arabic import ArabicParagraph, draw_line, line_width
from .storage import Refusal


def fonts(face):
    if face.file is None:
        return "Courier", "Courier-Bold"
    registered = []
    for path, data in ((face.file, face.regular_data),
                       (face.bold or face.file, face.bold_data or face.regular_data)):
        name = "Checkflow-" + sha256(data or str(path).encode()).hexdigest()[:16]
        if name not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(name, BytesIO(data) if data else str(path)))
            except (OSError, ValueError, IndexError, pdfmetrics.FontError, TTFError):
                raise Refusal("Use a readable, embeddable TrueType font in DESIGN.md.") from None
        registered.append(name)
    return tuple(registered)


class Style:
    def __init__(self, theme, direction, words):
        self.words = words
        self.rtl = direction == "rtl"
        self.main = colors.HexColor(theme.main)
        self.on_main = colors.HexColor(theme.on_main)
        self.ink = colors.HexColor(theme.ink)
        self.quiet = colors.HexColor(theme.quiet)
        self.line = colors.HexColor(theme.line)
        self.tint = colors.HexColor(theme.tint)
        self.radius = theme.radius * 0.75
        self.space = max(3, min(13, theme.spacing * 0.75))
        self.body, self.bold = fonts(theme.body)
        self.heading, self.heading_bold = fonts(theme.heading)
        self.start, self.end = (TA_RIGHT, TA_LEFT) if self.rtl else (TA_LEFT, TA_RIGHT)

    def caps(self, value):
        return value if self.rtl else value.upper()

    def visual_width(self, value, face, size):
        if self.rtl:
            return line_width(display(value), face, size)
        return pdfmetrics.stringWidth(value, face, size)

    def single_line(self, canvas, value, x, y, *, align, size):
        if not self.rtl:
            draw = {TA_LEFT: canvas.drawString, TA_CENTER: canvas.drawCentredString,
                    TA_RIGHT: canvas.drawRightString}[align]
            draw(x, y, value)
            return
        width = self.visual_width(value, self.body, size)
        x -= width if align == TA_RIGHT else width / 2 if align == TA_CENTER else 0
        draw_line(canvas, x, y, display(value), self.body, size)

    def section_title(self, number, title):
        return self.words["{number}. {title}"].format(number=number, title=title)

    def text(self, value, *, size=9.4, leading=None, face=None, color=None, align=None):
        para = ParagraphStyle(
            "checkflow", fontName=face or self.body, fontSize=size, leading=leading or size * 1.36,
            alignment=self.start if align is None else align, textColor=color or self.ink,
            allowWidows=0, allowOrphans=0,
        )
        if self.rtl:
            return ArabicParagraph(value, para)
        return Paragraph(escape(value).replace("\n", "<br/>"), para)

    def label(self, value, **kwargs):
        return self.text(value, size=kwargs.pop("size", 8), face=self.bold,
                         color=kwargs.pop("color", self.main), **kwargs)


class Heading(Flowable):
    """A compact heading with a rule and one tracked section start."""

    keepWithNext = True

    def __init__(self, number, title, style):
        super().__init__()
        self.number = number
        self.style = style
        self.title = style.text(style.section_title(number, title), size=15, face=style.heading_bold,
                                color=style.main)
        self.spaceBefore = 13
        self.spaceAfter = 8

    def wrap(self, avail_width, avail_height):
        _, self.title_height = self.title.wrap(avail_width, avail_height)
        self.width = avail_width
        self.height = self.title_height + 5
        return self.width, self.height

    def draw(self):
        self.title.drawOn(self.canv, 0, 5)
        self.canv.setStrokeColor(self.style.main)
        self.canv.setLineWidth(1.15)
        x = self.width - 36 if self.style.start == TA_RIGHT else 0
        self.canv.line(x, 0, x + 36, 0)


class Badge(Flowable):
    """A text status in a tinted label that wraps inside its table cell."""

    def __init__(self, value, style):
        super().__init__()
        status = value.casefold()
        passed = {style.words[key].casefold()
                  for key in ("Covered", "Delivered", "Left out as agreed", "Fixed")}
        changed = tuple(style.words[key].casefold() for key in ("Changed", "Changed, approved", "Keep"))
        if status in passed:
            self.background = colors.HexColor("#E2F0E6")
            ink = colors.HexColor("#205732")
        elif status.startswith(changed):
            self.background = colors.HexColor("#F8EBCB")
            ink = colors.HexColor("#694605")
        else:
            self.background, ink = style.tint, style.ink
        self.text = style.label(style.caps(value), size=7.2, color=ink)
        self.ideal = style.visual_width(value if style.rtl else value.upper(), style.bold, 7.2) + 8
        self.radius = style.radius

    def wrap(self, width, height):
        self.width = min(width, self.text.minWidth() + 8)
        self.width = min(width, max(self.width, self.ideal))
        _, text_height = self.text.wrap(max(1, self.width - 8), height)
        self.height = text_height + 4
        return self.width, self.height

    def draw(self):
        self.canv.setFillColor(self.background)
        self.canv.roundRect(0, 0, self.width, self.height, self.radius, fill=1, stroke=0)
        self.text.drawOn(self.canv, 4, 2)


class Signoff(Flowable):
    """Draw two aligned signing panels with space to write on each line."""

    def __init__(self, parties, fields, style):
        super().__init__()
        self.style = style
        self.parties = [(style.label(label, size=8, color=style.quiet),
                         style.label(name, size=11)) for label, name in parties]
        self.fields = [style.label(field, size=7.8, color=style.quiet) for field in fields]
        self.gap = 18
        self.padding = 12
        self.field_height = 30

    def wrap(self, width, height):
        self.width = width
        self.box_width = (width - self.gap) / 2
        self.text_width = self.box_width - 2 * self.padding
        heading_height = max(sum(item.wrap(self.text_width, height)[1] for item in party)
                             for party in self.parties)
        self.height = heading_height + 8 + 2 * self.padding + len(self.fields) * self.field_height
        return self.width, self.height

    def draw(self):
        canvas = self.canv
        for index, party in enumerate(self.parties):
            column = len(self.parties) - 1 - index if self.style.rtl else index
            x = column * (self.box_width + self.gap)
            canvas.setStrokeColor(self.style.line)
            canvas.setLineWidth(0.7)
            canvas.roundRect(x, 0, self.box_width, self.height, self.style.radius, fill=0, stroke=1)
            canvas.setStrokeColor(self.style.main)
            canvas.setLineWidth(1.6)
            canvas.line(x + self.style.radius, self.height, x + self.box_width - self.style.radius,
                        self.height)
            top = self.height - self.padding
            left = x + self.padding
            for item in party:
                top -= item.height
                item.drawOn(canvas, left, top)

            canvas.setStrokeColor(self.style.line)
            canvas.setLineWidth(0.65)
            for number, label in enumerate(self.fields):
                bottom = self.padding + (len(self.fields) - 1 - number) * self.field_height
                _, height = label.wrap(self.text_width, self.field_height)
                label.drawOn(canvas, left, bottom + self.field_height - height - 1)
                canvas.line(left, bottom, left + self.text_width, bottom)


class TimelineRow(Flowable):
    """A row of dated markers. The date and its label remain real text."""

    def __init__(self, rows, style):
        super().__init__()
        self.rows = [(style.label(day, size=8.3, align=TA_CENTER),
                      style.text(label, size=8, color=style.quiet, align=TA_CENTER))
                     for day, label in rows]
        self.ink = style.main
        self.rtl = style.rtl
        self.spaceAfter = 7

    def wrap(self, width, height):
        self.width = width
        self.step = width / len(self.rows)
        self.date_height = max(day.wrap(self.step - 4, height)[1] for day, _ in self.rows)
        self.label_height = max(label.wrap(self.step - 4, height)[1] for _, label in self.rows)
        self.height = self.label_height + self.date_height + 15
        return self.width, self.height

    def draw(self):
        y = self.label_height + 6
        canvas = self.canv
        canvas.setStrokeColor(self.ink)
        canvas.setFillColor(self.ink)
        canvas.setLineWidth(0.9)
        if len(self.rows) > 1:
            canvas.line(self.step / 2, y, self.width - self.step / 2, y)
        for index, (day, label) in enumerate(self.rows):
            column = len(self.rows) - 1 - index if self.rtl else index
            x = column * self.step
            canvas.circle(x + self.step / 2, y, 2.7, fill=1, stroke=0)
            day.drawOn(canvas, x + 2, self.height - day.height)
            label.drawOn(canvas, x + 2, self.label_height - label.height)


def timeline(rows, style):
    return [TimelineRow(rows[index:index + 5], style) for index in range(0, len(rows), 5)]
