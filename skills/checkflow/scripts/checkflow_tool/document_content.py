"""Build the client-facing content shared by PDF and HTML."""

import re
from dataclasses import asdict, dataclass, replace

from . import document_language, document_secrets, documents, first_page, report, secrets
from .document_dates import LABELS, reconciled_dates
from .proof import client_text
from .storage import Refusal


TITLE = "Project Delivery Document"
CREDIT = "Made with checkflow, a WorkSpace Labs skill"
TRANSLATION_NOTICE = "This is a translation. The approved documents are the official source."
SECTION_TITLES = (
    "Summary", "What you asked for and what you got",
    "What changed since you approved it", "What was not built", "Project dates",
    "How it was tested", "What you receive", "What happens next", "Sign-off",
)
HANDOVER = "docs/handover.md"
NEXT_STEPS = ("Who receives it", "Announcing it", "First weeks after go-live",
              "Running it", "Maintenance and updates")
PRD_HEADINGS = ("What it is", "Why", "Later")
HANDOVER_HEADINGS = ("What is handed over", *NEXT_STEPS)


@dataclass(frozen=True)
class Block:
    kind: str
    rows: tuple
    headers: tuple = ()
    widths: tuple = ()
    badges: tuple = ()
    numeric: tuple = ()


@dataclass(frozen=True)
class Section:
    number: int
    title: str
    blocks: tuple


@dataclass(frozen=True)
class Document:
    name: str
    title: str
    language: str
    direction: str
    cover_summary: tuple
    detail_values: dict
    details: tuple
    choice: dict
    metrics: tuple
    cover_blocks: tuple
    sections: tuple
    credit: str


def plain(text):
    text = re.sub(r"\x60([^`\n]+)\x60", r"\1", text)
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_\n]+)__", r"\1", text)
    text = re.sub(r"\[([^\]\n]+)\]\([^)\n]+\)", r"\1", text)
    return " ".join(text.split())


def document_sections(text, path, headings, values):
    lines = text.splitlines() if text is not None else []
    if not documents.approved(lines):
        return {}
    result = {}
    heading = None
    for number, line in documents.content_lines(lines[2:]):
        if line is None:
            continue
        title = documents.HEADING.match(line)
        if title:
            heading = title[2] if title[1] == "##" else None
        elif heading in headings and line.strip():
            item = documents.LIST_ITEM.match(line)
            raw = item[3] if item else line
            fragment = plain(raw)
            document_secrets.guard_line(path, number + 2, raw, values)
            if fragment != raw:
                document_secrets.guard_line(path, number + 2, fragment, values)
            if item or not line.startswith((" ", "\t")) or not result.get(heading):
                result.setdefault(heading, []).append(fragment)
            else:
                combined = result[heading][-1] + " " + fragment
                document_secrets.guard_line(path, number + 2, combined, values)
                result[heading][-1] = combined
    return {name: tuple(value for value in lines if value) for name, lines in result.items()}


def point_text(point):
    lines = point["text"].splitlines()
    first = documents.LIST_ITEM.match(lines[0])
    body = first[3] if first else lines[0]
    number = documents.NUMBER.match(body)
    text = plain(number[2] if number else body)
    in_note = False
    for line in lines[1:]:
        note = documents.SUBPOINT.match(line)
        if not note:
            if not in_note:
                text += " " + plain(line)
            continue
        in_note = True
        if not note["label"].startswith(("Changed", "تغيّر")):
            continue
        change = plain(line[note.end():].lstrip("* "))
        before, arrow, after = change.partition(" → ")
        if arrow and before and before in text:
            revised = re.split(r", because |; adds |، لأن |، بسبب ", after, maxsplit=1)[0].rstrip(".")
            text = text.replace(before, revised, 1)
        else:
            text += f" {note['label']}: {change}"
    return text


def paragraphs(lines, empty):
    return Block("paragraphs", tuple((line,) for line in lines or (empty,)))


