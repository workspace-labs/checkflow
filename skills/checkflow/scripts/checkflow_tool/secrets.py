"""Find known literal settings values without displaying them."""

import re
from dataclasses import dataclass

SETTING_FILES = (".env", ".env.local")
ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
SECRET_NAME = re.compile(
    r"(?:^|_)(?:PASSWORD|PASSWD|PASSCODE|SECRET|TOKEN|CREDENTIALS?|API_KEY|PRIVATE_KEY|ACCESS_KEY)(?:_|$)"
)
LITERAL = re.compile(r"""^(?:"([^"]*)"|'([^']*)'|([^"'\s][^#]*?))\s*(?:\s+#.*)?$""")
QUOTED_END = r"(?=$|[\s,.;:!?)\]}\x60])"
ASSIGNMENT_END = r"(?=$|[\s)\]}\x60]|[,.;:!?](?=$|[\s)\]}\x60]))"
FIELD_END = r"(?=[ \t]*(?:$|[)\]}\x60]|[,.;!?](?=$|[\s)\]}\x60])))"


@dataclass(frozen=True)
class KnownSecret:
    name: str
    value: str
    distinctive: bool
    assignment: re.Pattern

    def occurs_in(self, text):
        return (self.distinctive and self.value in text) or bool(self.assignment.search(text))


def distinctive(value):
    if len(value) < 8 or any(char.isspace() for char in value):
        return False
    mixed = any(char.isalpha() for char in value) and any(char.isdigit() for char in value)
    symbol = any(not char.isalnum() and char not in "._-" for char in value)
    return mixed or symbol


def assignment_pattern(name, value):
    name = f"(?i:{re.escape(name)})"
    label = rf"""(?<!\w)(?:{name}|"{name}"|'{name}'|\x60{name}\x60|\*\*{name}\*\*)[ \t]*"""
    value = re.escape(value)
    quoted = rf"""(?:"{value}"|'{value}'|\x60{value}\x60){QUOTED_END}"""
    assignment = rf"=[ \t]*(?:{quoted}|{value}{ASSIGNMENT_END})"
    field = rf":[ \t]*(?:{quoted}|{value}{FIELD_END})"
    return re.compile(rf"{label}(?:{assignment}|{field})")


def known_values(project):
    settings = set()
    for filename in SETTING_FILES:
        for line in (project.read_text(filename) or "").splitlines():
            setting = ASSIGNMENT.match(line)
            if not setting or not SECRET_NAME.search(setting[1].upper()):
                continue
            literal = LITERAL.fullmatch(setting[2])
            if literal:
                quoted_double, quoted_single, bare = literal.groups()
                value = bare.strip() if bare is not None else (
                    quoted_double if quoted_double is not None else quoted_single
                )
                if value:
                    settings.add((setting[1].upper(), value))
    return [KnownSecret(name, value, distinctive(value), assignment_pattern(name, value))
            for name, value in sorted(settings)]


def contains_secret(text, values):
    return any(secret.occurs_in(text) for secret in values)


def contains_secret_in_data(data, values):
    if not values:
        return False
    if isinstance(data, str):
        return contains_secret(data, values)
    if isinstance(data, (list, tuple)):
        return any(contains_secret_in_data(item, values) for item in data)
    if isinstance(data, dict):
        return any(
            any(name.upper() == secret.name and item == secret.value for secret in values)
            or contains_secret(name, values)
            or contains_secret_in_data(item, values)
            for name, item in data.items()
        )
    return False
