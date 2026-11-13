I folded docs/billing.md into the code. The page is not deleted, because the "Who to ask" section has no code to sit beside and stays as written.

Fate list, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." Dropped. The docstring, `sum(...)` and `quantize(CENT, ...)` in billing/totals.py already say it.
2. "Totals are rounded half-up." Dropped. `ROUND_HALF_UP` in billing/totals.py states it, and `test_total_rounds_half_up` covers it.
3. "...not with Python's default half-even rounding, because the tax office's e-invoice validator rejects half-even totals (FIN-88)." Moved. It is now a comment above the `quantize` call in `invoice_total`, billing/totals.py, with FIN-88 kept.
4. "`invoice_lines()` returns the order's lines sorted by SKU." Dropped. `sorted(..., key=lambda line: line.sku)` in billing/lines.py states it, and `test_lines_come_back_in_sku_order` covers it.
5. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." Moved. It is now a comment above the `return sorted(...)` in `invoice_lines`, billing/lines.py.
6. "Invoice disputes go to the finance team's FINQ queue, not to engineering." Kept. It is an operational fact about people and has no code owner.
7. "Questions about the e-invoice format go to the accounts-receivable lead." Kept, for the same reason.

Nothing was not migrated. The page and the code agree on every claim.

Other places that state a moved fact: AGENTS.md line 5 repeats the half-up rule and FIN-88. I left it alone for you to reconcile.

Links to the page: none found in README.md, AGENTS.md or docs/setup.md.

Gaps: none. The page now holds only the heading and the "Who to ask" section. If you want it gone entirely, that contact information needs another home.