def source_sections(project, path, source_language, headings, values):
    aliases = document_language.load(source_language)
    sections = document_sections(project.read_text(path), path, {aliases[key] for key in headings}, values)
    return {key: sections.get(aliases[key], ()) for key in headings}


def point_row(row, approved_changes, word, source, *, exclusion=False):
    if row["mark"] == "covered":
        badge = "Left out as agreed" if exclusion else "Delivered"
    elif row["mark"] == "changed" and row["id"] in approved_changes:
        badge = "Changed, approved"
    else:
        badge = row["mark"].capitalize()
    evidence = client_text(row["proof"], row["id"])
    return row["id"], source(point_text(row)), word(badge), source(plain(evidence))


def exclusions(prd, excluded, word, source):
    blocks = []
    if excluded:
        blocks.extend((
            Block("subheading", ((word("Out of scope"),),)),
            Block("table", excluded, tuple(map(word, ("No.", "Agreed exclusion", "Result", "Where to see it"))),
                  (.08, .33, .19, .40), (2,), (0,)),
        ))
    later = prd["Later"]
    if later:
        blocks.extend((Block("subheading", ((word("Later"),),)),
                       Block("list", tuple((source(line),) for line in later))))
    return tuple(blocks) or (paragraphs((), word("Nothing is listed outside the build.")),)


def content_blocks(data, prd, handover, dates, prepared_by, client, word, source):
    kept = [row for row in data["changes"] if row["decision"] == "keep"]
    approved_changes = {row.get("point") for row in kept if row["kind"] == "different" and row["done"]}
    asked, excluded = [], []
    for row in data["points"]:
        omission = row["id"].startswith("N")
        (excluded if omission else asked).append(
            point_row(row, approved_changes, word, source, exclusion=omission))
    changes = tuple((row["id"], row.get("point") or "—", source(plain(row["what"])), word("Keep"))
                    for row in kept)
    timeline, events, addition, _, _ = dates
    testing = []
    if asked or excluded:
        testing.append(word("See how each approved point was checked in the results above."))
    results = {row["result"] for row in data["checks"]}
    if "pass" in results and "fail" not in results:
        testing.append(word("The finished build also passed the project checks that applied to it."))
    next_steps = tuple(source(line) for heading in NEXT_STEPS for line in handover[heading])
    summary = tuple(map(source, prd["What it is"] + prd["Why"]))
    count = len(report.accepted_problems(data))
    if count:
        notice = ("{count} problem remains open. See the technical document." if count == 1
                  else "{count} problems remain open. See the technical document.")
        summary += (word(notice).format(count=count),)
    return (
        (paragraphs(summary, word("No summary is recorded.")),),
        (Block("table", tuple(asked), tuple(map(word, ("No.", "What you asked for", "Result", "Where to see it"))),
               (.08, .33, .19, .40), (2,), (0,)),) if asked
        else (paragraphs((), word("No delivery points are recorded.")),),
        (Block("table", changes, tuple(map(word, ("No.", "Point", "What was built", "Decision"))),
               (.08, .09, .69, .14), (3,), (0, 1)),) if changes
        else (paragraphs((), word("No changes were approved to keep.")),),
        exclusions(prd, tuple(excluded), word, source),
        (Block("timeline", timeline),
         Block("table", events, tuple(map(word, ("Date", "What happened", "Asked by", "Days", "Why and what it changed"))),
               (.16, .23, .17, .08, .36), (), (3,)) if events
         else paragraphs((), word("No change requests or delays are confirmed.")),
         Block("callout", ((addition,),))),
        (paragraphs(testing, word("No testing is recorded.")),),
        (Block("list", tuple((source(line),) for line in handover["What is handed over"])),)
        if handover["What is handed over"] else (paragraphs((), word("No handover items are recorded.")),),
        (paragraphs(next_steps, word("No next steps are recorded.")),),
        (Block("signoff", ((word("Prepared by"), prepared_by), (word("Accepted by"), client)),
               tuple(map(word, ("Name", "Signature", "Date")))),),
    )


