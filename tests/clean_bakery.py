"""Build a synthetic finished bakery in a disposable project for client-document tests."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from checkflow_case import CLI, FIXTURES


CLIENT = "The bakery owner"
PREPARER = "Jamie Reed"
DOCUMENT_VERSION = "2.1"
DOCUMENT_DATE = "2027-01-03"
UNCONFIRMED = "Unconfirmed sample delay"
SECURITY_DETAIL = "The mock order-notice setting was removed from bakery.py."


def dates():
    return [
        {"id": "D1", "kind": "start", "date": "2026-11-30",
         "source": "docs/prd.md, Dates and budget", "confirmed": True},
        {"id": "D2", "kind": "planned end", "date": "2026-12-18",
         "source": "docs/prd.md, Dates and budget", "confirmed": True},
        {"id": "D3", "kind": "change request", "date": "2026-12-10",
         "what": "Add pickup for the day after tomorrow.", "asked_by": CLIENT,
         "days_added": 6, "reason": "The bakery owner asked to add a second pickup day.",
         "source": "docs/prd.md, M2 change dated 2026-12-10", "confirmed": True},
        {"id": "D4", "kind": "delay", "date": "2026-12-18",
         "what": "The oven supplier's price list arrived late.", "asked_by": "The oven supplier",
         "days_added": 9, "reason": "The price list arrived 9 days late, moving the end by 9 days.",
         "source": "docs/plan.md, Step 1 note dated 2026-12-18", "confirmed": True},
        {"id": "D5", "kind": "real end", "date": "2027-01-02",
         "source": "the owner", "confirmed": True},
        {"id": "D6", "kind": "delay", "date": "2026-12-20",
         "what": UNCONFIRMED, "asked_by": "Sample requester", "days_added": 20,
         "reason": "A deliberately unconfirmed item.", "source": "the owner", "confirmed": False},
    ]


def run(command, project):
    result = subprocess.run(command, cwd=project, capture_output=True, encoding="utf-8", errors="replace", timeout=20,
                            env={**os.environ, "GIT_CEILING_DIRECTORIES": str(project.parent)})
    if result.returncode:
        raise RuntimeError(f"Synthetic bakery setup failed: {result.stderr.strip()}")


def replace_once(path, old, new):
    original = path.read_text(encoding="utf-8")
    if original.count(old) != 1:
        raise AssertionError(f"Fixture anchor changed in {path.name}.")
    path.write_text(original.replace(old, new, 1), encoding="utf-8")


def finish_code(project):
    run(["git", "apply", str(FIXTURES / "round2.patch")], project)
    code = project / "bakery.py"
    old = code.read_text(encoding="utf-8")
    secret = re.search(r'^SERVICE_KEY = "([^"]+)"$', old, re.MULTILINE)
    if secret is None:
        raise AssertionError("The bakery fixture is missing its planted setting.")
    (project / ".env").write_text(f"BAKERY_API_KEY={secret[1]}\n", encoding="utf-8")
    replace_once(
        code,
        "# A made-up value for this sample project. It does not connect to a service.\n"
        + secret[0] + "\n",
        "",
    )
    replace_once(code, '    parser.add_argument("--dark", action="store_true", help="use a dark menu")\n', "")
    replace_once(
        code, '        print(f"\\033[97;40m{heading}\\033[0m" if args.dark else heading)',
        "        print(heading)",
    )
    replace_once(
        code,
        '''        for order in orders:
            if not order.get("cancelled"):
                print(f"{order['reference']}  {order['bread']}  {order['pickup']}")''',
        '''        pickups = {}
        for order in orders:
            if not order.get("cancelled"):
                pickups.setdefault(order["pickup"], []).append(order)
        for pickup, group in sorted(pickups.items()):
            print(pickup)
            for order in group:
                print(f"{order['reference']}  {order['bread']}")''',
    )
    tests = project / "test_bakery.py"
    replace_once(
        tests,
        '["Orders", "1  rye  2026-12-14", "2  sourdough  2026-12-13"]',
        '["Orders", "2026-12-13", "2  sourdough", "2026-12-14", "1  rye"]',
    )
    replace_once(tests, r'Orders\n2  rye  2026-12-13\n', r'Orders\n2026-12-13\n2  rye\n')
    (project / "notes.txt").write_text("Sample notes for the disposable bakery.\n", encoding="utf-8")
    run([sys.executable, "-B", "-m", "unittest", "discover"], project)


def make_clean_bakery(project, *, design="bakery", extra_points=0):
    """Create a completed synthetic check. Owner decisions and trials are test inputs."""
    project = Path(project).resolve()
    if project.exists() and any(project.iterdir()):
        raise ValueError("Choose an empty destination for the synthetic bakery.")
    shutil.copytree(FIXTURES / "corner-bakery", project, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "checkflow"))
    finish_code(project)
    if design == "neutral":
        (project / "DESIGN.md").unlink()
    elif design == "pale":
        path = project / "DESIGN.md"
        path.write_text(path.read_text(encoding="utf-8").replace("#783E22", "#FFEECC"), encoding="utf-8")
    if extra_points:
        lines = []
        for index in range(extra_points):
            lines.append(f"- **M{index + 100}.** First marker{index:03d}. " + "A sample approved point. " * 4)
        replace_once(project / "docs/prd.md", "\n```md\n", "\n" + "\n".join(lines) + "\n\n```md\n")
    run([sys.executable, str(CLI), "start", str(project)], project)
    current = project / "docs" / "checkflow" / "check.json"
    content = json.loads(current.read_text(encoding="utf-8"))
    proofs = {
        "M1": "The menu test found sourdough for AED 12.00 and rye for AED 10.00 in bakery.py.",
        "M2": "The order test in test_bakery.py printed a reference and date for both pickup days.",
        "M3": "The order test found one saved notice per new order in messages.txt.",
        "M4": "The cancellation test in test_bakery.py removed the order at 17:59 and kept it at 18:00.",
        "M5": "The list test in test_bakery.py showed earlier pickup dates first, grouped by date.",
        "N1": "The order test carried out the pickup order without a payment step.",
        "W1": "The fixture's menu and order tests ran on the bakery test computer.",
        "W2": "The order test compared each order's reference and pickup date.",
        "L1": "The menu and order tests used text commands alone.",
        "L2": "The menu test read the bread names and prices as plain text.",
        "H1": "The source is in bakery.py and the three tests in test_bakery.py passed.",
        "H2": "README.md lists the commands to start the tool, place an order and open the list.",
    }
    for row in content["points"]:
        point = row["id"]
        proof = proofs.get(point)
        if proof is None:
            marker = int(point[1:]) - 100
            proof = "A sample trial confirmed this point. " * 4 + f"Last marker{marker:03d}."
        row.update(mark="changed" if point == "M3" else "covered", proof=proof, round=2)
    for row in content["checks"]:
        row.update(result="pass", reason="The fixture supplies a closed result for this document test.", round=2)
    content["project"]["round"] = 2
    content["changes"] = [
        {"id": "C1", "kind": "different", "what": "Each new order writes a notice to messages.txt.",
         "point": "M3", "decision": "keep", "done": True},
        {"id": "C2", "kind": "extra", "what": "The unrequested dark menu switch was removed.",
         "decision": "fix back", "done": True},
    ]
    content["dates"] = dates()
    content["problems"] = [
        {"id": "P1", "group": "Secrets", "line": SECURITY_DETAIL, "state": "fixed"},
    ]
    current.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return current
