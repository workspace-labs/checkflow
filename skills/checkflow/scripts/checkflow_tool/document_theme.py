"""Resolve a project's document colours, dimensions and licensed local fonts."""

import re
from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
from struct import Struct, error as StructError
from typing import Optional

from .arabic import REQUIRED_GLYPHS
from .document_language import load
from .documents import approved
from .secrets import contains_secret
from .storage import Refusal


FONT_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
TOKENS = re.compile(r"(?m)^\s*--([a-z0-9-]+):\s*([^;\n]+)\s*;")
HEX = re.compile(r"#[0-9a-fA-F]{6}")
PIXELS = re.compile(r"(\d{1,2}(?:\.\d+)?)\s*px\b")
COLOUR_LABELS = {
    "background": "background",
    "text": "text",
    "quiet text": "quiet",
    "main color": "main",
    "main colour": "main",
    "lines": "lines",
}
FONT_DIRS = ("docs/fonts", "assets/fonts", "fonts", ".")
MAX_FONT_BYTES = 8 * 1024 * 1024
SFNT_HEADER = Struct(">4sH6x")
SFNT_RECORD = Struct(">4s4xII")


@dataclass(frozen=True)
class FontFace:
    name: str
    file: Optional[Path]
    bold: Optional[Path]
    regular_data: Optional[bytes] = None
    bold_data: Optional[bytes] = None


ALEXANDRIA = FontFace("Alexandria", FONT_ASSETS / "Alexandria-Regular.ttf",
                      FONT_ASSETS / "Alexandria-Bold.ttf")
MONOSPACE = FontFace("Courier", None, None)


@dataclass(frozen=True)
class Theme:
    main: str
    on_main: str
    ink: str
    quiet: str
    line: str
    tint: str
    radius: float
    spacing: float
    heading: FontFace
    body: FontFace
    notices: tuple


def table_cells(design):
    for line in design.splitlines():
        if line.strip().startswith("|"):
            cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                yield cells[0].casefold(), cells[1]


def channels(colour):
    return tuple(int(colour[index:index + 2], 16) for index in (1, 3, 5))


def luminance(colour):
    rgb = [channel / 255 for channel in channels(colour)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in rgb]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def blend(colour, paper, paper_share):
    rgb = [round(a * (1 - paper_share) + b * paper_share)
           for a, b in zip(channels(colour), channels(paper))]
    return "#" + "".join(f"{value:02X}" for value in rgb)


def readable(colour, background, minimum=4.5):
    lighter = luminance(background)
    adjusted = colour
    while (lighter + 0.05) / (luminance(adjusted) + 0.05) < minimum:
        adjusted = blend(adjusted, "#000000", 0.08)
    return adjusted


def design_tokens(design):
    tokens = dict(TOKENS.findall(design))
    for label, value in table_cells(design):
        if label in COLOUR_LABELS:
            tokens.setdefault(f"color-{COLOUR_LABELS[label]}", value)
        elif label in ("headings", "text") and not HEX.fullmatch(value):
            role = "heading" if label == "headings" else "text"
            tokens.setdefault(f"font-{role}", value)
    corners = re.search(r"(?im)^- *\*\*Corners:\*\* *([^\n]+)", design)
    if corners:
        radius = PIXELS.search(corners[1])
        if radius:
            tokens.setdefault("radius", radius[0])
    spacing = re.search(r"(?im)^- *\*\*Spacing:\*\* *([^\n]+)", design)
    if spacing:
        steps = re.match(r"(?:steps of )?(\d{1,2}), *(\d{1,2})\b", spacing[1], re.IGNORECASE)
        if steps:
            tokens.setdefault("space-2", f"{steps[2]}px")
    return tokens


def size(tokens, key, fallback, maximum, *, minimum=0):
    match = PIXELS.fullmatch(tokens.get(key, "").strip())
    if match:
        return max(minimum, min(float(match[1]), maximum))
    return fallback


def font_key(name):
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def embedding_allowed(blob):
    if len(blob) < SFNT_HEADER.size:
        return False
    marker, count = SFNT_HEADER.unpack_from(blob)
    if marker not in (b"\x00\x01\x00\x00", b"true"):
        return False
    if SFNT_HEADER.size + count * SFNT_RECORD.size > len(blob):
        return False
    for index in range(count):
        tag, offset, length = SFNT_RECORD.unpack_from(blob, SFNT_HEADER.size + index * SFNT_RECORD.size)
        if tag == b"OS/2" and length >= 10 and offset + length <= len(blob):
            embedding = int.from_bytes(blob[offset + 8:offset + 10], "big")
            # The PDF subsets the font. The HTML embeds it for viewing.
            return not embedding & (0x0002 | 0x0100 | 0x0200)
    return False


def font_has_secret(blob, values):
    decoded = blob.decode("utf-8", errors="ignore")
    return contains_secret(decoded, values) or any(
        secret.distinctive and any(secret.value.encode(encoding) in blob
                                   for encoding in ("utf-16-be", "utf-16-le"))
        for secret in values
    )


