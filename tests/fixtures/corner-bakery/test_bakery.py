from contextlib import redirect_stdout
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from bakery import main


class BakeryTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)
        self.now = datetime(2026, 12, 12, 12)

    def run_command(self, *args):
        output = StringIO()
        with redirect_stdout(output):
            status = main(args, folder=self.folder, now=self.now)
        return status, output.getvalue()

    def test_menu_shows_bread_and_price(self):
        status, output = self.run_command("menu")
        self.assertEqual(status, 0)
        self.assertIn("sourdough", output)
        self.assertIn("AED 12.00", output)

    def test_orders_accept_both_pickup_days_and_record_local_notices(self):
        day_after = self.run_command("order", "rye", "--pickup", "day-after")
        tomorrow = self.run_command("order", "sourdough", "--pickup", "tomorrow")
        self.assertEqual(day_after, (0, "Order 1 for pickup on 2026-12-14.\n"))
        self.assertEqual(tomorrow, (0, "Order 2 for pickup on 2026-12-13.\n"))
        messages = (self.folder / "messages.txt").read_text(encoding="utf-8")
        self.assertEqual(len(messages.splitlines()), 2)
        status, orders = self.run_command("orders")
        self.assertEqual(status, 0)
        self.assertEqual(orders.splitlines(), ["Orders", "1  rye  2026-12-14", "2  sourdough  2026-12-13"])
