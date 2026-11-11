I retired docs/billing.md and moved its content as follows.

Checked against the code:
- "invoice_total() adds up the line amounts and returns a Decimal rounded to the cent" is shown by billing/totals.py, so I left it off the page without a comment.
- "invoice_lines() returns the order's lines sorted by SKU" is shown by billing/lines.py, so I left that off too.
- Nothing on the page is contradicted by the code. The half-up rounding and SKU order both match the implementation and the tests in tests/test_billing.py.

Moved into code comments:
- billing/totals.py, above the quantize() return: why totals round half-up rather than half-even (the e-invoice validator rejects half-even totals, FIN-88).
- billing/lines.py, above the sorted() return: why lines stay in SKU order (customers check printed invoices against packing slips, which list items by SKU).

Moved into a document (no code to sit beside):
- The "Who to ask" section (finance FINQ queue for invoice disputes, accounts-receivable lead for e-invoice format questions) is now a section in README.md.

Other changes:
- Deleted docs/billing.md, since it is being retired and all of its content has been moved.
- No code logic changed, and no new files were created other than this RESPONSE.md.

Left alone, for your decision:
- AGENTS.md line 5 repeats the half-up rounding rule with the FIN-88 reference. It is agent guidance rather than the retiring page, so I did not touch it. It now duplicates the totals.py comment, and you may want to keep only one of the two.
