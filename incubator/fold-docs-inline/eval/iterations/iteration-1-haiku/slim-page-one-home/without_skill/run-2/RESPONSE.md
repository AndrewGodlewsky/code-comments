I've retired docs/billing.md and moved the parts that describe the code into the code itself:

- billing/totals.py: the invoice_total() docstring now says totals round half-up, not half-even, because the e-invoice validator rejects half-even totals (FIN-88).
- billing/lines.py: the invoice_lines() docstring now says lines are sorted by SKU, because customers check printed invoices against packing slips, which list items by SKU.

The "Who to ask" section is not about the code, so I moved it to README.md rather than into a comment. Invoice disputes go to the finance team's FINQ queue, and e-invoice format questions go to the accounts-receivable lead.

docs/setup.md is unchanged because it covers the whole project, not billing. AGENTS.md still carries the half-up rule for agents, so it is unchanged too.

The test suite passes (`python -m unittest discover -s tests -t .`, 2 tests OK).
