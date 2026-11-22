#!/usr/bin/env python3
"""Run an offline project check."""

import argparse
import sys

sys.dont_write_bytecode = True

from checkflow_tool import (basic, document_commands, documents, first_page, merge, report, rounds,
                            secrets, validation)
from checkflow_tool.storage import CURRENT, OUTPUT, Project, Refusal, json_bytes, load_check


REPORT = f"{OUTPUT}/full-check.md"


def start(project, values):
    if project.read(CURRENT) is not None:
        raise Refusal("Use next-round. docs/checkflow/check.json already exists.")
    scope = documents.read_scope(project, 1, values)
    data = {
        "project": {"name": scope.name, "client": "", "language": "", "round": 1,
                    "bar": "basic", "not_approved": scope.not_approved, "checkers": 1},
        "points": scope.points,
        "checks": basic.empty_checks(basic.basic_checks()),
        "changes": [],
        "dates": [],
        "problems": [],
    }
    guard_check(data, values)
    contents = json_bytes(data)
    with project.writer():
        if project.read(CURRENT) is not None:
            raise Refusal("Use next-round. docs/checkflow/check.json already exists.")
        project.write(CURRENT, contents)


def guard_check(data, values):
    if secrets.contains_secret_in_data(data, values):
        raise Refusal("Remove the known secret value from the check and replace the secret before trying again.")


def finish(project, values, command, same_builder):
    previous, data = load_check(project)
    if command == "merge" and secrets.contains_secret(previous.decode(errors="replace"), values):
        raise Refusal("Remove the known secret value from the check and replace the secret before trying again.")
    guard_check(data, values)
    checks = basic.basic_checks()
    validation.validate(data, checks)
    current_round = data["project"]["round"]

    if command == "next-round":
        scope = documents.read_scope(project, current_round + 1, values)
        new_data = rounds.advance(data, scope)
        guard_check(new_data, values)
        publish_round(project, current_round, previous, json_bytes(new_data))
        return

    scope = documents.read_scope(project, current_round, values)
    validation.validate_scope(data, scope)
    if command == "merge":
        merge.run(project, previous, data, checks, scope, values)
        print("Checks merged.")
    elif command == "report":
        disagreements, sources = None, {}
        if data["project"].get("checkers", 1) == 2:
            disagreements, sources = merge.report_inputs(project, data, checks, values)
        markdown = report.full_check(data, checks, same_builder, disagreements)
        if secrets.contains_secret(markdown, values):
            raise Refusal("Remove the known secret from the full check's content before trying again.")
        with project.writer():
            require_current(project, previous)
            if any(project.read(name) != raw for name, raw in sources.items()):
                raise Refusal("Read both checks again. One changed while writing the report.")
            project.write(REPORT, markdown.encode("utf-8"))


def require_current(project, previous):
    if project.read(CURRENT) != previous:
        raise Refusal("Read the current check and try again. It changed during this command.")


def publish_round(project, number, previous, contents):
    name = f"{OUTPUT}/check.round-{number}.json"
    with project.writer():
        require_current(project, previous)
        archived = project.read(name)
        if archived is not None and archived != previous:
            raise Refusal(f"Keep the existing archive {name} and resolve the round number before retrying.")
        if archived is None:
            project.write(name, previous)
        try:
            project.write(CURRENT, contents)
        except (OSError, Refusal):
            if archived is None:
                project.path(name).unlink()
            raise


class CheckflowParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "1. Check the command, options and project folder. See checkflow.py --help.\n")


def main():
    parser = CheckflowParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "check", "report", "merge", "next-round", "preview", "choose", "document",
                 "translate", "confirm-translation"):
        command = commands.add_parser(name)
        command.add_argument("project", help="the folder being checked")
        if name == "report":
            command.add_argument("--same-builder", action="store_true",
                                 help="disclose that the checker also built the project")
        if name in ("preview", "choose"):
            command.add_argument("--frame", choices=first_page.FRAMES, help="first-page frame")
            command.add_argument("--name-position", choices=first_page.POSITIONS)
            command.add_argument("--details-style", choices=first_page.DETAIL_STYLES)
            command.add_argument("--details", help="comma-separated first-page details, or empty for none")
        if name in ("preview", "translate", "confirm-translation"):
            command.add_argument("--language", choices=tuple(first_page.LANGUAGES),
                                 required=name != "preview")
        if name == "choose":
            command.add_argument("--client", required=True)
            command.add_argument("--language", choices=("en", "ar", "both"), required=True)
            command.add_argument("--prepared-by", metavar="NAME", help="person or organisation preparing the document")
            command.add_argument("--version", metavar="TEXT", help="document version supplied by the owner")
            command.add_argument("--document-date", metavar="YYYY-MM-DD", help="document date supplied by the owner")
            credit = command.add_mutually_exclusive_group()
            credit.add_argument("--credit", dest="credit", action="store_true", default=None)
            credit.add_argument("--no-credit", dest="credit", action="store_false")
    args = parser.parse_args()
    values = []
    try:
        project = Project(args.project)
        values = secrets.known_values(project)
        if args.command == "start":
            start(project, values)
            print("Check started.")
        elif args.command == "choose":
            document_commands.choose(project, values, args)
        elif args.command == "preview":
            document_commands.preview(project, values, args)
        elif args.command == "document":
            document_commands.document(project, values)
        elif args.command in ("translate", "confirm-translation"):
            document_commands.translate(project, values, args.language,
                                        confirm=args.command == "confirm-translation")
        else:
            finish(project, values, args.command, getattr(args, "same_builder", False))
            if args.command == "check":
                print("Check complete.")
            elif args.command == "report":
                print("Full check written.")
    except Refusal as error:
        raw_message = str(error)
        message = " ".join(raw_message.split())
        if secrets.contains_secret(raw_message, values) or secrets.contains_secret(message, values):
            message = "Remove the known secret value and replace it before trying again."
        print(f"1. {message}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, RecursionError, RuntimeError):
        print("1. Check that the project files are accessible and use valid UTF-8, then try again.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
