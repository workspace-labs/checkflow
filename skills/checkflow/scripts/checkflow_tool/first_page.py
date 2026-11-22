"""Read and validate the pieces of an approved first page."""

import json

from .storage import OUTPUT, Refusal, unique_fields
from .validation import date_value


CHOICE = f"{OUTPUT}/first-page.json"
DETAILS = ("client", "prepared-by", "version", "date", "status")
LEGACY_DETAILS = ("client", "round", "verdict", "real-end")
DOCUMENT_FIELDS = ("prepared_by", "version", "date")
LAYOUT_FIELDS = {"frame", "name_position", "details_style", "details", "credit"}
FRAMES = ("register", "band", "side")
POSITIONS = ("center", "start")
DETAIL_STYLES = ("row", "list")
LANGUAGES = {"en": "ltr", "ar": "rtl"}
PRESETS = {
    "register": ("C · The register", "center", "row"),
    "band": ("A · The band", "start", "row"),
    "side": ("B · The side", "start", "list"),
}


def defaults(frame):
    _, position, style = PRESETS[frame]
    return {"frame": frame, "name_position": position, "details_style": style,
            "details": list(DETAILS), "credit": True, **dict.fromkeys(DOCUMENT_FIELDS, "")}


def validate_choice(choice):
    if (not isinstance(choice, dict) or not LAYOUT_FIELDS <= choice.keys()
            or choice.keys() - (LAYOUT_FIELDS | set(DOCUMENT_FIELDS))):
        raise Refusal("Correct the fields in docs/checkflow/first-page.json.")
    for key, choices in (("frame", FRAMES), ("name_position", POSITIONS), ("details_style", DETAIL_STYLES)):
        if choice[key] not in choices:
            raise Refusal(f"Choose a known first-page {key}.")
    details = choice["details"]
    if (not isinstance(details, list) or any(detail not in DETAILS for detail in details)
            or len(details) != len(set(details))):
        raise Refusal("Choose unique first-page details from client, prepared-by, version, date and status.")
    if type(choice["credit"]) is not bool:
        raise Refusal("Choose whether the first-page credit setting is on or off.")
    for field in DOCUMENT_FIELDS:
        if not isinstance(choice.get(field, ""), str):
            raise Refusal(f"Save {field} as text in docs/checkflow/first-page.json.")
    choice = {**choice, **{field: choice.get(field, "").strip() for field in DOCUMENT_FIELDS}}
    if choice["date"]:
        date_value(choice["date"], "first-page.json")
    return choice


def read_choice(raw):
    if raw is None:
        return None
    try:
        choice = json.loads(raw, object_pairs_hook=unique_fields)
    except (ValueError, RecursionError, Refusal):
        raise Refusal("Fix the JSON in docs/checkflow/first-page.json.") from None
    if isinstance(choice, dict) and choice.keys() == LAYOUT_FIELDS:
        details = choice["details"]
        if (isinstance(details, list) and all(key in LEGACY_DETAILS for key in details)
                and len(details) == len(set(details))):
            # Keep the layout and replace the former default fields with the approved ones.
            choice["details"] = (list(DETAILS) if details == list(LEGACY_DETAILS)
                                 else [key for key in details if key in DETAILS])
    return validate_choice(choice)


def with_options(args, base):
    choice = dict(base)
    choice.update({field: getattr(args, field) for field in ("name_position", "details_style", "credit")
                   if getattr(args, field, None) is not None})
    for field, flag in (("prepared_by", "prepared_by"), ("version", "version"), ("date", "document_date")):
        value = getattr(args, flag, None)
        if value is not None:
            choice[field] = value
    if args.details is not None:
        choice["details"] = [key.strip() for key in args.details.split(",")] if args.details else []
    return validate_choice(choice)


def proposals(args, saved):
    frame = args.frame or (saved["frame"] if saved else "register")
    result = []
    for option, (label, _, _) in PRESETS.items():
        choice = dict(saved) if saved and saved["frame"] == option else defaults(option)
        if saved:
            choice.update({field: saved[field] for field in DOCUMENT_FIELDS})
        if frame == option:
            choice = with_options(args, choice)
        result.append((label, choice))
    return result
