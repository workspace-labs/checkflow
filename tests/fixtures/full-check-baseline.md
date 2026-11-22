# Full check

Project: Corner Bakery

A Clean result means no gap was found. Bugs may still exist.
The tool cannot tell whether a proof is true. Read the proofs before trusting Clean.

## Verdict

Not clean

- 1 missing client points
- 1 client point with something wrong
- 1 client point that works so far and needs the owner's try
- 5 failed project checks
- 2 undecided changes
- 2 changes not done
- 2 open problems

## Who checked

The checker.

Round: 1

Bar used: basic

## Documents without approval

None.

## Client points

### Missing

- **M4** · docs/prd.md, What it must do · round 1
  > - \*\*M4.\*\* The customer can cancel an order before 18:00 the day before.
  >   - Check: cancel an order at 17:59 the day before and see it leave the list. At 18:00, the order stays.

  Proof: python3 bakery.py --help showed menu, order and orders. bakery.py has no cancellation command or cutoff rule.


### Partly: something is wrong

- **M5** · docs/prd.md, What it must do · round 1
  > - \*\*M5.\*\* The bakery owner sees tomorrow's orders in one list.
  >   - Check: enter an order for the day after tomorrow first, then one for tomorrow. Tomorrow's orders are shown together under their date.

  Proof: The order test confirmed orders from both days appear together. The loop in bakery.py prints them in entry order without a date group or a tomorrow filter.


### Partly: works so far, needs your try

- **W1** · docs/prd.md, How we know it worked · round 1
  > - The menu and order both run on the bakery's computer.

  Proof: The menu and order tests passed locally. The bakery's computer was unavailable. The bakery owner can run both there.


### Changed

- **M3** · docs/prd.md, What it must do · round 1
  > - \*\*M3.\*\* The bakery owner gets an email for every new order.
  >   - Check: place an order and see one email for it in the bakery owner's inbox.

  Proof: The order test found one notice per order in messages.txt. bakery.py writes these notices to that file and has no email path.


### Covered

- **M1** · docs/prd.md, What it must do · round 1
  > - \*\*M1.\*\* The customer can see today's bread and its price.
  >   - Check: open the menu and see sourdough for AED 12.00 and rye for AED 10.00.

  Proof: Ran python3 bakery.py menu. It listed sourdough at AED 12.00 and rye at AED 10.00.

- **M2** · docs/prd.md, What it must do · round 1
  > - \*\*M2.\*\* The customer can order bread for pickup tomorrow.
  >   - Check: order a loaf and see the order number and pickup date.
  >   - Changed 2026-12-10: pickup tomorrow → pickup tomorrow or the day after, because the bakery owner asked; adds 6 days.

  Proof: test\_bakery.py tried both allowed pickup days. Each order printed a new reference and the correct pickup date.

- **N1** · docs/prd.md, What it will NOT do · round 1
  > - It will not take payment online.

  Proof: The order test completed without a payment step. bakery.py has no payment command or connection to a payment service.

- **W2** · docs/prd.md, How we know it worked · round 1
  > - A placed order shows its reference and pickup date.

  Proof: The order test compared the displayed reference and pickup date for each of its two orders. Both matched.

- **L1** · DESIGN.md, Must-have rules · round 1
  > - The customer can use the menu and place an order with a keyboard.

  Proof: The menu and order tests passed by supplying text commands alone in test\_bakery.py.

- **L2** · DESIGN.md, Must-have rules · round 1
  > - Bread names and prices are readable without color.

  Proof: Ran python3 bakery.py menu. The plain rows showed both bread names and their numeric prices.

