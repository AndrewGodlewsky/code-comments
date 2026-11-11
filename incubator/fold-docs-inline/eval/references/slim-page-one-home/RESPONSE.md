docs/billing.md is slimmed rather than deleted. Claim by claim:

- **`invoice_total()` adds the line amounts and returns a `Decimal` rounded to the cent.** Dropped: the function and its docstring say this.
- **Totals round half-up because the e-invoice validator rejects half-even totals (FIN-88).** Moved to a comment above the `quantize` call in `invoice_total`, billing/totals.py.
- **Lines are kept in SKU order because customers match invoices to packing slips.** Moved to a comment above the `sorted` call in `invoice_lines`, billing/lines.py. The "sorted by SKU" part was dropped; the code shows it.
- **Who to ask (FINQ queue, accounts-receivable lead).** Kept on docs/billing.md. It is about people, not code, so it has nothing to sit beside, and that section is now all the page holds. If you'd rather it lived somewhere else, say where and I'll move it.

AGENTS.md also states the FIN-88 rounding rule (line 5). I didn't edit it, since it's an instruction file; you may want to drop that line now that the reason sits beside the code, or keep it as a rule for agents.

No code changed and I added no files.
