# Project checks

Walk all ten groups. Write a result and a reason for each check. Use project
files, normal local tests or recorded evidence kept with the project. Keep
credentials out of every note. Use a disposable local copy for a test that
writes files or changes state.

Decide whether each check applies from the project and its approved documents.
Use `does not apply` only when the check has no feature, data or obligation
to cover. Mark an approved but absent safeguard or feature `fail` and give the reason. A group does not apply when none of its checks apply.

For every applicable check, mark `pass` when the evidence shows it passed.
Mark `fail` when it fails or lacks evidence. If you need a person or a named
device, say exactly what the owner needs to supply. For example, ask for a
dated record of a new user placing the first order on the named computer.
A helper agent's trial is supporting evidence only for a check that calls
for a person.
Mark it `pass` in a later round when the supplied evidence shows that it passed.

Use web checks about browsers, servers or pages only where the project has or
requires that part. A terminal tool without a server or web page has no
server-side input checks, server-side prices, page scripts, page titles or
page language to verify. For general checks about a user interface, use the
tool's actual commands, prompts, output and help. A terminal counts as an
interface even though it has no web page.

## Contents

- [Who gets in](#who-gets-in)
- [Secrets](#secrets)
- [Bad input](#bad-input)
- [The connection](#the-connection)
- [Data and privacy](#data-and-privacy)
- [The release](#the-release)
- [Accessibility](#accessibility)
- [Easy to use](#easy-to-use)
- [Speed](#speed)
- [People who run it](#people-who-run-it)

## Who gets in

- **Every page and action that should need sign-in refuses someone signed out**
  - How to check it. List the approved private pages and actions. Check the server's sign-in rules and run the project's normal signed-out tests.
  - When it does not apply. No page or action is supposed to require sign-in.

- **A user sees and changes only their own things (tried with two accounts)**
  - How to check it. Use the project's test with two ordinary sample accounts. Confirm the permitted account can read and change its sample record and the other account is refused.
  - When it does not apply. Users have no account-owned data or actions that must be kept private from other accounts.

- **Admin pages and actions are refused to a non-admin, on the server**
  - How to check it. Check server rules for each admin page and action. Run the normal permission tests for an admin and an ordinary sample account.
  - When it does not apply. No page or action is reserved for an administrator.

- **Passwords are saved scrambled, never as plain text**
  - How to check it. Follow password setup and reset to storage. Check that the app saves a password hash and run its password storage test if it has one.
  - When it does not apply. Password storage belongs entirely to another service, or sign-in uses no passwords.

- **A password reset link stops working after a set time**
  - How to check it. Read the expiry rule and run the project's existing reset test with a sample link and a test clock beyond the limit.
  - When it does not apply. The project neither issues nor requires password reset links.

- **No default account or default password is left**
  - How to check it. Review setup scripts, sample accounts and release settings for an account or password enabled by default.
  - When it does not apply. The project neither uses nor requires sign-in accounts.

- **A session stops working after sign-out**
  - How to check it. Read the sign-out handler and use the project's session test to confirm a signed-out session cannot open a private page.
  - When it does not apply. The project neither uses nor requires sign-in sessions.

## Secrets

- **No password, key or token is written in the code**
  - How to check it. Review the code and tracked settings for saved credential values. Record only the setting name or where it was found.
  - When it does not apply. The project contains no code or tracked settings to review.

- **None is in the git history**
  - How to check it. Review local Git history or a recent redacted history check. Record locations or results without recording any credential value.
  - When it does not apply. The checked copy has no Git folder or Git worktree pointer. If it has one but the history is unavailable, mark fail.

- **Settings come from the environment, and the example settings file holds names only**
  - How to check it. Follow the code that loads settings. Check that it reads from the environment and compare its setting names with the example file. If there is no example file, use the setting names listed in an approved document or the guide as the example.
  - When it does not apply. The project has no runtime or release settings to supply and the approved documents require none.

- **Local settings files are ignored by git**
  - How to check it. Compare the project's local settings files with its Git ignore rules and tracked file list.
  - When it does not apply. The checked copy has no Git folder or Git worktree pointer, or has no local settings files to keep out of Git.

- **The source-control folder cannot be reached from outside**
  - How to check it. Read the release package list and server rules. Check that the source-control folder is excluded or explicitly blocked.
  - When it does not apply. The checked copy has no source-control folder or pointer, or it neither serves nor distributes files from its source tree.

- **Debug mode is off and error details are not shown to users**
  - How to check it. Inspect release settings and error handling. Use an existing ordinary failure test to see what users receive, including in a terminal.
  - When it does not apply. The project has neither a debug mode nor any way to show or return errors to users.

## Bad input

- **Everything a user sends is checked on the server, not only in the browser**
  - How to check it. Trace each user input to its server checks. Run the project's own tests for ordinary invalid or missing values.
  - When it does not apply. The project neither has nor requires a server that accepts user input.

- **Database queries use placeholders**
  - How to check it. Read the database calls and check that user values are bound separately from query text.
  - When it does not apply. The project makes no database queries.

- **Text from users cannot run as code on a page**
  - How to check it. Follow user text to every web page or generated HTML page that shows it. Check that templates escape it or render it as text. Try ordinary text containing punctuation in a local test.
  - When it does not apply. No web page or generated HTML shows text from users, and the approved documents require no such display.

- **File uploads are limited by type and size**
  - How to check it. For this check, count every way the project takes in files, such as a server upload, opening a file with the app or a cable transfer. Read the rules for each way and use sample files to try the accepted types and size limits.
  - When it does not apply. The project neither accepts nor requires file uploads.

- **Prices and totals are worked out on the server**
  - How to check it. Follow an order to the server's calculation and check that it uses its own price list. Run the normal totals test.
  - When it does not apply. The project neither works out nor requires prices or totals on a server.

- **Steps cannot be skipped or done out of order**
  - How to check it. Trace the required order of steps to its state rules. Run an existing test that checks the rule for an unfinished earlier step.
  - When it does not apply. No project action has a required earlier step.

## The connection

- **The connection is encrypted and plain HTTP is refused or redirected**
  - How to check it. Read the release settings and existing test results for encrypted connections. For an HTTP service, also look for evidence that plain HTTP is refused or redirected.
  - When it does not apply. The project uses no network connections and the approved documents require none.

- **Only the right sites may call the service**
  - How to check it. Compare the service's allowed web origins and access rules with the approved sites. Review the project's existing access tests.
  - When it does not apply. The project has no service for browser calls and requires none.

- **The security headers are set**
  - How to check it. Review response and release settings for the headers the service needs. Use an existing response test or captured headers as proof.
  - When it does not apply. The project neither sends nor requires HTTP responses.

- **Sign-in cookies carry their safe settings**
  - How to check it. Read the sign-in cookie setup and any response test. Check Secure, HttpOnly, SameSite and scope against the way sign-in works.
  - When it does not apply. The project neither uses nor requires browser sign-in cookies.

- **Forms are protected against forgery**
  - How to check it. Read the form and server protections for actions made with browser credentials. Check the existing form tests.
  - When it does not apply. No browser action changes data or settings using credentials the browser sends automatically.

- **Nothing sensitive is in a web address**
  - How to check it. Read routes, links and redirects that carry user data or credentials. Check the shape of the address in an ordinary local test.
  - When it does not apply. The project uses no web addresses in routes, links, redirects or requests.

- **Repeated tries are limited on sign-in and on costly actions**
  - How to check it. Read the attempt limits and tests for sign-in and each costly action. Look for the result when a permitted test limit is reached.
  - When it does not apply. The project has neither sign-in nor a repeatable action with a direct cost or heavy use of limited resources.

## Data and privacy

- **It saves what the approved Data document says and nothing more**
  - How to check it. Compare the approved saved fields with the files, database records and logs the project writes. Make a normal sample record if a safe local test is available.
  - When it does not apply. The project saves no data and the approved documents require none to be saved.

- **A backup exists**
  - How to check it. Find a dated copy or a record of a successful backup for the required data. A record counts only if it is dated after the last change to the shape of the saved data. A separate paper copy can count if it holds the records needed to recover. Recovery instructions alone do not show that a copy exists.
  - When it does not apply. The project has no data to preserve after loss. An approved recovery route using a separate copy, including a paper copy, makes the check apply.

- **Getting the data back from that backup was tried**
  - How to check it. Find dated evidence that the required data was restored from its backup or approved recovery copy. If needed, try the written restore steps with a sample copy on a disposable local project.
  - When it does not apply. The project has no data to recover after loss. An approved recovery route using a separate copy, including a paper copy, makes the check apply.

- **Database changes are ready to run on the live copy**
  - How to check it. Read the migration files and written release steps. Compare them with a recorded trial on a disposable copy of matching data.
  - When it does not apply. The release requires no database schema or data migration.

- **Personal data is kept and removed as the approved documents say**
  - How to check it. Follow personal fields, such as names and contact details, through storage and removal. Compare those rules and any recorded test with the approved requirements.
  - When it does not apply. The project neither stores personal data nor has an approved rule for keeping or removing personal data. Check non-personal retention under the saved-data check.

## The release

- **The copy that will go live is the copy that was tested**
  - How to check it. Mark pass only if a record already kept with the project identifies the copy to be delivered by version, commit or checksum and ties that copy to a successful test run. A comparison the checker makes during the check is supporting evidence only and cannot make this check pass. On fail, name the record the owner must supply in the reason.
  - When it does not apply. No deployment or handover of a runnable copy is planned.

- **A way back to the last version exists and was tried**
  - How to check it. Read the recovery steps and look for a dated trial on a safe copy with the intended previous version.
  - When it does not apply. This is the first release, with no earlier live version to restore.

- **The packages it uses have no known serious weakness**
  - How to check it. List the installed or locked package versions. Compare them with a dated dependency report or advisory data already available in the project.
  - When it does not apply. The project uses no third-party packages.

## Accessibility

- **Every action works from the keyboard and focus is never trapped**
  - How to check it. Try the main tasks and each control with a keyboard in the local interface. Open and close each dialog and check where focus goes. For a terminal tool, run the commands and try any interactive prompts.
  - When it does not apply. The project has no user-operated interface.

- **Text has readable contrast**
  - How to check it. Check each foreground and background pair the tool sets, including optional modes and errors. Plain output that sets neither colour inherits the host pair and needs no project colour measurement. If the tool sets only one colour, check it against the other colour on each approved host theme. Mark pass when all pairs the tool controls are shown readable.
  - When it does not apply. The project displays no text to a person.

- **Pictures that carry meaning have a text alternative**
  - How to check it. Review each picture with meaning and inspect its text alternative in the interface or source.
  - When it does not apply. The project has no pictures or icons needed to understand or use it.

- **Fields have labels and errors say which field**
  - How to check it. Inspect the label or name for each input, including prompts and command arguments. Omit or mistype an ordinary value in a local test and read the error.
  - When it does not apply. The user enters no values through fields, prompts or command arguments.

- **Every page has a title and its language set**
  - How to check it. Inspect each page's title and language metadata in the local app or its templates.
  - When it does not apply. The project presents no web pages or generated HTML pages.

## Easy to use

- **A new user finishes the main task the first time, using only what is on the screen**
  - How to check it. Use a trial with a person unfamiliar with the project. Watch them try the main task using what the interface shows, or read a record of that trial on the same interface. For a terminal tool, include its built-in help.
  - When it does not apply. The project gives an end user no task to do. A task carried out in the terminal makes the check apply.

- **The words are plain and the same thing has the same name everywhere**
  - How to check it. Read the main screens, instructions and errors. Compare the names for the same actions and objects across them.
  - When it does not apply. The project has no words for users in its interface, output, errors or instructions.

- **A user can see where they are and can go back**
  - How to check it. Walk each user flow. Check that the current step or screen is clear and try the available way back.
  - When it does not apply. The project has no flow that takes a user through more than one screen or prompt. Separate one-step terminal commands are not a multi-step flow.

- **An error message says what went wrong and what to do**
  - How to check it. Try a normal, safe error in a local test and read the message. Review the source for other errors users can see.
  - When it does not apply. There is no user action that can fail or reject input.

- **It works on the devices the approved documents name**
  - How to check it. Use the named devices or read test evidence from those devices for the main tasks.
  - When it does not apply. The approved documents name no device or class of devices.

## Speed

- **It meets the speed the approved documents name**
  - How to check it. Run the local timing test under the stated conditions or compare a recorded result with the approved target.
  - When it does not apply. The approved documents name no speed target.

- **The main database queries are fast**
  - How to check it. Review local timings or query plans on sample data of a useful size. Compare them with the project's performance evidence.
  - When it does not apply. The project makes no database queries.

- **It was tried under load before launch**
  - How to check it. Find a dated test record for realistic demand. If needed, run the project's bounded load test on a disposable local copy.
  - When it does not apply. The planned use is one operation at a time, with no batch work or higher demand to reproduce.

## People who run it

- **Following the written guide, someone who did not build it can start it on an empty computer**
  - How to check it. Have a person who did not build the project follow only the written guide on a clean test computer, or read a record of that trial.
  - When it does not apply. Nobody other than the builder is expected to start the project.

- **Errors are recorded, with no password or key in the record**
  - How to check it. Try an ordinary error on a safe copy or read its existing test record. Check what the project records and how it leaves out credentials.
  - When it does not apply. The project runs no operations that could fail during use. It also does not apply if one person is the only user, sees every error on screen, and no approved document requires an error record.

- **Someone is told when it fails, and a named person owns that**
  - How to check it. Use the approved failure instructions to find the owner and notification route. A manual handoff counts for an attended tool when a dated trial shows the named recipient was told. For unattended work, require a trial of the configured alert. A named route without a trial is fail.
  - When it does not apply. The project has no unattended service or background work and the approved documents name no duty to tell someone about a software failure. Instructions for a lost device or a leak alone do not count as a duty to tell for this check.

- **Users have a way to report a problem**
  - How to check it. Find the contact or reporting path in the app or guide and confirm it is listed without sending a message.
  - When it does not apply. The project has no users or operators other than the builder. It also does not apply when the owner is the only user, even if the owner builds through AI agents.

- **Everything the approved Handover names exists**
  - How to check it. Find each item promised in the approved Handover and check that it opens or can be used.
  - When it does not apply. There is no approved Handover or it promises no items.
