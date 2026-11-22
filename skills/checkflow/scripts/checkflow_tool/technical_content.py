"""Collect the approved operating details used in both technical document formats."""

import re

from . import documents, report, secrets
from .document_content import Block, Section, paragraphs, plain, point_text
from .document_secrets import SETTING, guard_line


TRD = "docs/trd.md"
DATA = "docs/data.md"
SECURITY = "docs/security.md"
HANDOVER = "docs/handover.md"
SETTING_FILES = (".env.example", *secrets.SETTING_FILES)

# Headings and labels in the approved source documents.
HEADINGS = {
    "What it is": "ما هو",
    "Work rules": "قواعد العمل", "Screen": "الواجهة", "Brain": "الخادم",
    "Data storage": "تخزين البيانات", "Where it lives": "أين يعمل",
    "Outside services": "الخدمات الخارجية", "Rules it must follow": "القواعد التي يلتزم بها",
    "Available": "التوفر", "Release recovery": "التعافي عند الإصدار",
    "What it saves": "ما يحفظه", "Sheets": "الجداول", "How the sheets link": "كيف ترتبط الجداول",
    "If this copy is lost": "إذا ضاعت هذه النسخة", "Who can get in": "من يستطيع الدخول",
    "Running it": "تشغيله", "Maintenance and updates": "الصيانة والتحديثات",
    "Assumptions and risks": "الافتراضات والمخاطر", "Later": "لاحقًا",
}
SECTION_TITLES = (
    "What it is built with", "How it is put together", "The database", "Install and run",
    "The settings it needs", "Who can do what", "Outside services", "Backup and getting data back",
    "Watching it", "Updating it and going back", "Security status", "Known limits",
)
SETTING_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
ENV_NAME = re.compile(rf"^\s*(?:export[ \t]+)?({SETTING_NAME})[ \t]*=[ \t]*(['\"])?")
QUOTE_END = {quote: re.compile(rf"(?:[^{quote}\\]|\\.)*{quote}") for quote in ("'", '"')}
DOCUMENT_SETTING = re.compile(
    rf"\$\{{?({SETTING_NAME})\}}?|\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b"
)
CODE_SPAN = re.compile(r"`([^`\n]+)`")
MARKS = {"column": ("Column", "العمود"), "holds": ("Holds", "يحمل", "ما يحفظه"),
         "mark": ("Mark", "العلامة")}
COMMON_WORDS = frozenset(
    "about after any before can each every for from gets has have into one per the "
    "their them they this use uses was were what when which will with would "
    "إلى التي الذي بعد على عند قبل لكل هذه هذا ويتم ومن".split()
)


def read_approved(project, path):
    lines = (project.read_text(path) or "").splitlines()
    if not documents.approved(lines):
        return {}
    sections = {}
    heading = None
    for number, line in documents.content_lines(lines):
        if line is None:
            continue
        title = documents.HEADING.match(line)
        if title and title[1] in ("#", "##"):
            heading = sections.setdefault(title[2], []) if title[1] == "##" else None
        elif heading is not None:
            heading.append((number, line))
    return sections


def normalize_heading(heading):
    return re.sub("[\u064b-\u065f\u0670]", "", heading).casefold()


def words(text):
    return frozenset(word for word in re.findall(r"[^\W_]+", normalize_heading(text))
                     if len(word) >= 3 and not word.isdigit()) - COMMON_WORDS


def change_details(data, word, source):
    points = {point["id"]: point_text(point) for point in data["points"]}
    context = words(data["project"]["name"] + " " + data["project"]["client"])
    rows = []
    references = []
    for change in data["changes"]:
        if change["decision"] != "keep":
            continue
        point = change.get("point") or ""
        approved = points.get(point, "")
        built = plain(change["what"])
        rows.append((change["id"], point or "—",
                     source(approved) if approved else word("No approved point is recorded."),
                     source(built)))
        if approved and change["kind"] == "different":
            agreed_words = words(approved) - context
            references.append((change["id"], point, approved, agreed_words, agreed_words - words(built)))
    if not rows:
        return (), references
    return (
        Block("subheading", ((word("Kept changes"),),)),
        Block("table", tuple(rows), tuple(map(word, ("No.", "Point", "What was approved", "What was built"))),
              (.08, .11, .40, .41), (), (0, 1)),
    ), references


