"""Draw the cover's approved pieces for the PDF and its first-page previews."""

from reportlab.lib.colors import linearlyInterpolatedColor
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4

from .pdf_style import timeline
from .storage import Refusal


WIDTH, HEIGHT = A4
MARGIN = 45


class CoverOverflow(Refusal):
    """A first page whose chosen pieces will not fit."""


class Cover:
    def __init__(self, canvas, model, style, choice):
        self.canvas = canvas
        self.model = model
        self.style = style
        self.choice = choice
        self.frame = choice["frame"]
        self.x = {"register": 54, "side": 148, "band": MARGIN}[self.frame]
        self.width = WIDTH - self.x - (54 if self.frame == "register" else MARGIN)
        if style.rtl:
            self.x = WIDTH - self.x - self.width
        self.y = HEIGHT - (105 if self.frame == "register" else 81)

    def draw(self, page_numbers, label):
        self.background()
        self.title(label)
        details = [self.model.detail_values[key] for key in self.choice["details"]
                   if key in self.model.detail_values and self.model.detail_values[key][1]]
        if self.frame != "register":
            self.details(details)
        self.metrics()
        self.contents(page_numbers)
        for section in self.model.cover_blocks:
            self.cover_section(section)
        if self.frame == "register" and details:
            content_end = self.y
            self.y = max(127, self.details_height(details) + 78)
            if self.y + 8 > content_end:
                self.y = content_end - 8
            self.details(details)
        if self.y < 53:
            self.overflow()

    def background(self):
        style, canvas = self.style, self.canvas
        if self.frame == "register":
            for inset, color in ((22, style.main), (26, style.line)):
                canvas.setStrokeColor(color)
                canvas.setLineWidth(0.65)
                canvas.roundRect(inset, inset, WIDTH - 2 * inset, HEIGHT - 2 * inset,
                                 style.radius, fill=0, stroke=1)
        elif self.frame == "side":
            rail = WIDTH - self.width - MARGIN - 34
            left = WIDTH - rail if style.rtl else 0
            canvas.setFillColor(style.main)
            canvas.rect(left, 0, rail, HEIGHT, fill=1, stroke=0)
            canvas.setStrokeColor(linearlyInterpolatedColor(style.main, style.on_main, 0, 1, 0.12))
            canvas.setLineWidth(0.45)
            for y in range(15, int(HEIGHT), 14):
                canvas.line(left, y, left + rail, y)

    def title(self, label):
        style = self.style
        align = TA_CENTER if self.choice["name_position"] == "center" else style.start
        band = self.frame == "band"
        name, name_height = self.project_name(style.on_main if band else style.main, align)
        title = style.text(self.model.title, size=15, face=style.bold, align=align,
                           color=style.on_main if band else style.ink)
        summary = [style.text(line, size=10.3, color=style.on_main if band else style.quiet, align=align)
                   for line in self.model.cover_summary]
        if band:
            canvas = self.canvas
            # Extend the accent only as far as the title and summary actually need.
            band_end = self.y - name_height - title.wrap(self.width, HEIGHT)[1] - 51
            band_end -= sum(p.wrap(self.width, HEIGHT)[1] + 4 for p in summary)
            canvas.setFillColor(style.main)
            canvas.rect(0, band_end, WIDTH, HEIGHT - band_end, fill=1, stroke=0)
        if label:
            color = style.on_main if band else style.main
            self.put(style.label(label, color=color), HEIGHT - 40)
        self.y = self.put(name, self.y) - 7
        rule_x = self.x + (self.width / 2 - 22 if align == TA_CENTER else
                           self.width - 44 if align == TA_RIGHT else 0)
        self.rule(rule_x, self.y, 44, style.on_main if band else style.main, 1.8)
        self.y -= 14
        self.y = self.put(title, self.y) - 7
        for paragraph in summary:
            self.y = self.put(paragraph, self.y) - 4
        self.y -= 30 if band else 23

    def project_name(self, colour, align):
        # Bound the heading area so a wrapped name cannot push the cover past its footer.
        largest = 32 if self.frame == "side" else 37
        for size in range(largest, 8, -1):
            name = self.style.text(self.model.name, size=size, leading=size * 1.13,
                                   face=self.style.heading_bold, color=colour, align=align)
            height = name.wrap(self.width, HEIGHT)[1]
            if height <= 42:
                return name, height
        self.overflow()

    def overflow(self):
        raise CoverOverflow(self.style.words["The first-page content exceeds the available space."])

    def details_height(self, details):
        if self.choice["details_style"] == "list":
            return len(details) * 18
        return 41

    def details(self, details):
        if not details:
            return
        if self.choice["details_style"] == "row":
            self.strip(details, metrics=False)
            return
        style = self.style
        label_width = min(97, self.width / 3)
        for label, value in details:
            self.rule(self.x, self.y, self.width)
            start = self.y - 3
            label_x = self.x + (self.width - label_width + 2 if style.rtl else 6)
            value_x = self.x + (6 if style.rtl else label_width)
            label_end = self.put(style.label(label, color=style.quiet), start, label_x, label_width - 8)
            value_end = self.put(style.text(value, size=8.7, face=style.bold), start,
                                 value_x, self.width - label_width - 6)
            self.y = min(label_end, value_end) - 3
        self.rule(self.x, self.y, self.width)
        self.y -= 16

    def metrics(self):
        if self.model.metrics:
            self.strip(self.model.metrics, metrics=True)

    def strip(self, entries, *, metrics):
        style = self.style
        width = self.width / len(entries)
        start = self.y - 8
        bottom = self.y
        for index, (first, second) in enumerate(entries):
            column = len(entries) - 1 - index if style.rtl else index
            x = self.x + width * column + (7 if style.rtl else 8)
            top = self.put(style.label(first, size=17 if metrics else 7.8,
                                       color=style.main if metrics else style.quiet), start, x, width - 15)
            end = self.put(style.text(second, size=8.3 if metrics else 9.2,
                                     face=style.body if metrics else style.bold), top - 2, x, width - 15)
            bottom = min(bottom, end)
        bottom -= 7
        self.rule(self.x, self.y, self.width)
        self.rule(self.x, bottom, self.width)
        canvas = self.canvas
        # Separator strokes appear only in the body of the strip.
        for index in range(1, len(entries)):
            x = self.x + index * width
            canvas.line(x, self.y - 6, x, bottom + 6)
        self.y = bottom - 19

    def contents(self, page_numbers):
        style = self.style
        self.label_rule(style.words["Contents"])
        sections = self.model.sections
        two_columns = self.frame == "register" or len(sections) > 9
        count = (len(sections) + 1) // 2
        groups = (sections[:count], sections[count:]) if two_columns else (sections,)
        gap = 19
        width = (self.width - gap * (len(groups) - 1)) / len(groups)
        bottom = self.y
        for index, group in enumerate(groups):
            column = len(groups) - 1 - index if style.rtl else index
            x, top = self.x + column * (width + gap), self.y
            for section in group:
                head = style.text(style.section_title(section.number, section.title), size=8.5)
                next_top = self.put(head, top, x + (24 if style.rtl else 0), width - 24)
                page = page_numbers.get(section.number)
                if page is not None:
                    page_x = x if style.rtl else x + width - 22
                    self.put(style.label(str(page), align=style.end), top, page_x, 22)
                self.rule(x, next_top - 2, width, weight=0.26)
                top = next_top - 7
            bottom = min(bottom, top)
        self.y = bottom - 17

    def cover_section(self, section):
        self.label_rule(section.title)
        for block in section.blocks:
            if block.kind == "timeline":
                for row in timeline(block.rows, self.style):
                    _, height = row.wrap(self.width, HEIGHT)
                    self.y -= height
                    row.drawOn(self.canvas, self.x, self.y)
                    self.y -= 7
            else:
                for (line,) in block.rows:
                    self.y = self.put(self.style.text(line, size=9), self.y) - 5
                    self.rule(self.x, self.y + 1, self.width, weight=0.3)
        self.y -= 11

    def label_rule(self, title):
        label = self.style.label(title, size=8.7)
        self.put(label, self.y)
        end = self.style.visual_width(title, self.style.bold, 8.7) + 12
        self.rule(self.x if self.style.rtl else self.x + end, self.y - 7, max(0, self.width - end))
        self.y -= 18

    def put(self, paragraph, top, x=None, width=None):
        _, height = paragraph.wrap(self.width if width is None else width, HEIGHT)
        paragraph.drawOn(self.canvas, self.x if x is None else x, top - height)
        return top - height

    def rule(self, x, y, width, color=None, weight=0.55):
        self.canvas.setStrokeColor(color or self.style.line)
        self.canvas.setLineWidth(weight)
        self.canvas.line(x, y, x + width, y)


def draw_cover(canvas, model, style, choice, page_numbers, label=None):
    cover = Cover(canvas, model, style, choice)
    cover.draw(page_numbers, label)
