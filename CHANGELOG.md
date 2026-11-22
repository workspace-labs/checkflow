# Changelog

## 0.2.0 — 2026-11-22

- Place checkflow third in the whole-project workflow, after project-docs approval and the build from approved documents and the plan. Deployment and handover wait for a clean check.

## 0.1.2 — 2026-11-22

- The shared path check now refuses absolute paths outside the project.

## 0.1.1 — 2026-11-22

- Fix the draft Arabic preview, which was refused after choosing a first page. The draft mark now sits in the page label.
- Print messages as UTF-8 on every platform, so Arabic stays readable in captured Windows output.
- Keep fixtures and snapshots in LF with `.gitattributes`.
- Make the tests read files and PDF text as UTF-8.
- Skip two Arabic PDF text tests, with a clear reason, when `pdftotext` is not Poppler.
- Say that the GitHub repository is live.
- Use plain English refusal reasons for Arabic previews and documents so legacy Windows consoles can display them.
- Name an inaccessible output file and explain how to retry.
- Check draft labels on every preview page without a PDF text reader.
- Record the Windows 11 test in the README limits.

## 0.1.0 — 2026-11-22

First release.

- Check approved client points, record changes and cover the ten basic groups.
- Write a full check and preserve finished rounds while opening a new one.
- Include a small sample project and command tests that use only Python's standard library.
- Refine known-secret matching so ordinary project words do not block a check.
- Give the checker clear rules for incomplete proof, checks that apply and security problems.
- Confirm a successful check and date the sample project's delay note.
- Let each user choose a first page, with an optional credit line on the last page.
- Make the client's project document, with its dates, as a PDF and an HTML page.
- Make the technical document, with setting names only and no text from the project's README.
- Add Arabic documents from a translation the owner reads and confirms.
- Let the owner accept an open security problem with a written reason.
- Split a partly covered point into `wrong` and `untried`.
- Try every stated limit, and merge an optional second checker with the worse result winning.
- Add the README guide and its picture.
- The full check tells the owner to read the proofs before trusting Clean.
