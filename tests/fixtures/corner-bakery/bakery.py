"""A small command-line shop for bread orders."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path


BREADS = {"sourdough": "12.00", "rye": "10.00"}
PICKUP_DAYS = {"tomorrow": 1, "day-after": 2}
# A made-up value for this sample project. It does not connect to a service.
SERVICE_KEY = "bakery_live_PLANTED_7f3a91c2"


def read_orders(path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_orders(path, orders):
    path.write_text(json.dumps(orders, indent=2) + "\n", encoding="utf-8")


def place_order(folder, path, orders, bread, pickup, today):
    reference = len(orders) + 1
    pickup_date = (today + timedelta(days=PICKUP_DAYS[pickup])).isoformat()
    orders.append({"reference": reference, "bread": bread, "pickup": pickup_date})
    save_orders(path, orders)
    notice = f"Order {reference} for pickup on {pickup_date}."
    with (folder / "messages.txt").open("a", encoding="utf-8") as messages:
        messages.write(notice + "\n")
    print(notice)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Corner Bakery")
    parser.add_argument("--dark", action="store_true", help="use a dark menu")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("menu", help="show today's bread")
    order = commands.add_parser("order", help="order a loaf")
    order.add_argument("bread", choices=BREADS)
    order.add_argument("--pickup", choices=PICKUP_DAYS, default="tomorrow")
    commands.add_parser("orders", help="list orders")
    return parser.parse_args(argv)


def main(argv=None, *, folder=None, now=None):
    args = parse_args(argv)
    if args.command in (None, "menu"):
        heading = "Today's bread"
        print(f"\033[97;40m{heading}\033[0m" if args.dark else heading)
        for bread, price in BREADS.items():
            print(f"{bread}  AED {price}")
        return 0

    folder = Path.cwd() if folder is None else folder
    now = datetime.now() if now is None else now
    path = folder / "orders.json"
    orders = read_orders(path)
    if args.command == "order":
        place_order(folder, path, orders, args.bread, args.pickup, now.date())
    else:
        print("Orders")
        for order in orders:
            print(f"{order['reference']}  {order['bread']}  {order['pickup']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
