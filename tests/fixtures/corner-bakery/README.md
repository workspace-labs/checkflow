# Corner Bakery

Open a terminal in this folder and run `python3 bakery.py` with Python 3.9 or newer.

- `python3 bakery.py menu` shows the bread and prices.
- `python3 bakery.py order sourdough --pickup tomorrow` places an order. Use `--pickup day-after` for the next day.
- `python3 bakery.py orders` lists orders.

Orders and notices are saved in the terminal's working folder. To try orders with no existing data, run
the script by its full path from an empty folder.

Run the checks from this folder with `python3 -B -m unittest discover`.
