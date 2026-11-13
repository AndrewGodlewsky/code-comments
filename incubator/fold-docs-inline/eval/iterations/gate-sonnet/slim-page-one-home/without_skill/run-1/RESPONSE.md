I moved the two "why" explanations from docs/billing.md into comments beside the code they explain:

- `billing/totals.py`: a comment above the rounding explains that totals round half-up because the tax office's e-invoice validator rejects half-even totals (FIN-88).
- `billing/lines.py`: a comment above the sort explains that lines stay in SKU order because customers check printed invoices against packing slips, which list items by SKU.

The description of what `invoice_total()` and `invoice_lines()` do was already in their docstrings, so I did not repeat it.

I did not delete docs/billing.md. Its "Who to ask" section (invoice disputes go to the finance team's FINQ queue; e-invoice format questions go to the accounts-receivable lead) is not about the code, so it does not belong in code comments, and nothing else in the repo carries it. Before you delete the file, decide where that section should live (for example the README). Tell me if you want me to place it and remove the file.

I did not run the tests. The changes are comments only.
