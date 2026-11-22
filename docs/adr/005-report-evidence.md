# Report evidence

Keep the point text verbatim in the check file. Present it as a quote in the
report and escape markup from the checked project. Show a group result derived
from its rows. A failed check makes the group fail. A group passes when
applicable checks pass, and does not apply when none of its checks apply. The
report lists each reason under the group.

The report command takes `--same-builder` to disclose that the checker also
built the project. This keeps the disclosure out of the approved JSON shape.
