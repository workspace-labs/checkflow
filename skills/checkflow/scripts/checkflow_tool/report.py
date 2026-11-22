"""Render a validated full check for the owner."""

from collections import Counter

from .proof import owner_text


POINT_SECTIONS = (
    ("missing", "", "Missing"),
    ("partly", "wrong", "Partly: something is wrong"),
    ("partly", "untried", "Partly: works so far, needs your try"),
    ("changed", "", "Changed"),
    ("covered", "", "Covered"),
)


def plain(text):
    for char in "\\`*_[]<>!&~":
        if char in "<>&":
            continue
        text = text.replace(char, "\\" + char)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def accepted_problems(data):
    return tuple(row for row in data["problems"]
                 if row["state"] == "still open" and row.get("accepted", "").strip())


def verdict_gaps(data, accepted):
    accepted_checks = {(row["group"], row.get("check")) for row in accepted}
    project = data["project"]
    counts = Counter(row["mark"] for row in data["points"])
    partly = Counter(row["gap"] for row in data["points"] if row["mark"] == "partly")
    wrong, untried = partly["wrong"], partly["untried"]
    gaps = []
    if project["bar"] != "basic":
        gaps.append(f"The higher bar ({plain(project['bar'])}) is not supported yet.")
    for count, label in [
        (counts["missing"], "missing client points"),
        (wrong, "client point with something wrong" if wrong == 1 else "client points with something wrong"),
        (untried, "client point that works so far and needs the owner's try" if untried == 1
         else "client points that work so far and need the owner's try"),
        (sum(row["result"] == "fail" and (row["group"], row["check"]) not in accepted_checks
             for row in data["checks"]), "failed project checks"),
        (sum(row["decision"] == "not decided" for row in data["changes"]), "undecided changes"),
        (sum(not row["done"] for row in data["changes"]), "changes not done"),
        (sum(row["state"] == "still open" for row in data["problems"]) - len(accepted), "open problems"),
    ]:
        if count:
            gaps.append(f"{count} {label}")
    return gaps


def is_clean(data):
    return not verdict_gaps(data, accepted_problems(data))


def verdict(data):
    accepted = accepted_problems(data)
    gaps = verdict_gaps(data, accepted)
    if gaps:
        return ["Not clean", "", *[f"- {gap}" for gap in gaps]]
    if accepted:
        noun = "problem" if len(accepted) == 1 else "problems"
        return [f"Clean, with {len(accepted)} {noun} accepted by the owner"]
    return ["Clean"]


def full_check(data, checks, same_builder, disagreements=None):
    project = data["project"]
    point_disagreements, check_disagreements = disagreements or (set(), set())
    who = ["Checked by the same agent that built it." if same_builder else "The checker."]
    if project.get("checkers", 1) == 2:
        point_count, check_count = len(point_disagreements), len(check_disagreements)
        point_label = "client point" if point_count == 1 else "client points"
        check_label = "project check" if check_count == 1 else "project checks"
        who = (who if same_builder else []) + [
            "Two independent checkers ran. The worse result is shown for each point.",
            f"Disagreements: {point_count} {point_label} and {check_count} {check_label}.",
        ]
    lines = [
        "# Full check", "", f"Project: {plain(project['name'])}", "",
        "A Clean result means no gap was found. Bugs may still exist.",
        "The tool cannot tell whether a proof is true. Read the proofs before trusting Clean.", "",
        "## Verdict", "", *verdict(data), "",
        "## Who checked", "", *who, "",
        f"Round: {project['round']}", "", "Bar used: basic", "",
        "## Documents without approval", "",
    ]
    lines.extend((f"- {plain(path)}" for path in project["not_approved"]) if project["not_approved"] else ["None."])
    lines.extend(["", "## Client points"])
    for mark, gap, heading in POINT_SECTIONS:
        lines.extend(["", f"### {heading}", ""])
        points = [row for row in data["points"] if row["mark"] == mark and row.get("gap", "") == gap]
        if not points:
            lines.append("None.")
        for row in points:
            disputed = " · Checkers disagreed" if row["id"] in point_disagreements else ""
            lines.append(f"- **{plain(row['id'])}** · {plain(row['source'])} · round {row['round']}{disputed}")
            lines.extend(f"  > {plain(line)}" for line in row["text"].splitlines())
            evidence = owner_text(row["proof"])
            lines.extend(["", f"  Proof: {plain(evidence).replace(chr(10), ' ')}", ""])

    lines.extend(["", "## Changes", ""])
    if not data["changes"]:
        lines.append("None.")
    for row in data["changes"]:
        target = f" · {plain(row['point'])}" if row.get("point") else ""
        done = "done" if row["done"] else "open"
        lines.append(f"- **{plain(row['id'])}** · {row['kind']}{target} · {plain(row['what'])}")
        lines.append(f"  Decision: {row['decision']} · {done}")

    lines.extend(["", "## Project checks"])
    by_key = {(row["group"], row["check"]): row for row in data["checks"]}
    for group in dict.fromkeys(group for group, _ in checks):
        names = [name for group_name, name in checks if group_name == group]
        rows = [by_key[group, name] for name in names]
        results = {row["result"] for row in rows}
        outcome = "fail" if "fail" in results else "pass" if "pass" in results else "does not apply"
        counts = Counter(row["result"] for row in rows)
        summary = ", ".join(f"{counts[result]} {result}" for result in ("pass", "fail", "does not apply")
                            if counts[result])
        lines.extend(["", f"### {group}", "", f"Group result: {outcome} ({summary}).", ""])
        for row in rows:
            disputed = " · Checkers disagreed" if (group, row["check"]) in check_disagreements else ""
            lines.append(f"- **{row['result']}** · {plain(row['check'])}{disputed}. "
                         f"Reason: {plain(row['reason']).replace(chr(10), ' ')}")

    lines.extend(["", "## Problems found", ""])
    if not data["problems"]:
        lines.append("None.")
    for row in data["problems"]:
        next_step = f" · Next: {plain(row['next'])}" if row.get("next") else ""
        reason = plain(" ".join(row.get("accepted", "").split()))
        acceptance = f" · Accepted by the owner: {reason}" if reason else ""
        lines.append(f"- **{plain(row['id'])}** · {row['group']} · {row['state']}: "
                     f"{plain(row['line'])}{next_step}{acceptance}")
    return "\n".join(lines) + "\n"
