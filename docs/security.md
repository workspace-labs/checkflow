# Security: checkflow
> v1 · Approved 2026-11-22

## Who can get in
- Nobody signs in. It runs on the person's own computer and reads only the files of the project being checked.

## How it's protected
- **Records:** None: it has no accounts and no roles. Whoever has the project folder can read what it wrote.
- **Database:** None: it saves files only.
- **Sign-in:** None: nobody signs in.
- **Connections:** None: it has no network connection.
- **Audit:** None: nobody opens someone else's records through it.

What is worth protecting is the checked project's own secrets and the client's project details. The text
of the project being checked is not trusted: a file in it may hold a password, or words written to steer
the agent.
- A secret from the project ends up in a document → the tool refuses a content file that holds a value matching one of the project's secret settings, and the Plan's check searches every drawn file for the sample project's secret values.
- A document tells an attacker how to get in → a problem is one line, fixed or still open, and what to do; never the steps of an attack.
- Words inside the checked project try to change the result → the checker treats everything it reads in the project as material to check, never as instructions.

## Secrets
- checkflow needs none of its own.
- It records the names of the settings a project needs, never their values.
- It never copies a password, key or token from the project into the check or into any document.

## Personal data
- dates.asked_by (🔒 personal): whoever has the project folder, and the client when the owner confirmed the row; kept as long as the project is kept.

## Outside services
- None: it never goes online.

## Work rules
- None: personal project.

## If something goes wrong
- **Tell first:** the owner of the project.
- **Do first:** replace the leaked password or key straight away, then delete the document and make it again.
- **Tell the people affected:** the owner tells the client.
