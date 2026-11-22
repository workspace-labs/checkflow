"""Keep the owner's confirmation tied to the reviewed translation rows."""

import hashlib
import json
import re
import unicodedata

from .storage import OUTPUT, Refusal, json_bytes, unique_fields


def filename(language):
    return f"{OUTPUT}/translation-{language}.json"


def read(raw, language):
    path = filename(language)
    if raw is None:
        raise Refusal(f"{path} is missing. Run translate with --language {language}.")
    try:
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_fields)
    except (ValueError, RecursionError, Refusal):
        raise Refusal(f"Fix the JSON in {path}.") from None
    fields = {"language", "confirmed", "rows"}
    if (not isinstance(data, dict) or not fields <= data.keys()
            or data.keys() - fields - {"confirmed_digest"}
            or data["language"] != language or type(data["confirmed"]) is not bool
            or not isinstance(data["rows"], list)):
        raise Refusal(f"Correct the language, confirmed and rows fields in {path}.")
    digest = data.get("confirmed_digest", "")
    if not isinstance(digest, str) or (digest and not re.fullmatch("[0-9a-f]{64}", digest)):
        raise Refusal(f"Run translate to prepare a new confirmation in {path}.")
    seen = set()
    for row in data["rows"]:
        if (not isinstance(row, dict) or row.keys() != {"source", "text"}
                or not isinstance(row["source"], str) or not row["source"].strip()
                or not isinstance(row["text"], str)
                or row["source"] in seen):
            raise Refusal(f"Use distinct sources and text strings for the rows in {path}.")
        seen.add(row["source"])
    return data


class Sources:
    def __init__(self):
        self.texts = {}

    def collect(self, text):
        if needs_translation(text):
            self.texts.setdefault(text, "")
        return text


def needs_translation(text):
    return any(char.isalpha() for char in text)


def has_arabic_letters(text):
    return any(char.isalpha() and "ARABIC" in unicodedata.name(char, "") for char in text)


def wrong_language(text, language):
    if language == "en":
        return has_arabic_letters(text)
    # Catch plain English prose left in a translated row. A name or an identifier
    # can legitimately remain in Latin script and is part of the owner's review.
    return (not has_arabic_letters(text)
            and bool(re.search(r"[A-Za-z]+\s+[a-z]+(?=[\s.!?]|$)", text)))


def rows_digest(data):
    rows = [(row["source"], row["text"]) for row in data["rows"]]
    return hashlib.sha256(json_bytes([data["language"], rows])).hexdigest()


def is_confirmed(data):
    return data["confirmed"] and data.get("confirmed_digest") == rows_digest(data)


def confirmed(data):
    return {**data, "confirmed": True, "confirmed_digest": rows_digest(data)}


def refreshed(existing, language, texts):
    previous = {row["source"]: row["text"] for row in existing["rows"]} if existing else {}
    draft = {"language": language, "confirmed": False, "confirmed_digest": "",
             "rows": [{"source": text, "text": previous.get(text, "")} for text in texts]}
    if existing and is_confirmed(existing) and existing["confirmed_digest"] == rows_digest(draft):
        return confirmed(draft)
    return draft


def reviewed(data, language, texts=None, *, confirm=False, preview=False):
    path = filename(language)
    translations = {row["source"]: row["text"] for row in data["rows"]}
    if texts is not None and translations.keys() != texts.keys():
        raise Refusal(f"The source text changed in {path}. Run translate and review the changes.")
    for index, text in enumerate(translations.values(), 1):
        if not text.strip():
            raise Refusal(f"Translate row {index} in {path}. Its text is empty.")
        if wrong_language(text, language):
            raise Refusal(f"Translate row {index} in {path}. Its text is still in the source language.")
    if not (confirm or preview or is_confirmed(data)):
        raise Refusal(f"The owner must confirm {path} after reading the translation.")

    def translated(source):
        if not needs_translation(source):
            return source
        if source not in translations:
            raise Refusal(f"The source text changed in {path}. Run translate and review the changes.")
        return translations[source]

    return translated