def related_changes(fragment, references):
    """Prefer explicit references and full quotes over shared vocabulary."""
    text = normalize_heading(fragment)
    terms = words(fragment)
    for change, point, approved, agreed_words, replaced_words in references:
        identifiers = "|".join(re.escape(value.casefold()) for value in (change, point))
        if (re.search(rf"(?<![\w-])(?:{identifiers})(?![\w-])", text)
                or normalize_heading(approved) in text
                or (len(agreed_words & terms) >= 2 and replaced_words & terms)):
            yield change


def aliases(heading, source_language):
    return (heading,) if source_language == "en" else (HEADINGS[heading], heading)


def section(doc, heading, source_language):
    names = {normalize_heading(name) for name in aliases(heading, source_language)}
    return next((lines for title, lines in doc.items() if normalize_heading(title) in names), ())


def items(lines):
    """Read prose and list items, keeping their source line for a refusal."""
    parts = []
    for number, raw in lines:
        bullet = documents.LIST_ITEM.match(raw)
        if (bullet or not raw.strip()) and parts:
            yield parts
            parts = []
        if raw.strip():
            parts.append((number, bullet[3] if bullet else raw.strip()))
    if parts:
        yield parts


def field(line, heading, source_language):
    names = {normalize_heading(name) for name in aliases(heading, source_language)}
    return normalize_heading(line.partition(":")[0]) in names and ":" in line


def checked_text(path, number, raw, values, names):
    for code in CODE_SPAN.findall(raw):
        guard_line(path, number, code, values, setting_names=names)
    text = plain(raw)
    guard_line(path, number, text, values, setting_names=names)
    return text


def fragments(path, lines, values, names, /, *, only=None, omit=None, source_language):
    for parts in items(lines):
        fragment = plain(" ".join(raw for _, raw in parts))
        if not fragment:
            continue
        if only and not field(fragment, only, source_language):
            continue
        if omit and field(fragment, omit, source_language):
            continue
        for number, raw in parts:
            checked_text(path, number, raw, values, names)
        if len(parts) > 1:
            guard_line(path, parts[0][0], fragment, values, setting_names=names)
        yield fragment


def env_names(text):
    quote = None
    for number, line in enumerate(text.splitlines(), 1):
        if quote is not None:
            if QUOTE_END[quote].match(line):
                quote = None
            continue
        match = ENV_NAME.match(line)
        if match:
            yield number, match[1]
            if match[2] and not QUOTE_END[match[2]].match(line, match.end()):
                quote = match[2]


def setting_names(project, approved, values):
    names = set()

    def add(path, number, name):
        guard_line(path, number, name, values)
        names.add(name)

    for path in SETTING_FILES:
        for number, name in env_names(project.read_text(path) or ""):
            add(path, number, name)
    for path in (TRD, SECURITY):
        for lines in approved[path].values():
            for number, line in lines:
                assignment = next((
                    match for match in SETTING.finditer(line)
                    if match[1] in names or match[1].isupper() or match[2] == "="
                ), None)
                # The assignment tail can contain a value shaped like a name.
                if assignment is not None:
                    add(path, number, assignment[1])
                    line = line[:assignment.start()]
                for reference in DOCUMENT_SETTING.finditer(line):
                    add(path, number, reference[1] or reference[2])
    return tuple(sorted(names))


def table_cells(line):
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        return ()
    return tuple(cell.strip() for cell in re.split(r"(?<!\\)\|", line[1:-1]))


def column_positions(cells):
    keys = tuple(normalize_heading(plain(cell)) for cell in cells)
    positions = {}
    for name, spellings in MARKS.items():
        expected = {normalize_heading(spelling) for spelling in spellings}
        for index, key in enumerate(keys):
            if key in expected:
                positions[name] = index
                break
    return tuple(positions.values()) if len(positions) == len(MARKS) else ()


