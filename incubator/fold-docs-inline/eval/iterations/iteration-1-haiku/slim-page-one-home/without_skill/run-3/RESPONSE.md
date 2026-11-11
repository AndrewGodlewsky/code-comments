I moved the code-facing parts of docs/billing.md into the code and left the rest for you to place.

What moved:
- billing/totals.py: the `invoice_total()` docstring now says totals round half-up, not half-even, and cites the e-invoice validator rejection (FIN-88).
- billing/lines.py: the `invoice_lines()` docstring now says the lines are sorted by SKU and why (customers check printed invoices against packing slips, which list items by SKU).

What I did not move:
- The "Who to ask" section. It names the finance team's FINQ queue for invoice disputes and the accounts-receivable lead for e-invoice format questions. That describes people and process, not the code, so it does not belong in a comment. It needs a home before docs/billing.md goes, for example the README or a team page. Tell me where it should go and I will add it.

What I left alone:
- docs/billing.md is still in place. Once the contacts have a new home, it can be deleted. I did not delete it because that would lose the contacts.
- docs/setup.md is not billing content, so it is unchanged.
- No code or test logic changed. `python -m unittest discover -s tests -t .` passes (2 tests).
