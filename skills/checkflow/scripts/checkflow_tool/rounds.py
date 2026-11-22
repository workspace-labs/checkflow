"""Carry evidence forward only when its client point can be identified."""

from collections import defaultdict


def match_points(old_points, new_points):
    old_by_id = {(row["source"], row["id"]): row for row in old_points}
    old_by_text = defaultdict(list)
    new_by_text = defaultdict(list)
    for row in old_points:
        old_by_text[row["source"], row["text"]].append(row)
    for row in new_points:
        new_by_text[row["source"], row["text"]].append(row)

    for row in new_points:
        if row["id"].startswith("M"):
            prior = old_by_id.get((row["source"], row["id"]))
        else:
            key = row["source"], row["text"]
            candidates = old_by_text[key]
            prior = candidates[0] if len(candidates) == len(new_by_text[key]) == 1 else None
        yield row, prior


def advance(data, scope):
    links = {}
    points = []
    for row, prior in match_points(data["points"], scope.points):
        if prior is not None:
            links[prior["id"]] = row["id"]
        if prior is not None and prior["text"] == row["text"]:
            points.append({**prior, "id": row["id"], "gap": prior.get("gap", "")})
        else:
            points.append(row)

    changes = []
    for row in data["changes"]:
        if row.get("point"):
            row = {**row, "point": links.get(row["point"], "")}
        changes.append(row)
    project = {**data["project"], "round": data["project"]["round"] + 1,
               "name": scope.name, "not_approved": scope.not_approved, "checkers": 1}
    return {**data, "project": project, "points": points, "changes": changes}
