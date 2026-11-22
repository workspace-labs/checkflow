# Data: Corner Bakery
> v1 · Approved 2026-11-29 by the bakery owner

## What it saves
The tool saves orders in `orders.json`. It needs no names or contact details.
- **If this copy is lost:** the bakery owner re-enters open orders from the paper list.

## Sheets

### Orders (orders)
One row is one pickup order.

| Column | Holds | Example | Mark |
|---|---|---|---|
| reference | Order number | 1 | – |
| bread | Bread name | sourdough | – |
| pickup | Pickup date | 2026-12-13 | – |
| cancelled | Whether the order was cancelled | false | – |

- **Who can see it:** anyone using the bakery computer.
- **How long it's kept:** until the owner closes the pickup list for the week.
- **Required:** reference, bread, pickup
- **Unique:** reference
- **Removal:** the bakery owner removes old orders.

## How the sheets link
- There is one list.

## Ready block
```json
[
  {"reference": 1, "bread": "sourdough", "pickup": "2026-12-13", "cancelled": false}
]
```
