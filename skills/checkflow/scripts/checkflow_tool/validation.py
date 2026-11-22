"""Validate the check file against the approved data shape and basic bar."""

import re
from collections import Counter
from datetime import date

from .storage import Refusal


LISTS = ("points", "checks", "changes", "dates", "problems")
MARKS = ("covered", "partly", "missing", "changed")
PARTLY_GAPS = ("wrong", "untried")
RESULTS = ("pass", "fail", "does not apply")
DECISIONS = ("fix back", "keep", "not decided")
DATE_KINDS = ("start", "planned end", "real end", "change request", "delay")
SECURITY_CHECK_GROUPS = {"Who gets in", "Secrets", "Bad input", "The connection"}
PACKAGE_SECURITY_CHECK = "The packages it uses have no known serious weakness"

PROJECT = {"name": str, "client": str, "language": ("", "en", "ar", "both"),
           "round": int, "bar": str, "not_approved": list, "checkers": int}
ROWS = {
    "points": {"id": str, "source": str, "text": str, "mark": MARKS, "gap": str,
               "proof": str, "round": int},
    "checks": {"group": str, "check": str, "result": RESULTS, "reason": str, "bar": ("basic",),
               "round": int},
    "changes": {"id": str, "kind": ("different", "extra"), "what": str, "point": str,
                "decision": DECISIONS, "done": bool},
    "dates": {"id": str, "kind": DATE_KINDS, "date": str, "what": str, "asked_by": str,
              "days_added": int, "reason": str, "source": str, "confirmed": bool},
    "problems": {"id": str, "group": str, "line": str, "state": ("fixed", "still open"),
                 "next": str, "accepted": str, "check": str},
}
OPTIONAL = {
    "points": {"gap"},
    "changes": {"point"},
    "dates": {"what", "asked_by", "days_added", "reason"},
    "problems": {"next", "accepted", "check"},
}


def fields(data, schema, where, optional=()):
    if not isinstance(data, dict):
        raise Refusal(f"Make {where} a JSON object.")
    for name in data:
        if name not in schema:
            raise Refusal(f"Remove the unknown field {name!r} from {where}.")
    for name, rule in schema.items():
        if name not in data:
            if name in optional:
                continue
            raise Refusal(f"Add the required field {name} to {where}.")
        value = data[name]
        if isinstance(rule, tuple):
            if value not in rule:
                choices = ", ".join(repr(choice) for choice in rule)
                raise Refusal(f"Set {where}.{name} to one of {choices}.")
        elif type(value) is not rule:
            raise Refusal(f"Set {where}.{name} to type {rule.__name__}.")


def need_text(row, names, where):
    for name in names:
        if not row[name].strip():
            raise Refusal(f"Fill in {where}.{name}.")


def row_round(row, maximum, where):
    if not 1 <= row["round"] <= maximum:
        raise Refusal(f"Set {where}.round between 1 and the current project round.")


def point_gap(row):
    gap = row.get("gap", "")
    where = f"point {row['id']}.gap"
    if gap and gap not in PARTLY_GAPS:
        raise Refusal(f"Set {where} to 'wrong', 'untried' or an empty string.")
    if row["mark"] == "partly" and not gap:
        raise Refusal(f"Set {where} to 'wrong' or 'untried' for a partly point.")
    if row["mark"] != "partly" and gap:
        raise Refusal(f"Leave {where} empty unless the point is marked partly.")


def no_duplicate(items, label):
    for key, count in Counter(items).items():
        if count > 1:
            raise Refusal(f"Keep only one row for {label} {key!r}.")


def problem_line(line, where):
    if (len(line) > 200 or len(line.splitlines()) != 1 or line != line.splitlines()[0]
            or "\x60\x60\x60" in line or "~~~" in line or line.startswith(("    ", "\t"))
            or re.search(r"<\s*/?\s*(?:pre|code)\b", line, re.IGNORECASE)):
        raise Refusal(f"Write {where}.line as one line of up to 200 characters without a code block.")


def date_value(value, where):
    try:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError
        date.fromisoformat(value)
    except ValueError:
        raise Refusal(f"Set {where}.date to a real date in YYYY-MM-DD format.") from None


