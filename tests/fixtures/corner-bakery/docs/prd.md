# PRD: Corner Bakery
> v2 · Approved 2026-12-10 by the bakery owner

## What it is
A small bread menu and pickup order tool.

## Why
Customers can see what is available and book pickup before coming to the shop.

## Who it's for
- **Customer:** chooses a loaf and a pickup day.
- **Bakery owner:** sees what to bake.

## How it works today
Customers order over the counter. The bakery owner writes down each order.

## How it will work
Customers see the menu and place an order in a terminal. The bakery owner checks the pickup list.

## Who decides
- **Owner:** the bakery owner.
- **Approves the scope:** the bakery owner.
- **Approves the prototype:** the bakery owner.
- **Accepts it (UAT):** the bakery owner.
- **Others to involve:** a customer tries ordering a loaf.

## What it must do
- **M1.** The customer can see today's bread and its price.
  - Check: open the menu and see sourdough for AED 12.00 and rye for AED 10.00.
- **M2.** The customer can order bread for pickup tomorrow.
  - Check: order a loaf and see the order number and pickup date.
  - Changed 2026-12-10: pickup tomorrow → pickup tomorrow or the day after, because the bakery owner asked; adds 6 days.
- **M3.** The bakery owner gets an email for every new order.
  - Check: place an order and see one email for it in the bakery owner's inbox.
- **M4.** The customer can cancel an order before 18:00 the day before.
  - Check: cancel an order at 17:59 the day before and see it leave the list. At 18:00, the order stays.
- **M5.** The bakery owner sees tomorrow's orders in one list.
  - Check: enter an order for the day after tomorrow first, then one for tomorrow. Tomorrow's orders are shown together under their date.

```md
- **M99.** A line showing how a point is written.
  - Check: this is an example inside a code block.
```

## What it will NOT do
- It will not take payment online.

## Later
- Delivery.

## Assumptions and risks
- **Assumption:** the bakery uses a computer with a terminal.
- **Risk:** the oven supplier may send its price list late.

## How we know it worked
- The menu and order both run on the bakery's computer.
- A placed order shows its reference and pickup date.

## Dates and budget
- **Dates:** start 2026-11-30; planned end 2026-12-18.
- **Budget:** none set for the sample.
