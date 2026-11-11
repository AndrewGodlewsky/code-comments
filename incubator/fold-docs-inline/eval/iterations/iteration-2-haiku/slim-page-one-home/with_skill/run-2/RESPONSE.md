I folded docs/billing.md into the code. The two code facts moved into comments; the rest of the page is dropped or kept. I did not delete the page because it still holds kept claims.

Fate list, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal`" - Dropped. billing/totals.py:10-13 sums the amounts and returns a quantized Decimal.
2. "rounded to the cent" - Dropped. billing/totals.py:9 docstring and CENT quantize at :13.
3. "Totals are rounded half-up" - Dropped. billing/totals.py:13 uses rounding=ROUND_HALF_UP.
4. "not with Python's default half-even rounding, because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)" - Moved to billing/totals.py, invoice_total: comment at lines 11-12, above the quantize call.
5. "`invoice_lines()` returns the order's lines sorted by SKU" - Dropped. billing/lines.py:32 sorts by sku; tests/test_billing.py test_lines_come_back_in_sku_order covers it.
6. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU" - Moved to billing/lines.py, invoice_lines: comment at lines 30-31, above the sorted call.
7. "# Billing" heading - Kept (page title, content remains).
8. "## Who to ask" heading - Kept.
9. "Invoice disputes go to the finance team's FINQ queue, not to engineering." - Kept. Ownership routing with no code home.
10. "Questions about the e-invoice format go to the accounts-receivable lead." - Kept. Ownership routing with no code home.

Not migrated: none. Every code-checkable claim matches the code.

Other files:
- AGENTS.md:5 states the same moved fact ("Invoice totals round half-up, never half-even: the e-invoice validator rejects half-even totals (FIN-88)."). I did not edit it, per scope. Please reconcile it with the new comment, or keep it as the single agent-facing copy.
- No file links to docs/billing.md or to the removed sections.

Gaps and page status:
- docs/billing.md was not deleted. It still holds the "Who to ask" section (two sentences). Retiring the page needs a new home for those two sentences first, such as a team page or the README. Then delete it.
- The FIN-88 rationale (the tax office validator) is outside this repository and cannot be checked here. It is moved as written, because the code's ROUND_HALF_UP depends on it.
- docs/setup.md was not in the retirement scope and is unchanged.
- Tests pass: python -m unittest discover -s tests -t . (2 tests, OK).
