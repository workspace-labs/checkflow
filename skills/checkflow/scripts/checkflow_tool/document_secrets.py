"""Refuse credential-bearing document source text without quoting it."""

import json
import re

from .secrets import SECRET_NAME, contains_secret
from .storage import Refusal


SETTING = re.compile(
    r"""(?<![\w./-])(?:[\x60"']|\*\*)?([A-Za-z_][A-Za-z0-9_]*)(?:[\x60"']|\*\*)?[ \t]*(=|:)"""
)
LONG_OPTION = re.compile(r"""(?<![\w-])--([A-Za-z][A-Za-z0-9_-]*)(?:[ \t]+|=)""")
SHORT_PASSWORD = re.compile(r"""(?:^|[\s"'\x60])-p(?=\S)""")
AUTHORIZATION = re.compile(
    r"""(?i)\bauthorization(?:["'\x60]|\*\*)?[ \t]*:[ \t]*(?:\*\*[ \t]*)?"""
    r"""(?:(?:basic|bearer|digest|negotiate)[ \t]+)?"""
)
BEARER = re.compile(r"""(?im)(?:^[ \t]*|(?<=['"\x60]))bearer(?:[ \t]*:[ \t]*|[ \t]+)""")
ADDRESS = re.compile(
    r"""(?i)(?:\b[a-z][a-z0-9+.-]*://|(?<![\w:/])//)[^\s:/@"'<>\x60]+:([^\s/@"'\x60]+)@"""
)
VALUE = re.compile(
    r"""[ \t]*(?:\*\*[ \t]*)?(?:"([^"\r\n]+)"|'([^'\r\n]+)'|"""
    r"""\x60([^\x60\r\n]+)\x60|([^\s;"'|\x60]+))"""
)
REFERENCE = re.compile(r"""(?:\$(?:[A-Za-z_]\w*|\{[A-Za-z_]\w*\})|%[A-Za-z_]\w*%|<[\w.-]+>)""")
DATABASE_PASSWORD_NAMES = {"PGPASSWORD", "MYSQL_PWD"}
JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
LINE_BREAK = re.compile(r"\r\n?|\n")


def literal_value(tail):
    match = VALUE.match(tail)
    if match is None:
        return False
    value = next(part for part in match.groups() if part is not None)
    return not REFERENCE.fullmatch(value)


def credential_name(name):
    name = name.upper().replace("-", "_")
    return name in DATABASE_PASSWORD_NAMES or bool(SECRET_NAME.search(name))


def credential_syntax(text, setting_names):
    for match in SETTING.finditer(text):
        name, separator = match.groups()
        named = name in setting_names or (credential_name(name) and (separator == "=" or name.isupper()))
        if named and literal_value(text[match.end():]):
            return True
    if any(credential_name(match[1]) and literal_value(text[match.end():])
           for match in LONG_OPTION.finditer(text)):
        return True
    for pattern in (AUTHORIZATION, BEARER, SHORT_PASSWORD):
        if any(literal_value(text[match.end():]) for match in pattern.finditer(text)):
            return True
    return any(not REFERENCE.fullmatch(match[1]) for match in ADDRESS.finditer(text))


def refuse(path, number):
    raise Refusal(
        f"Remove and replace the secret in {path}, line {number}. "
        "Use settings by name without literal values."
    )


def guard_line(path, number, text, values, *, setting_names=()):
    if contains_secret(text, values) or credential_syntax(text, setting_names):
        refuse(path, number)


def guard_json(path, raw, values):
    if raw is None:
        return
    # Decode the file the same way as json.loads(bytes), then read string
    # tokens individually to keep their physical line numbers.
    source = raw.decode(json.detect_encoding(raw), errors="surrogatepass")
    number = 1
    previous_end = 0
    previous = ""
    for match in JSON_STRING.finditer(source):
        between = source[previous_end:match.start()]
        number += len(LINE_BREAK.findall(between))
        value = json.loads(match[0])
        guard_line(path, number, value, values)
        if LINE_BREAK.search(value):
            guard_line(path, number, " ".join(value.split()), values)
        if between.strip() == ":" and any(
                previous.upper() == secret.name and value == secret.value for secret in values):
            refuse(path, number)
        previous_end = match.end()
        previous = value
