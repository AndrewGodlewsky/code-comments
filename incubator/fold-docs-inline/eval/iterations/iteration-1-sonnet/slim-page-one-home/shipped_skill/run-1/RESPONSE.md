I moved the two code-related explanations from docs/billing.md into comments beside the code:

- billing/totals.py: a comment at the rounding line says totals round half-up rather than half-even because the e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py: a comment at the sort says lines stay in SKU order because customers check printed invoices against packing slips, which list items by SKU.

The sentence saying `invoice_total()` adds the lines and rounds to the cent was already covered by its docstring, so I didn't copy it.

I did not delete docs/billing.md. Its "Who to ask" section (invoice disputes go to the finance team's FINQ queue, and e-invoice format questions go to the accounts-receivable lead) is not code knowledge, so I left it unmoved. Tell me where it should live, such as the README, and I can move it and delete the file.

The tests pass.
