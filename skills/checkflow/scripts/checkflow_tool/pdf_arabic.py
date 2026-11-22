"""Wrap Arabic in reading order and shape each PDF line before it is drawn."""

from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Flowable

from .arabic import display, is_mark, visual


def line_width(text, font, size):
    shaped = "".join(character for character, _ in visual(text))
    return pdfmetrics.stringWidth(shaped, font, size)


def draw_line(canvas, x, y, text, font, size):
    # Separate the zero-width vowel marks so they can sit on their own letters.
    shaped = [character for character, _ in visual(text)]
    marks = []
    run = ""
    for character in shaped:
        if is_mark(character):
            marks.append(character)
            continue
        if marks:
            canvas.drawString(x, y, run)
            x += pdfmetrics.stringWidth(run, font, size)
            width = pdfmetrics.stringWidth(character, font, size)
            canvas.drawString(x + max(0, (width - 0.2 * size) / 2), y, "".join(marks))
            run = ""
            marks.clear()
        run += character
    canvas.drawString(x, y, run + "".join(marks))


class ArabicParagraph(Flowable):
    """Plain text with the same layout inputs as the English paragraphs."""

    def __init__(self, value, style):
        super().__init__()
        self.value = display(value)
        self.style = style

    def measure(self, text):
        return line_width(text, self.style.fontName, self.style.fontSize)

    def minWidth(self):
        return max((self.measure(word) for word in self.value.split()), default=0)

    def _split_word(self, word, width):
        fragment = ""
        for character in word:
            if fragment and not is_mark(character) and self.measure(fragment + character) > width:
                yield fragment
                fragment = ""
            fragment += character
        if fragment:
            yield fragment

    def _wrap_line(self, source, width):
        line = ""
        for word in source.split():
            candidate = f"{line} {word}" if line else word
            if self.measure(candidate) <= width:
                line = candidate
                continue
            if line:
                yield line
            *fragments, line = self._split_word(word, width)
            yield from fragments
        yield line

    def wrap(self, width, height):
        self.width = width
        self.lines = [line for source in self.value.split("\n") for line in self._wrap_line(source, width)]
        self.height = len(self.lines) * self.style.leading
        return self.width, self.height

    def split(self, width, height):
        self.wrap(width, height)
        count = min(int(height / self.style.leading), len(self.lines) - 2)
        if count < 2:
            return []
        first, rest = self.lines[:count], self.lines[count:]
        opening = type(self)("\n".join(first), self.style)
        closing = type(self)("\n".join(rest), self.style)
        opening.spaceBefore = self.getSpaceBefore()
        closing.spaceAfter = self.getSpaceAfter()
        return [opening, closing]

    def draw(self):
        style, canvas = self.style, self.canv
        if style.backColor:
            padding = style.borderPadding
            canvas.setFillColor(style.backColor)
            canvas.rect(-padding, -padding, self.width + 2 * padding, self.height + 2 * padding,
                        stroke=0, fill=1)
        canvas.setFillColor(style.textColor)
        canvas.setFont(style.fontName, style.fontSize)
        for index, line in enumerate(self.lines):
            remaining = self.width - self.measure(line)
            x = remaining if style.alignment == TA_RIGHT else remaining / 2 if style.alignment == TA_CENTER else 0
            y = self.height - style.fontSize - index * style.leading
            draw_line(canvas, x, y, line, style.fontName, style.fontSize)