def sheet_blocks(lines, word, quote, values, names, source_language):
    blocks = []
    prose = []
    rows = []
    positions = ()
    for number, line in (*lines, (0, "")):
        cells = table_cells(line)
        if not cells:
            if rows:
                blocks.append(Block("table", tuple(rows), tuple(map(word, ("Column", "Holds", "Mark"))),
                                    (.24, .48, .28)))
                rows.clear()
            positions = ()
        heading = documents.HEADING.match(line)
        if (heading or cells or not number) and prose:
            text = tuple(quote(fragment) for fragment in
                         fragments(DATA, prose, values, names, source_language=source_language))
            if text:
                blocks.append(paragraphs(text, ""))
            prose.clear()
        if heading:
            title = checked_text(DATA, number, heading[2], values, names)
            blocks.append(Block("subheading", ((quote(title),),)))
        elif cells:
            if not positions:
                positions = column_positions(cells)
            elif max(positions) < len(cells) and not all(
                    re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells):
                name, holds, mark = (
                    checked_text(DATA, number, cells[index], values, names) for index in positions
                )
                identifier = quote(name, translate=not re.fullmatch(SETTING_NAME, name))
                rows.append((identifier, quote(holds), quote(mark)))
            continue
        elif number:
            prose.append((number, line))
    return tuple(blocks)


def build(project, scope, data, values, source_language, word, source, *, readme_present):
    approved = {path: read_approved(project, path) for path in (documents.PRD, TRD, DATA, SECURITY, HANDOVER)}
    names = setting_names(project, approved, values)

    changes, references = change_details(data, word, source)

    def extracted(path, *headings, **fields):
        return tuple(
            fragment for heading in headings
            for fragment in fragments(path, section(approved[path], heading, source_language), values, names,
                                      source_language=source_language, **fields)
        )

    def quote(fragment, *, translate=True):
        text = source(fragment) if translate else fragment
        notes = tuple(word("See kept change {id} in section 2.").format(id=change)
                      for change in related_changes(fragment, references))
        return " ".join((text, *notes))

    def take(path, *headings, **fields):
        return tuple(quote(fragment) for fragment in extracted(path, *headings, **fields))

    def body(lines):
        return (paragraphs(lines, word("No source is recorded.")),)

    def optional(lines):
        return (paragraphs(lines, ""),) if lines else ()

    data_before = take(DATA, "What it saves", omit="If this copy is lost")
    sheets = sheet_blocks(section(approved[DATA], "Sheets", source_language),
                          word, quote, values, names, source_language)
    data_after = take(DATA, "How the sheets link")
    running = take(HANDOVER, "Running it")
    install = running
    if readme_present:
        install += (word("The commands to install and run the project are in README.md."),)
    maintenance = take(HANDOVER, "Maintenance and updates")
    problems = tuple(
        word("{id} · {status}: {problem} · {next_label}: {next_step}").format(
            id=row["id"], status=word(row["state"]), problem=source(plain(row["line"])),
            next_label=word("What to do"),
            next_step=source(plain(row["next"])) if row.get("next", "").strip()
            else word("No next step is recorded."),
        ) for row in data["problems"]
    )
    accepted = tuple(
        word("{id} · {reason}").format(id=row["id"], reason=source(plain(row["accepted"])))
        for row in report.accepted_problems(data)
    )
    excluded = tuple(word("Unapproved document, not used: {path}").format(path=path)
                     for path in scope.not_approved)
    limits = take(documents.PRD, "Assumptions and risks", "Later") + accepted
    tools_used = []
    revised_tools = []
    for fragment in extracted(TRD, "Work rules", "Screen", "Brain", "Data storage"):
        if any(related_changes(fragment, references)):
            revised_tools.append(quote(fragment))
        else:
            tools_used.append(quote(fragment))
    if not tools_used and revised_tools:
        tools_used.append(word("See section 2 for the approved details."))
    architecture = take(documents.PRD, "What it is") + take(TRD, "Brain", "Where it lives")
    architecture += tuple(fragment for fragment in revised_tools if fragment not in architecture)
    sections = (
        body(tuple(tools_used)),
        changes + body(architecture),
        optional(data_before) + sheets + optional(data_after) or body(()),
        body(install),
        body(names),
        body(take(SECURITY, "Who can get in")),
        body(take(TRD, "Outside services") + take(SECURITY, "Outside services")),
        body(take(DATA, "What it saves", only="If this copy is lost") + maintenance),
        body(running + take(TRD, "Rules it must follow", only="Available")),
        body(take(TRD, "Where it lives", only="Release recovery") + maintenance),
        body(problems),
        body(limits) + optional(excluded),
    )
    return tuple(Section(number, word(title), blocks)
                 for number, (title, blocks) in enumerate(zip(SECTION_TITLES, sections), 1))