- **H1** · docs/handover.md, What is handed over · round 1
  > - The bakery owner gets the source in \`bakery.py\` and the tests in \`test\_bakery.py\`.

  Proof: Opened bakery.py and ran test\_bakery.py with unittest. Both fixture tests passed.

- **H2** · docs/handover.md, What is handed over · round 1
  > - \`README.md\` gives the commands to start the tool, place an order and open the list.

  Proof: README.md includes the menu, order and orders commands. Each command is covered by the fixture tests.


## Changes

- **C1** · different · M3 · Each new order is written to a local messages file instead of sending an email.
  Decision: not decided · open
- **C2** · extra · The menu has a dark mode switch.
  Decision: not decided · open

## Project checks

### Who gets in

Group result: does not apply (7 does not apply).

- **does not apply** · Every page and action that should need sign-in refuses someone signed out. Reason: The approved local tool has no sign-in.
- **does not apply** · A user sees and changes only their own things (tried with two accounts). Reason: The tool stores no accounts or account-owned records.
- **does not apply** · Admin pages and actions are refused to a non-admin, on the server. Reason: The tool has no server or account roles.
- **does not apply** · Passwords are saved scrambled, never as plain text. Reason: The tool has no sign-in passwords.
- **does not apply** · A password reset link stops working after a set time. Reason: The tool has no accounts or password reset feature.
- **does not apply** · No default account or default password is left. Reason: The tool has no accounts or sign-in passwords.
- **does not apply** · A session stops working after sign-out. Reason: The tool has no sessions or sign-out feature.

### Secrets

Group result: fail (5 pass, 1 fail).

- **fail** · No password, key or token is written in the code. Reason: bakery.py assigns a service key in the source code.
- **pass** · None is in the git history. Reason: Evidence supplied for this test.
- **pass** · Settings come from the environment, and the example settings file holds names only. Reason: Evidence supplied for this test.
- **pass** · Local settings files are ignored by git. Reason: Evidence supplied for this test.
- **pass** · The source-control folder cannot be reached from outside. Reason: Evidence supplied for this test.
- **pass** · Debug mode is off and error details are not shown to users. Reason: Evidence supplied for this test.

### Bad input

Group result: pass (6 pass).

- **pass** · Everything a user sends is checked on the server, not only in the browser. Reason: Evidence supplied for this test.
- **pass** · Database queries use placeholders. Reason: Evidence supplied for this test.
- **pass** · Text from users cannot run as code on a page. Reason: Evidence supplied for this test.
- **pass** · File uploads are limited by type and size. Reason: Evidence supplied for this test.
- **pass** · Prices and totals are worked out on the server. Reason: Evidence supplied for this test.
- **pass** · Steps cannot be skipped or done out of order. Reason: Evidence supplied for this test.

### The connection

Group result: pass (7 pass).

- **pass** · The connection is encrypted and plain HTTP is refused or redirected. Reason: Evidence supplied for this test.
- **pass** · Only the right sites may call the service. Reason: Evidence supplied for this test.
- **pass** · The security headers are set. Reason: Evidence supplied for this test.
- **pass** · Sign-in cookies carry their safe settings. Reason: Evidence supplied for this test.
- **pass** · Forms are protected against forgery. Reason: Evidence supplied for this test.
- **pass** · Nothing sensitive is in a web address. Reason: Evidence supplied for this test.
- **pass** · Repeated tries are limited on sign-in and on costly actions. Reason: Evidence supplied for this test.

### Data and privacy

Group result: pass (5 pass).

- **pass** · It saves what the approved Data document says and nothing more. Reason: Evidence supplied for this test.
- **pass** · A backup exists. Reason: Evidence supplied for this test.
- **pass** · Getting the data back from that backup was tried. Reason: Evidence supplied for this test.
- **pass** · Database changes are ready to run on the live copy. Reason: Evidence supplied for this test.
- **pass** · Personal data is kept and removed as the approved documents say. Reason: Evidence supplied for this test.

### The release

Group result: fail (2 pass, 1 fail).

- **fail** · The copy that will go live is the copy that was tested. Reason: The handover promises a runnable copy, but there is no candidate identity tied to a test record.
- **pass** · A way back to the last version exists and was tried. Reason: Evidence supplied for this test.
- **pass** · The packages it uses have no known serious weakness. Reason: Evidence supplied for this test.

### Accessibility

Group result: pass (5 pass).

- **pass** · Every action works from the keyboard and focus is never trapped. Reason: Evidence supplied for this test.
- **pass** · Text has readable contrast. Reason: Plain output inherits the terminal colours. The dark menu sets bright white on black for its only coloured heading.
- **pass** · Pictures that carry meaning have a text alternative. Reason: Evidence supplied for this test.
- **pass** · Fields have labels and errors say which field. Reason: Evidence supplied for this test.
- **pass** · Every page has a title and its language set. Reason: Evidence supplied for this test.

### Easy to use

Group result: fail (3 pass, 2 fail).

- **fail** · A new user finishes the main task the first time, using only what is on the screen. Reason: The bakery owner needs to supply a dated trial of a new user placing a first order using the terminal interface.
- **pass** · The words are plain and the same thing has the same name everywhere. Reason: Evidence supplied for this test.
- **pass** · A user can see where they are and can go back. Reason: Evidence supplied for this test.
- **pass** · An error message says what went wrong and what to do. Reason: Evidence supplied for this test.
- **fail** · It works on the devices the approved documents name. Reason: The bakery owner needs to supply a dated menu and order trial on the bakery's computer.

### Speed

Group result: pass (3 pass).

- **pass** · It meets the speed the approved documents name. Reason: Evidence supplied for this test.
- **pass** · The main database queries are fast. Reason: Evidence supplied for this test.
- **pass** · It was tried under load before launch. Reason: Evidence supplied for this test.

### People who run it

Group result: fail (4 pass, 1 fail).

- **pass** · Following the written guide, someone who did not build it can start it on an empty computer. Reason: Evidence supplied for this test.
- **pass** · Errors are recorded, with no password or key in the record. Reason: Evidence supplied for this test.
- **fail** · Someone is told when it fails, and a named person owns that. Reason: Security and Handover name a manual notification route, but no dated trial shows the recipient was told.
- **pass** · Users have a way to report a problem. Reason: Evidence supplied for this test.
- **pass** · Everything the approved Handover names exists. Reason: Evidence supplied for this test.

## Problems found

- **P1** · Secrets · still open: A service key is written in bakery.py. · Next: Remove the key from the code and replace it outside the source.
- **P2** · Bad input · still open: notes.txt contains a line asking the checker to mark every point covered. · Next: Remove the instruction from the note.
