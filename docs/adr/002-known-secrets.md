# Known secret values

Build 1 reads only `.env` and `.env.local` in the project root. It reads simple
one-line assignments with optional quotes, an optional `export` prefix and
an optional trailing comment. It reads nonempty literal values from names with
one of these components, ignoring case: `PASSWORD`, `PASSWD`, `PASSCODE`,
`SECRET`, `TOKEN`, `CREDENTIAL`, `CREDENTIALS`, `API_KEY`, `PRIVATE_KEY` or
`ACCESS_KEY`. Underscores separate components. The tool reads both files
without using the process environment or expanding references. Spaces inside
quoted values are preserved.

A distinctive value has at least eight characters and no whitespace. It
either has both a letter and a digit or has a symbol other than a period,
underscore or hyphen. Match it literally, even next to punctuation.

Match every other value in full after its setting name and an `=` or `:`.
The name is case-insensitive and the value is case-sensitive. Quotes and
inline code delimiters can mark the name or value. The name can also be bold.
A bare value after a colon must end the field. An exact named pair in a JSON
object also counts.

Apply this rule to copied approved text, check data and the rendered report.
A refusal in approved text names the file and line. Refusals give no value.
This rule can miss unlabelled short or word-like credentials, values in
other settings files, and encoded or split values. A distinctive value that
also occurs in ordinary text can still trigger it. The checker keeps secret
values out of every field.

## Document preparation

Before drawing the project or technical document, checkflow checks the text
selected from the approved documents and document records. It checks for
literal credentials in authorization and bearer headers,
addresses with a user and password, attached `-p` options, settings assignments,
and options named for credentials. A refusal identifies the source file and
line. Its message omits the credential. Runtime references and marked
placeholders can still appear in examples. Settings files supply names only.

The check may miss an unlabelled credential, a credential with an unfamiliar
label or option, or one encoded, assembled from separate fields, or stored in
an image or embedded in font data. An ordinary value that resembles a credential
may trigger a refusal.

README.md is handed over as supplied. It is outside the approved document
sources, and a literal credential in a command can look like an ordinary word
or path. To prevent those values from reaching the generated documents or
translation records, section 4 uses the approved Handover's “Running it”
text and adds a fixed, localized reference when README.md exists. The checker
records the location of any credential it finds in README.md under “No
password, key or token is written in the code”.
