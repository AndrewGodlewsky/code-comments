I moved the two code-level explanations from docs/billing.md into the code and left the file in place.

- billing/totals.py: the half-up rounding rationale (FIN-88) now sits beside the quantize call, with the reason the e-invoice validator needs it.
- billing/lines.py: `invoice_lines()` docstring now states the SKU ordering, and a comment above the sort gives the reason (customers check printed invoices against packing slips, which list items by SKU).

Not moved: the "Who to ask" section. It is contact routing (FINQ queue for invoice disputes, accounts-receivable lead for e-invoice format), not something the code explains, so it does not belong in a comment. It needs a new home (for example a CODEOWNERS or contacts note) before docs/billing.md is deleted. I have not deleted docs/billing.md for that reason.

Tests: `python -m unittest discover -s tests -t .` passes (2 tests). No test or AGENTS.md text was changed.
