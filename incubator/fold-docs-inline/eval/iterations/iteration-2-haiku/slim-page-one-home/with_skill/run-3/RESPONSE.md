I folded docs/billing.md into the code. Fate list, in page order:

1. "`invoice_total()` adds up the line amounts and returns a `Decimal` rounded to the cent." — Dropped. billing/totals.py `invoice_total` sums `line.amount` and calls `quantize(CENT)`; its docstring already says "rounded to the cent".
2. "Totals are rounded half-up, not with Python's default half-even rounding, because the tax office's e-invoice validator rejects totals rounded half-even (FIN-88)." — Moved to billing/totals.py `invoice_total` (docstring, added paragraph). The code shows ROUND_HALF_UP, but not the half-even alternative or the reason. FIN-88 kept.
3. "`invoice_lines()` returns the order's lines sorted by SKU." — Dropped. billing/lines.py `invoice_lines` returns `sorted(..., key=lambda line: line.sku)`; test_lines_come_back_in_sku_order covers it.
4. "They are kept in SKU order because customers check printed invoices against their packing slips, which list items by SKU." — Moved to billing/lines.py `invoice_lines` (docstring, added paragraph). The ordering is in code; the reason is not.
5. "# Billing" — heading, kept (kept content remains under it).
6. "## Who to ask" — heading, kept.
7. "Invoice disputes go to the finance team's FINQ queue, not to engineering." — Kept. Organisational routing that no code here relies on.
8. "Questions about the e-invoice format go to the accounts-receivable lead." — Kept, same reason as 7.

Results:
- docs/billing.md now holds only "# Billing", "## Who to ask" and the two kept routing sentences. I did not delete it, because a kept claim remains. The routing content needs a home from you (another doc, or an owner decision); once it has one, the page can be deleted.
- Tests pass: `python -I -m unittest discover -s tests -t .` runs 2 tests, OK.
- No other file was changed. docs/setup.md, README.md, AGENTS.md and the tests are untouched.

Files that also state a moved fact (for you to reconcile; not edited):
- AGENTS.md line 5: "Invoice totals round half-up, never half-even: the e-invoice validator rejects half-even totals (FIN-88)." This duplicates the totals.py docstring. AGENTS.md is an instruction file, so I left it alone.

Links to the page or to removed sections: none found. No file in the repo links to docs/billing.md.

Gaps for you to fill:
- Where the "Who to ask" routing should live, since the page is not yet deletable.
- Whether AGENTS.md line 5 should stay as is, given the new totals.py docstring.
