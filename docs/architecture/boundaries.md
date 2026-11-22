# Code boundaries

The command entry point connects the reader, validation, round logic, report
and file storage. The approved document reader owns Markdown and approval
stamps. Validation owns the check file contract. Round logic owns point
matching and carry-over. The report formats a validated check. Storage owns
project paths and writes. The checker supplies judgments and evidence.

Test code invokes the command from outside these modules. The basic-check
asset supplies the checks, and the reference gives the checker ways to try them.
