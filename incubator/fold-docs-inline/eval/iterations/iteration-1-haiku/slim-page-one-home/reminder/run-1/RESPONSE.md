I moved the code-specific content of docs/billing.md into the code and into README.md, then deleted docs/billing.md. The unit tests pass (`python -m unittest discover -s tests -t .`, 2 tests OK).

What I did with each claim on the page:

- "`invoice_total()` adds up the line amounts and returns a Decimal rounded to the cent." Left out. billing/totals.py already shows this (sum of `line.amount`, `quantize(CENT, ...)`).
- "Totals are rounded half-up ... the e-invoice validator rejects totals rounded half-even (FIN-88)." Moved to a comment beside the `quantize` line in billing/totals.py. The code shows ROUND_HALF_UP, but not the reason, so the reason went into the comment.
- "`invoice_lines()` returns the order's lines sorted by SKU ... customers check printed invoices against their packing slips." Moved to a comment beside the `sorted(...)` line in billing/lines.py. The code shows the sort, not the reason.
- "Who to ask" (FINQ queue for invoice disputes, accounts-receivable lead for e-invoice format). No code to sit beside, so it went into README.md as a new "Who to ask" section.

Nothing on the page was contradicted by the code, so I did not flag any conflicts.

Things you should know:

- AGENTS.md also states the half-up rule with the FIN-88 reason. I left AGENTS.md alone because it is not the page being retired. It now duplicates the totals comment, so you may want to trim one of them.
- docs/setup.md is untouched. The only file removed is docs/billing.md, and nothing else in the repo references it.
- No code logic changed. The only code edits are the two comments. No new files were created apart from this RESPONSE.md.

Changed files:
- billing/totals.py (comment added)
- billing/lines.py (comment added)
- README.md ("Who to ask" section added)
- docs/billing.md (deleted)
- RESPONSE.md (this message)
