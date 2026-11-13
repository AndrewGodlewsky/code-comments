I moved the two code-specific facts from docs/billing.md into comments and kept the one fact that has no code to sit beside. I changed no code, only added comments, and created no new files besides this message.

Moved into comments (and removed from the page):
- billing/totals.py, above the `quantize(..., ROUND_HALF_UP)` call: totals round half-up rather than half-even because the tax office's e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py, above the `sorted(...)` call in `invoice_lines()`: lines stay in SKU order because customers check printed invoices against packing slips, which list items by SKU.

Left out because the code already shows it:
- That `invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent. The code and its docstring say this.
- That `invoice_lines()` sorts by SKU. The `sorted(...)` call shows what happens, so only the reason was moved.

Kept in docs/billing.md:
- "Who to ask" (invoice disputes go to the FINQ queue, e-invoice format questions go to the accounts-receivable lead). It is not about any code, so it stays in a document. The page is now just this section.

Contradictions: none. Every claim I checked matched the code, and the tests cover both behaviours.

Note: AGENTS.md also states the half-up rule and FIN-88. I left it alone, as it is an instruction for agents rather than part of the page you are retiring.
