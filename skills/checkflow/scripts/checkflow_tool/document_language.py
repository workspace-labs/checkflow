"""Load the words shared by both renderers and document content models."""

import json
from functools import lru_cache
from pathlib import Path


LANGUAGE_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "languages"


@lru_cache(maxsize=2)
def load(language):
    with (LANGUAGE_ASSETS / f"{language}.json").open(encoding="utf-8") as source:
        return json.load(source)
