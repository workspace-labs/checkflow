"""Combine two finished checks of the same approved scope and round."""

from . import proof, secrets, validation
from .storage import CURRENT, OUTPUT, Refusal, json_bytes, load_check


SECOND = f"{OUTPUT}/second-check.json"
POINT_ORDER = (("covered", ""), ("partly", "untried"), ("changed", ""),
               ("partly", "wrong"), ("missing", ""))
CHECK_ORDER = ("does not apply", "pass", "fail")


def archive_name(number):
    return f"{OUTPUT}/check.before-merge-{number}.json"


def point_result(row):
    return row["mark"], row.get("gap", "")


def check_key(row):
    return row["group"], row["check"]


def results_and_evidence(data):
    return (
        {row["id"]: (point_result(row), row["proof"]) for row in data["points"]},
        {check_key(row): (row["result"], row["reason"]) for row in data["checks"]},
    )


def require_distinct(first, second):
    if results_and_evidence(first) == results_and_evidence(second):
        raise Refusal("The point and project check results and evidence are identical. "
                      "Supply a fresh independent check.")


def approved_points(data):
    return {(row["id"], row["text"], row["source"]) for row in data["points"]}


def match_inputs(first, second):
    if first["project"]["round"] != second["project"]["round"]:
        raise Refusal("Use two finished checks from the same round.")
    if approved_points(first) != approved_points(second):
        raise Refusal("Use two checks with the same point IDs, text and sources.")


def has_owner_decision(data):
    project = data["project"]
    return (project["language"] or project["client"]
            or any(row["decision"] != "not decided" or row["done"] for row in data["changes"])
            or any(row.get("accepted", "").strip() for row in data["problems"])
            or any(row["confirmed"] for row in data["dates"]))


def independent_input(project, name, checks, values):
    try:
        raw, data = load_check(project, name)
        if (secrets.contains_secret(raw.decode(errors="replace"), values)
                or secrets.contains_secret_in_data(data, values)):
            raise Refusal("Remove the known secret value and replace the secret before trying again.")
        validation.validate(data, checks)
        if data["project"].get("checkers", 1) != 1:
            raise Refusal("Supply a finished check from one checker.")
    except Refusal as error:
        raise Refusal(f"{name}: {error}") from None
    return raw, data


def combine_results(first, second, key, rank, field):
    by_key = {key(row): row for row in second}
    combined = []
    for left in first:
        right = by_key[key(left)]
        left_rank, right_rank = rank(left), rank(right)
        worse = right if right_rank > left_rank else left
        if field == "proof":
            selected = "first" if worse is left else "second"
            if left_rank == right_rank:
                selected = "both"
            evidence = proof.attributed(left[field], right[field], selected)
        else:
            evidence = proof.labelled(left[field], right[field])
        combined.append({**worse, field: evidence})
    return combined


def combine_rows(first, second, prefix, identity):
    used_ids = {row["id"] for row in (*first, *second)}
    seen = set()
    combined = []
    number = 1
    for rows, new_ids in ((first, False), (second, True)):
        for row in rows:
            words = tuple(row.get(field, "") for field in identity)
            if words in seen:
                continue
            seen.add(words)
            if new_ids:
                while f"{prefix}{number}" in used_ids:
                    number += 1
                row = {**row, "id": f"{prefix}{number}"}
                number += 1
            combined.append(row)
    return combined


def combine(first, second):
    changes = combine_rows(first["changes"], second["changes"], "C", ("kind", "what", "point"))
    problems = combine_rows(first["problems"], second["problems"], "P",
                            ("group", "line", "state", "next", "check"))
    higher_bars = dict.fromkeys(check["project"]["bar"] for check in (first, second)
                                if check["project"]["bar"] != "basic")
    return {
        **first,
        "project": {**first["project"], "checkers": 2, "bar": ", ".join(higher_bars) or "basic"},
        "points": combine_results(first["points"], second["points"], lambda row: row["id"],
                                  lambda row: POINT_ORDER.index(point_result(row)), "proof"),
        "checks": combine_results(first["checks"], second["checks"], check_key,
                                  lambda row: CHECK_ORDER.index(row["result"]), "reason"),
        "changes": [{**row, "decision": "not decided", "done": False} for row in changes],
        "problems": [{key: value for key, value in row.items() if key != "accepted"}
                     if row.get("accepted", "").strip() else row for row in problems],
    }


def run(project, first_raw, first, checks, scope, values):
    archive = archive_name(first["project"]["round"])
    already_merged = "This round was already merged. Keep the existing first-check archive."
    if first["project"].get("checkers", 1) == 2 or project.read(archive) is not None:
        raise Refusal(already_merged)
    if has_owner_decision(first):
        raise Refusal("Merge before recording any owner decisions in the first check.")
    second_raw, second = independent_input(project, SECOND, checks, values)
    match_inputs(first, second)
    validation.validate_scope(second, scope)
    require_distinct(first, second)
    merged = combine(first, second)
    validation.validate(merged, checks)
    if secrets.contains_secret_in_data(merged, values):
        raise Refusal("Remove the known secret value and replace the secret before trying again.")
    contents = json_bytes(merged)
    with project.writer():
        if project.read(archive) is not None:
            raise Refusal(already_merged)
        if project.read(CURRENT) != first_raw or project.read(SECOND) != second_raw:
            raise Refusal("Read both checks again. One changed during the merge.")
        project.write(archive, first_raw)
        try:
            project.write(CURRENT, contents)
        except (OSError, Refusal):
            project.path(archive).unlink()
            raise


def report_inputs(project, current, checks, values):
    archive = archive_name(current["project"]["round"])
    first_raw, first = independent_input(project, archive, checks, values)
    second_raw, second = independent_input(project, SECOND, checks, values)
    match_inputs(current, first)
    match_inputs(first, second)
    require_distinct(first, second)
    first_points = {row["id"]: point_result(row) for row in first["points"]}
    first_checks = {check_key(row): row["result"] for row in first["checks"]}
    points = {row["id"] for row in second["points"] if first_points[row["id"]] != point_result(row)}
    disputed_checks = {check_key(row) for row in second["checks"]
                       if first_checks[check_key(row)] != row["result"]}
    return (points, disputed_checks), {archive: first_raw, SECOND: second_raw}
