I moved the two code-specific facts from docs/billing.md into comments, and the page now holds only the "Who to ask" section.

Moved into comments (code logic unchanged):
- billing/totals.py, above the `quantize` call: totals round half-up rather than half-even because the tax office's e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py, above the `sorted` call: lines stay in SKU order because customers check printed invoices against packing slips, which list items by SKU.

Left out because the code already shows it: that `invoice_total()` sums the line amounts and returns a `Decimal` rounded to the cent, and that `invoice_lines()` returns lines sorted by SKU (only the reason for the sorting was added).

Contradictions: none. Every claim on the page matches the code, and the two tests agree.

Kept in docs/billing.md: "Who to ask" (the FINQ queue for invoice disputes, the accounts-receivable lead for e-invoice format questions). No code governs it, so it stays in a document. docs/billing.md is therefore not empty, and you may want to move that section somewhere else before deleting the file.

Note: AGENTS.md also states the half-up rule and FIN-88. I left it, since it is agent guidance rather than part of the page being retired. No new files were created, apart from this message.