def validate_project(project):
    fields(project, PROJECT, "project", optional=("checkers",))
    if project.get("checkers", 1) not in (1, 2):
        raise Refusal("Set project.checkers to 1 or 2.")


def validate(data, checks):
    fields(data, {"project": dict, **dict.fromkeys(LISTS, list)}, "check.json")
    project = data["project"]
    validate_project(project)
    need_text(project, ("name", "bar"), "project")
    if project["round"] < 1:
        raise Refusal("Set project.round to a positive integer.")
    if any(not isinstance(path, str) or not path.strip() for path in project["not_approved"]):
        raise Refusal("List file names in project.not_approved.")

    for name in LISTS:
        for index, row in enumerate(data[name], start=1):
            where = f"{name} row {index}"
            fields(row, ROWS[name], where, OPTIONAL.get(name, ()))
            if name == "points":
                need_text(row, ("id", "source", "text", "proof"), where)
                point_gap(row)
                row_round(row, project["round"], where)
            elif name == "checks":
                need_text(row, ("group", "check", "reason"), where)
                row_round(row, project["round"], where)
            elif name == "changes":
                need_text(row, ("id", "what"), where)
            elif name == "dates":
                need_text(row, ("id", "source"), where)
                date_value(row["date"], where)
            else:
                need_text(row, ("id", "group", "line"), where)
                problem_line(row["line"], where)

    for name in ("points", "changes", "dates", "problems"):
        no_duplicate((row["id"] for row in data[name]), name)
    validate_checks(data, checks)
    validate_links(data, {group for group, _ in checks})


def validate_checks(data, checks):
    actual = [(row["group"], row["check"]) for row in data["checks"]]
    no_duplicate(actual, "check")
    actual_set, required = set(actual), set(checks)
    for group, name in checks:
        if (group, name) not in actual_set:
            raise Refusal(f"Restore the basic check {name!r} in {group}.")
    if actual_set - required:
        group, name = sorted(actual_set - required)[0]
        raise Refusal(f"Remove the unknown check {name!r} in {group!r}.")


def validate_links(data, groups):
    point_ids = {row["id"] for row in data["points"]}
    linked = set()
    for row in data["changes"]:
        point = row.get("point")
        if point:
            if point not in point_ids:
                raise Refusal(f"Fix changes row {row['id']!r}.point to name an existing point.")
            if row["kind"] == "different":
                linked.add(point)
    for row in data["points"]:
        if row["mark"] == "changed" and row["id"] not in linked:
            raise Refusal(f"Give changed point {row['id']} a different row in changes that points to it.")
    failed_checks = {(row["group"], row["check"]) for row in data["checks"]
                     if row["result"] == "fail"}
    for row in data["problems"]:
        where = f"problems row {row['id']!r}"
        if row["group"] not in groups:
            raise Refusal(f"Set {where}.group to one of the ten groups.")
        if row.get("accepted", "").strip() and row["state"] != "still open":
            raise Refusal(f"Fill in {where}.accepted only when the problem is still open.")
        check = row.get("check", "")
        if not check.strip():
            continue
        if (row["group"], check) not in failed_checks:
            raise Refusal(f"Set {where}.check to the exact name of a failed check in the same group, "
                          "or leave it empty.")
        if row["group"] not in SECURITY_CHECK_GROUPS and check != PACKAGE_SECURITY_CHECK:
            raise Refusal(f"Set {where}.check to a failed security check, or leave it empty.")


def validate_scope(data, scope):
    if data["project"]["name"] != scope.name:
        raise Refusal("Run next-round to read the current name from the approved PRD.")
    if data["project"]["not_approved"] != scope.not_approved:
        raise Refusal("Run next-round to read the current approval stamps.")
    actual = {row["id"]: row for row in data["points"]}
    for point in scope.points:
        point_id = point["id"]
        if point_id not in actual:
            raise Refusal(f"Point {point_id} is missing from check.json. Run next-round to read the approved points.")
        row = actual.pop(point_id)
        if row["text"] != point["text"] or row["source"] != point["source"]:
            raise Refusal(f"Point {point_id} no longer matches its approved document. Run next-round.")
    if actual:
        point_id = next(iter(actual))
        raise Refusal(f"Point {point_id!r} is no longer approved. Run next-round.")
