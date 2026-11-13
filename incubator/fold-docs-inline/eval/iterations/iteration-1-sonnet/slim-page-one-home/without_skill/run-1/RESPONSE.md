I removed docs/billing.md and moved its content as follows.

- Half-up rounding and the FIN-88 reason are now a comment in `billing/totals.py`, right above the `quantize` call in `invoice_total()`.
- The SKU-order reason (customers check printed invoices against packing slips) is now a comment in `billing/lines.py`, above the `sorted` call in `invoice_lines()`.
- I dropped the description of what each function returns. The docstrings and code already say it.
- The "Who to ask" section (disputes go to the FINQ queue, e-invoice format questions go to the accounts-receivable lead) is not about the code, so I put it in README.md instead of a code comment. Move it if you'd rather have it somewhere else.

I did not run the tests, and I made no other changes.