def font_data(path, family, values, words):
    if path.stat().st_size > MAX_FONT_BYTES:
        return None
    blob = path.read_bytes()
    if font_has_secret(blob, values):
        raise Refusal(words["Remove the known secret from the project font and replace the secret."])
    if not embedding_allowed(blob):
        return None
    # ReportLab is loaded only when the renderer needs a project font.
    from reportlab.pdfbase.ttfonts import TTFont, TTFError
    try:
        face = TTFont("CheckflowFontTrial", BytesIO(blob)).face
        actual_name = face.familyName.decode("utf-8", errors="replace")
    except (TTFError, StructError, ValueError, LookupError, OSError, RuntimeError):
        return None
    return blob if font_key(actual_name) == family else None


def font_licence(directory, family):
    allowed_names = {f"{family}ofl", f"ofl{family}", f"{family}license",
                     f"license{family}", f"{family}licence", f"licence{family}", "ofl"}
    for path in sorted(directory.iterdir()):
        if (font_key(path.stem) not in allowed_names or path.is_symlink() or not path.is_file()
                or path.suffix.casefold() not in (".txt", ".md", "")
                or path.stat().st_size > 100_000):
            continue
        words = " ".join(path.read_text(encoding="utf-8", errors="replace").casefold().split())
        named = font_key(path.stem) != "ofl" or family in font_key(words)
        if named and "sil open font license" in words and "permission is hereby granted" in words:
            return True
        if "apache license" in words and "version 2.0" in words and font_key(path.stem) != "ofl":
            return True
    return False


def local_font(project, name, values, words):
    family = font_key(name)
    if not family:
        return None
    for relative in FONT_DIRS:
        try:
            directory = project.path(relative)
        except Refusal:
            continue
        if not directory.is_dir() or not directory.resolve().is_relative_to(project.root):
            continue
        candidates = {}
        for file in sorted(directory.glob("*")):
            if (file.suffix.casefold() == ".ttf" and not file.is_symlink() and file.is_file()
                    and file.resolve().is_relative_to(project.root)):
                candidates.setdefault(font_key(file.stem), file)
        regular = candidates.get(f"{family}regular", candidates.get(family))
        if not regular or not font_licence(directory, family):
            continue
        regular_data = font_data(regular, family, values, words)
        if regular_data is None:
            continue
        bold = candidates.get(f"{family}bold")
        bold_data = font_data(bold, family, values, words) if bold else None
        return FontFace(name, regular, bold if bold_data else None, regular_data, bold_data)
    return None


def select_font(project, tokens, role, values, notices, words):
    primary = tokens.get(f"font-{role}", "").partition(",")[0].strip().strip("\"'")
    if role == "heading" and primary.casefold() in ("monospace", "system monospace"):
        return MONOSPACE
    if primary:
        face = local_font(project, primary, values, words)
        if face:
            return face
    label = words["heading" if role == "heading" else "body"]
    notice = words["Using Alexandria for the {role} because DESIGN.md supplies no licensed usable font."]
    notices.append(notice.format(role=label))
    return ALEXANDRIA


def for_language(theme, language):
    if language != "ar":
        return theme

    from reportlab.pdfbase.ttfonts import TTFont

    def usable(face):
        if face == ALEXANDRIA:
            return face
        if face.file is None:
            return ALEXANDRIA
        for path, data in ((face.file, face.regular_data), (face.bold, face.bold_data)):
            if path is None:
                continue
            glyphs = TTFont("CheckflowArabicTrial", BytesIO(data) if data else str(path)).face.charToGlyph
            if any(not glyphs.get(ord(character)) for character in REQUIRED_GLYPHS):
                return ALEXANDRIA
        return face

    return replace(theme, heading=usable(theme.heading), body=usable(theme.body))


def load_theme(project, values, language="en"):
    words = load(language)
    design = project.read_text("DESIGN.md")
    notices = []
    if design is None:
        notices.append(words["No DESIGN.md was found. Using neutral colours and Alexandria."])
    elif not approved(design.splitlines()):
        notices.append(words["DESIGN.md is not approved. Using neutral colours and Alexandria."])
        design = None
    tokens = design_tokens(design or "")

    def colour(name, fallback):
        value = tokens.get(name, "").strip()
        return value.upper() if HEX.fullmatch(value) else fallback

    white = "#FFFFFF"
    main = colour("color-main", "#394759")
    background = colour("color-background", blend(main, white, 0.93))
    tint = blend(background, white, 0.4 if luminance(background) > 0.85 else 0.93)
    if tint == white:
        tint = blend(main, white, 0.95)
    ink = colour("color-text", "#252B32")
    quiet = colour("color-quiet", "#515B65")
    line = colour("color-lines", "#A1A9B1")
    adjusted = [readable(main, tint), readable(ink, tint), readable(quiet, tint)]
    for before, after, role in zip((main, ink, quiet), adjusted, ("main", "text", "quiet text")):
        if before != after:
            notice = words["Darkened the {role} colour for readable contrast on white paper."]
            notices.append(notice.format(role=words[role]))
    main, ink, quiet = adjusted
    line = readable(line, tint, minimum=2.25)
    heading = select_font(project, tokens, "heading", values, notices, words) if design is not None else ALEXANDRIA
    body = select_font(project, tokens, "text", values, notices, words) if design is not None else ALEXANDRIA
    radius = size(tokens, "radius", 4, 32)
    spacing = size(tokens, "space-2", 8, 16, minimum=4)
    return Theme(main, white, ink, quiet, line, tint, radius, spacing, heading, body, tuple(notices))
