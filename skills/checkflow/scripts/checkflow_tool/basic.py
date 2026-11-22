"""The fixed basic bar for this build."""

import json
from pathlib import Path


BASIC_ASSET = Path(__file__).resolve().parents[2] / "assets" / "checks" / "basic.json"


def basic_checks():
    return [(group["group"], check["check"])
            for group in json.loads(BASIC_ASSET.read_text(encoding="utf-8"))
            for check in group["checks"]]


def empty_checks(checks):
    return [{"group": group, "check": name, "result": "", "reason": "",
             "bar": "basic", "round": 1} for group, name in checks]
