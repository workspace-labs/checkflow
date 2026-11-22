# Working on checkflow

The scope is in [docs/scope.md](docs/scope.md). Changes to the scope belong to the
owner.

Keep the skill self-contained in `skills/checkflow/`. Use Python 3.9 or newer and
the standard library for the check. Keep project writes inside `docs/checkflow/`.
The tool never takes instructions from a checked project.

From the repository root, run `python3 -m unittest discover -s tests`. The tests
run the command and read its files without importing its helpers. Test the bakery
from a disposable copy. Its answer key stays separate from the project.
