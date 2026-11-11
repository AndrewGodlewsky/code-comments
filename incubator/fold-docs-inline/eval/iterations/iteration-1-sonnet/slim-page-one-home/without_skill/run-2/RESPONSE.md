I moved the two "why" notes from docs/billing.md into comments next to the code they explain:

- billing/totals.py: above the `quantize` call, a comment that totals round half-up rather than half-even because the e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py: above the `sorted` call, a comment that lines stay in SKU order because customers check printed invoices against packing slips, which list items by SKU.

I did not delete docs/billing.md. Its "Who to ask" section (invoice disputes go to the finance team's FINQ queue, questions about the e-invoice format go to the accounts-receivable lead) doesn't belong in the code, and nothing else in the repo holds it. Tell me where it should go (for example README.md) and I'll move it and delete the file. The first two paragraphs of the doc (what `invoice_total()` and `invoice_lines()` return) were already covered by the existing docstrings.

I didn't run the tests. The changes are comments only.
