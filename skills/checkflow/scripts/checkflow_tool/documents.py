"""Read the approved points in project document format."""

import re
from dataclasses import dataclass

from .secrets import contains_secret
from .storage import Refusal


PRD = "docs/prd.md"
DOCUMENTS = (PRD, "docs/trd.md", "DESIGN.md", "docs/data.md",
             "docs/security.md", "docs/handover.md", "docs/plan.md")
SECTIONS = {
    PRD: {
        "What it must do": "M", "ما يجب أن يفعله": "M",
        "What it will NOT do": "N", "ما لن يفعله": "N",
        "How we know it worked": "W", "كيف نعرف أنه نجح": "W",
    },
    "DESIGN.md": {"Must-have rules": "L", "قواعد لا بد منها": "L"},
    "docs/handover.md": {"What is handed over": "H", "ما يُسلَّم": "H"},
}
STAMP = re.compile(
    r"^>\s+(?:v[0-9]+\s*·\s+Approved [0-9]{4}-[0-9]{2}-[0-9]{2}(?: by .+)?"
    r"|الإصدار [0-9٠-٩]+\s*·\s+معتمد [0-9]{4}-[0-9]{2}-[0-9]{2}(?: من .+)?)\s*$"
)
HEADING = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$")
TITLE_PREFIX = re.compile(r"^(?:PRD|متطلبات المنتج(?: \(PRD\))?)\s*:\s*", re.IGNORECASE)
LIST_ITEM = re.compile(r"^( {0,3})(?:[-+*]|\d+[.)])([ \t]+)(.+\S|\S)\s*$")
FENCE = re.compile(r"^(\x60{3,}|~{3,})(.*)$")
PREFORMATTED = re.compile(r"^<pre(?:\s|>)", re.IGNORECASE)
END_PREFORMATTED = re.compile(r"</pre\s*>", re.IGNORECASE)
NUMBER = re.compile(r"^(?:\*\*)?(M[1-9][0-9]*)\.(?:\*\*)?(?:\s+|$)(.*)$")
SUBPOINT = re.compile(
    r"^[ \t]+[-+*][ \t]+(?:\*\*)?(?P<label>Check|Changed\s+\d{4}-\d{2}-\d{2}"
    r"|التحقق|تغيّر في\s+\d{4}-\d{2}-\d{2}):"
)


@dataclass(frozen=True)
class Scope:
    name: str
    points: list
    not_approved: list
    language: str


def approved(lines):
    return len(lines) > 1 and bool(STAMP.fullmatch(lines[1]))


def indentation(line):
    leading = line[:len(line) - len(line.lstrip(" \t"))]
    return len(leading.expandtabs(4))


def content_lines(lines):
    fence = None
    comment = False
    preformatted = False
    list_margin = 0
    for number, line in enumerate(lines, start=1):
        stripped = line.lstrip(" \t")
        indent = indentation(line)
        marker = FENCE.match(stripped)
        if fence:
            opening, container = fence
            if container and stripped and indent < container:
                fence = None
            else:
                if (marker and container <= indent <= container + 3 and marker[1][0] == opening[0]
                        and len(marker[1]) >= len(opening) and not marker[2].strip()):
                    fence = None
                continue
        if preformatted or (indent <= 3 and PREFORMATTED.match(stripped)):
            if not preformatted:
                list_margin = 0
                yield number, None
            preformatted = not END_PREFORMATTED.search(stripped)
            continue
        if comment or stripped.startswith("<!--"):
            comment = "-->" not in stripped
            continue
        container = list_margin if list_margin and indent >= list_margin else 0
        if (marker and indent <= container + 3
                and (marker[1][0] == "~" or "\x60" not in marker[2])):
            fence = marker[1], container
            if not container:
                list_margin = 0
                yield number, None
            continue
        if indent > container + 3:
            continue
        item = LIST_ITEM.match(line)
        if stripped and not container:
            list_margin = item.start(3) if item else 0
        yield number, line


def guard_line(path, number, line, values):
    if contains_secret(line, values):
        raise Refusal(
            f"Remove and replace the secret found in {path}, line {number}, "
            "and get the document approved again before starting the check."
        )


def extract(path, lines, round_number, values, guard):
    points = []
    heading = None
    current = None
    margin = 0
    continuation = 0
    counters = {}
    for number, line in content_lines(lines):
        if line is None:
            current = None
            continue
        header = HEADING.match(line)
        if header:
            heading = header[2] if header[1] == "##" else None
            current = None
            continue
        prefix = SECTIONS[path].get(heading)
        if not prefix:
            continue
        indent = indentation(line)
        subpoint = SUBPOINT.match(line)
        if subpoint and current is not None and indent >= margin:
            if prefix == "M" or subpoint["label"].startswith(("Changed", "تغيّر")):
                guard(path, number, line, values)
                current["text"] += "\n" + line
                continuation = indent + 2
            continue
        if not line.strip():
            continue
        if current is not None and indent >= margin:
            if indent >= continuation and not LIST_ITEM.match(line.lstrip()):
                guard(path, number, line, values)
                current["text"] += "\n" + line
            continue
        current = None
        item = LIST_ITEM.match(line)
        body = item[3] if item else line.strip()
        if body.startswith("~~") and body.endswith("~~"):
            continue
        if prefix == "M":
            numbered = NUMBER.match(body)
            if not numbered or (numbered[2].startswith("~~") and numbered[2].endswith("~~")):
                continue
            point_id = numbered[1]
        else:
            if not item:
                continue
            counters[prefix] = counters.get(prefix, 0) + 1
            point_id = f"{prefix}{counters[prefix]}"
        guard(path, number, line, values)
        current = {"id": point_id, "source": f"{path}, {heading}", "text": line,
                   "mark": "", "gap": "", "proof": "", "round": round_number}
        margin = item.start(3) if item else indent + 1
        continuation = margin
        points.append(current)
    return points


def read_scope(project, round_number, values, *, guard=guard_line):
    points = []
    unapproved = []
    name = ""
    language = "en"
    for path in DOCUMENTS:
        text = project.read_text(path)
        lines = text.splitlines() if text is not None else []
        if path == PRD:
            if not approved(lines):
                if text is None:
                    detail = "docs/prd.md is missing"
                elif len(lines) > 1 and re.search(r"\bDraft\b|مسودة", lines[1]):
                    detail = "docs/prd.md is stamped Draft"
                else:
                    detail = "docs/prd.md has no Approved stamp on line 2"
                raise Refusal(f"{detail}. Get the scope approved first.")
            language = "ar" if lines[1][1:].lstrip().startswith("الإصدار ") else "en"
            title = HEADING.match(lines[0])
            if not title or title[1] != "#":
                raise Refusal("Put the project title on line 1 of docs/prd.md.")
            guard(path, 1, lines[0], values)
            name = TITLE_PREFIX.sub("", title[2]).strip()
            if not name:
                raise Refusal("Add the project name to the title in docs/prd.md.")
        elif not approved(lines):
            if text is not None:
                unapproved.append(path)
            continue
        if path in SECTIONS:
            points.extend(extract(path, lines, round_number, values, guard))
    ids = [point["id"] for point in points]
    if len(set(ids)) != len(ids):
        raise Refusal("Give each approved point a unique number in its source document.")
    return Scope(name, points, unapproved, language)
