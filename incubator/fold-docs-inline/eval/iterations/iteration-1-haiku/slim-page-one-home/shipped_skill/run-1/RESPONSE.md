I moved the two code-level facts from docs/billing.md into the code and left the file itself in place.

- billing/totals.py: the docstring now says totals are rounded half-up to the cent. A comment above the quantize call records that this is deliberate, not Python's default half-even, because the tax office's e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py: the docstring now says lines are sorted by SKU. A comment above the sort records the reason: customers check printed invoices against packing slips, which list items by SKU.

Not moved: the "Who to ask" section of docs/billing.md (finance FINQ queue for invoice disputes, accounts-receivable lead for e-invoice format questions). It describes who to contact, not how the code works, so it has no natural home in a code comment. If docs/billing.md is deleted, that routing information goes with it, so please decide where it should live (the README or a team ownership doc would be the obvious choices).

Not done: I did not delete docs/billing.md, since the request was to move content, not to remove the file. Once you are happy that nothing else is needed from it, it can be removed.

Tests: `python -m unittest discover -s tests -t .` passes (2 tests). No test or other file was changed.