def unchanged(text):
    return text


def build(project, scope, data, choice, values, *, language, source=unchanged, preview=False):
    word = document_language.load(language).__getitem__
    prd = source_sections(project, documents.PRD, scope.language, PRD_HEADINGS, values)
    handover = source_sections(project, HANDOVER, scope.language, HANDOVER_HEADINGS, values)
    sections = tuple(Section(i, word(title), ()) for i, title in enumerate(SECTION_TITLES, 1))
    full = data is not None and "points" in data and report.is_clean(data)
    dates = None
    if full:
        try:
            dates = reconciled_dates(data["dates"], word, source)
        except Refusal:
            if not preview:
                raise

    info = data["project"] if data else {}
    client = source(info.get("client", ""))
    prepared_by = source(choice["prepared_by"])
    version = source(choice["version"])
    if dates is not None:
        timeline, _, _, milestones, days = dates
        blocks = content_blocks(data, prd, handover, dates, prepared_by, client, word, source)
        sections = tuple(Section(section.number, section.title, items)
                         for section, items in zip(sections, blocks))

    detail_values = {
        "client": (word("Prepared for"), client),
        "prepared-by": (word("Prepared by"), prepared_by),
        "version": (word("Version"), version),
        "date": (word("Date"), choice["date"]),
        "status": (word("Status"), word("Final") if dates is not None and prepared_by else ""),
    }
    details = tuple(detail_values[key] for key in choice["details"] if detail_values[key][1])
    metrics = ()
    cover_blocks = []
    if dates is not None:
        metrics = ((str(len(data["points"])), word("approved points")),
                   (str(sum(row["decision"] == "keep" for row in data["changes"])), word("changes kept")),
                   (f"{days:+d}", word("days added")))
        # A long project keeps the detailed timeline inside the paginated section.
        if len(timeline) > 5:
            timeline = tuple(sorted((day, word(LABELS[kind])) for kind, day in milestones.items()))
        cover_blocks.append(Section(0, word("Project dates"), (Block("timeline", timeline),)))
    if handover["What is handed over"]:
        cover_blocks.append(Section(0, word("What you receive"),
                                    (Block("list", tuple((source(line),) for line in handover["What is handed over"][:2])),)))
    for heading in NEXT_STEPS:
        if handover[heading]:
            cover_blocks.append(Section(0, word("Next step"),
                                        (paragraphs(tuple(map(source, handover[heading][:1])), ""),)))
            break
    summary = tuple(map(source, prd["What it is"]))
    if language != scope.language:
        summary = (word(TRANSLATION_NOTICE), *summary)
    # Only the display values belong in the drawing model. The saved cover may
    # still hold the preparer's original name and version in the source language.
    layout = {key: choice[key] for key in first_page.LAYOUT_FIELDS}
    model = Document(source(scope.name), word(TITLE), language, first_page.LANGUAGES[language],
                     summary, detail_values, details, layout, metrics, tuple(cover_blocks),
                     sections, word(CREDIT) if choice["credit"] else "")
    guard_model(model, values)
    return model


def paired(project, scope, data, choice, values, *, language, source=unchanged, readme_present=False):
    from . import technical_content

    project_model = build(project, scope, data, choice, values, language=language, source=source)
    word = document_language.load(language).__getitem__
    notice = (word(TRANSLATION_NOTICE),) if language != scope.language else ()
    technical = replace(project_model, title=word("Technical Document"), cover_summary=notice,
                        cover_blocks=(), metrics=(),
                        sections=technical_content.build(project, scope, data, values,
                                                         scope.language, word, source,
                                                         readme_present=readme_present))
    guard_model(technical, values)
    return project_model, technical


def guard_model(model, values):
    if secrets.contains_secret_in_data(asdict(model), values):
        raise Refusal("Remove the known secret from the document content and replace it before trying again.")
