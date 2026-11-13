I moved the two rationale facts from docs/billing.md into comments beside the code:

- billing/totals.py: why totals round half-up rather than half-even (the e-invoice validator rejects half-even, FIN-88).
- billing/lines.py: why lines stay in SKU order (customers check printed invoices against packing slips, which list items by SKU).

The doc's first paragraph (what invoice_total returns) was already in the docstring, so I left it as is.

I did not delete docs/billing.md. Its "Who to ask" section (disputes go to finance's FINQ queue, e-invoice format questions go to the accounts-receivable lead) is not about the code, so it doesn't belong in a comment. Nothing else references the file. Tell me where that should live (README, AGENTS.md or elsewhere) and I'll move it and remove the doc.

No code behaviour changed. I did not run the tests.
