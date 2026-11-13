I moved the code-level rationale from docs/billing.md into the code and left the file in place. The unit tests pass.

Changes:
- billing/totals.py: added a comment above the quantize call explaining the half-up rounding and why half-even is ruled out (the e-invoice validator rejects half-even totals, FIN-88). The docstring is unchanged.
- billing/lines.py: the invoice_lines docstring now says the lines are sorted by SKU, and a comment above the sort explains why (customers check printed invoices against packing slips, which list items by SKU).

Not moved:
- The "Who to ask" section of docs/billing.md (invoice disputes go to the FINQ queue; e-invoice format questions go to the accounts-receivable lead). This is contact information, not code rationale, so it does not belong in code comments. It needs a home before docs/billing.md is deleted, for example the README or a team page. I did not delete docs/billing.md for that reason.

Left alone:
- AGENTS.md already states the half-up rule and FIN-88.
- docs/setup.md is not billing-related.
- The tests did not need comments; their names explain the behaviour.
