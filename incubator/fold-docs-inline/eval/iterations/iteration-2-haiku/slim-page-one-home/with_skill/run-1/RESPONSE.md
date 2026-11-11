I folded docs/billing.md into the code. Fate list, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." Dropped. billing/totals.py `invoice_total` sums the amounts (line 10), quantizes to CENT (line 11), and its docstring says rounded to the cent.
2. "Totals are rounded half-up, not with Python's default half-even rounding" Moved to billing/totals.py `invoice_total` docstring. Evidence: ROUND_HALF_UP at line 11; test_total_rounds_half_up.
3. "because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)." Moved to the same docstring, FIN-88 kept.
4. "`invoice_lines()` returns the order's lines sorted by SKU." Dropped. billing/lines.py `invoice_lines` line 17 is `sorted(..., key=lambda line: line.sku)`; test_lines_come_back_in_sku_order covers it.
5. "They are kept in SKU order" Moved to billing/lines.py `invoice_lines` docstring as a constraint.
6. "because customers check printed invoices against their packing slips, which list items by SKU." Moved (reason) to the same docstring.
7. "Invoice disputes go to the finance team's FINQ queue, not to engineering." Kept as written. Ownership contact, no code home.
8. "Questions about the e-invoice format go to the accounts-receivable lead." Kept as written. Ownership contact, no code home.
9. Headings "# Billing" and "## Who to ask" are not claims; both kept because the kept claims sit under them.
Not migrated: none. No claim contradicts the code.

Other files:
- AGENTS.md line 5 states the same half-up / FIN-88 rule as the moved docstring. Not edited (instruction file); reconcile it yourself.

Links:
- No file links to docs/billing.md or to a removed section. Grep found no references outside the page.

Gaps and state:
- docs/billing.md is not deleted. It still holds the two kept "Who to ask" claims. Decide where those contacts go (kept in the page, moved to README, or elsewhere), then delete the page.
- No module overview claim was on the page, so no module docstring was needed.
- Tests: `python -m unittest discover -s tests -t .` passes (2 tests). No new files were added and no bytecode caches were written.
- Changed files: billing/totals.py, billing/lines.py, docs/billing.md.
