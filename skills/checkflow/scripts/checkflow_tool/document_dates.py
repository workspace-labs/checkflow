"""Reconcile recorded dates before they reach the client."""

from datetime import date, timedelta

from .storage import Refusal


MILESTONES = ("start", "planned end", "real end")
LABELS = {"start": "Start", "planned end": "Planned end", "real end": "Real end",
          "change request": "Change request", "delay": "Delay"}


def reconciled_dates(rows, word, source):
    milestone_rows = {}
    event_rows = []
    for index, row in enumerate(rows, 1):
        kind = row["kind"]
        where = f"dates row {index} ({row['id']})"
        if kind not in MILESTONES and "days_added" not in row:
            raise Refusal(f"Ask the owner for days_added on {where}.")
        if not row["confirmed"]:
            continue
        if kind in MILESTONES:
            if kind in milestone_rows:
                raise Refusal(f"Confirm exactly one {kind} row in dates. Review {where}.")
            milestone_rows[kind] = (row["date"], where)
        else:
            required = ("what", "reason", "asked_by") if kind == "change request" else ("what", "reason")
            for field in required:
                if not row.get(field, "").strip():
                    raise Refusal(f"Ask the owner for {field} on {where}.")
            event_rows.append((row, where))

    for kind in MILESTONES:
        if kind not in milestone_rows:
            raise Refusal(f"Ask the owner to confirm one {kind} row in dates.")
    milestones = {kind: day for kind, (day, _) in milestone_rows.items()}
    start, start_where = milestone_rows["start"]
    planned, real = milestones["planned end"], milestones["real end"]

    # The check has already validated each date as a fixed-width ISO date.
    for kind in ("planned end", "real end"):
        if start > milestones[kind]:
            raise Refusal(f"Review {start_where} with the owner because the start date {start} "
                          f"is after the {kind} date {milestones[kind]}.")
    for row, where in event_rows:
        if not start <= row["date"] <= real:
            raise Refusal(f"Review {where} with the owner because the {row['kind']} date {row['date']} "
                          f"is outside the project dates {start} through {real}.")

    events = sorted((row for row, _ in event_rows), key=lambda row: row["date"])
    days = sum(row["days_added"] for row in events)
    try:
        calculated = (date.fromisoformat(planned) + timedelta(days=days)).isoformat()
    except OverflowError:
        raise Refusal("Check the confirmed days_added values. They produce a date outside the calendar.") from None
    if calculated != real:
        raise Refusal(f"Review the dates with the owner. The confirmed days give {calculated}, "
                      f"but the recorded real end is {real}.")

    label = {kind: word(key) for kind, key in LABELS.items()}
    days_text = word("{days:+d} days")
    timeline = [(milestones[kind], label[kind]) for kind in MILESTONES]
    timeline.extend((row["date"], word("{label} ({days})").format(
        label=label[row["kind"]], days=days_text.format(days=row["days_added"])))
        for row in events)
    timeline.sort(key=lambda row: row[0])
    table = tuple(
        (row["date"], word("{label} · {what}").format(
            label=label[row["kind"]], what=source(row["what"])),
         source(row.get("asked_by", "").strip()) or "—",
         f"{row['days_added']:+d}", source(row["reason"])) for row in events
    )
    terms = " ".join(days_text.format(days=row["days_added"]) for row in events)
    terms = terms or days_text.format(days=0)
    return tuple(timeline), table, f"{planned} {terms} = {real}", milestones, days
