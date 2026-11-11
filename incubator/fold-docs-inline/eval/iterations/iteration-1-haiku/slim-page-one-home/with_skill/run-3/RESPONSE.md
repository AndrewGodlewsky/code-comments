I went through docs/billing.md claim by claim and moved what belongs beside the code. The page is slimmed rather than deleted, because one section still has no code home.

Fate list, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." Dropped. billing/totals.py `invoice_total` sums `line.amount` and returns `total.quantize(CENT, ...)`, and its docstring already says rounded to the cent.
2. "Totals are rounded half-up, not with Python's default half-even rounding, because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)." Moved to billing/totals.py `invoice_total`, as a comment above the `return` line. Code evidence: `ROUND_HALF_UP`. The same rule also appears in AGENTS.md line 5.
3. "`invoice_lines()` returns the order's lines sorted by SKU." Dropped. billing/lines.py `invoice_lines` returns `sorted(lines, key=lambda line: line.sku)`.
4. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." Moved to billing/lines.py `invoice_lines`, as a comment above the `return` line.
5. "## Who to ask" heading. Kept, because content remains under it.
6. "Invoice disputes go to the finance team's FINQ queue, not to engineering." Kept. Operational ownership with no code home.
7. "Questions about the e-invoice format go to the accounts-receivable lead." Kept. Same reason.

Not migrated: none. Every claim matched the code.

Other files stating a moved fact:
- AGENTS.md line 5 states the half-up rule with FIN-88. I did not edit it, since it is an instruction file out of scope. Reconcile it yourself if you want the rule in one place.

Links: nothing in the repository links to docs/billing.md or to a removed section. README.md, AGENTS.md and docs/setup.md were checked.

Gaps and decisions for you:
- docs/billing.md is not deleted. It still holds "Who to ask", which has no code home. Decide where that section should live, then delete the page.
- The two moved comments are not covered by the test suite as comments. The existing tests `test_total_rounds_half_up` and `test_lines_come_back_in_sku_order` do cover the behaviour. The suite passes (2 tests, OK).

Changed files: billing/totals.py, billing/lines.py, docs/billing.md. RESPONSE.md was added as requested. No code, tests, AGENTS.md or other docs were changed.
