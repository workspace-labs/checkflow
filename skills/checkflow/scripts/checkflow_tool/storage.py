"""Project paths and publication of check files."""

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


CURRENT = "docs/checkflow/check.json"
OUTPUT = "docs/checkflow"


class Refusal(Exception):
    """A short instruction for correcting a check."""


@contextmanager
def output_access(name):
    try:
        yield
    except PermissionError:
        raise Refusal(
            f"Cannot access {name}. Close it if it is open, check its permissions, and try again."
        ) from None


class Project:
    def __init__(self, folder):
        self.root = Path(folder).resolve()
        if not self.root.is_dir():
            raise Refusal("Choose an existing project folder.")

    def path(self, name):
        path = self.root / name
        for part in (*path.parents, path):
            if part == self.root or self.root not in part.parents:
                continue
            if part.is_symlink() or part.resolve() != part:
                raise Refusal(f"Use a regular path inside the project for {name}.")
        return path

    def read(self, name):
        path = self.path(name)
        if path.is_file():
            return path.read_bytes()
        if path.exists():
            raise Refusal(f"Use a regular file for {name}.")
        return None

    def read_output(self, name):
        with output_access(name):
            return self.read(name)

    def read_text(self, name):
        raw = self.read(name)
        if raw is None:
            return None
        try:
            return raw.decode("utf-8-sig")
        except UnicodeError:
            raise Refusal(f"Save {name} as UTF-8.") from None

    @contextmanager
    def writer(self):
        output = self.path(OUTPUT)
        created = not output.exists()
        output.mkdir(exist_ok=True)
        lock = self.path(f"{OUTPUT}/.write-lock")
        try:
            with lock.open("x"):
                pass
        except FileExistsError:
            raise Refusal(
                "Let the other check finish, then try again. If no check is running, "
                "remove the leftover docs/checkflow/.write-lock and retry."
            ) from None
        try:
            yield
        finally:
            lock.unlink()
            if created and not any(output.iterdir()):
                output.rmdir()

    def write(self, name, data):
        path = self.path(name)
        if not path.parent.is_dir() or (path.exists() and not path.is_file()):
            raise Refusal(f"Use a regular file for {name}.")
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
            temp_path = Path(tmp.name)
            try:
                tmp.write(data)
                tmp.close()
                with output_access(name):
                    os.replace(temp_path, path)
            finally:
                temp_path.unlink(missing_ok=True)


def json_bytes(data):
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal("Remove repeated field names from check.json.")
        result[key] = value
    return result


def load_check(project, name=CURRENT):
    raw = project.read(name)
    if raw is None:
        if name == CURRENT:
            raise Refusal("Run start to create docs/checkflow/check.json.")
        raise Refusal(f"Supply the finished check at {name}.")
    try:
        return raw, json.loads(raw, object_pairs_hook=unique_fields)
    except (ValueError, RecursionError):
        raise Refusal(f"Fix the JSON in {name}.") from None
