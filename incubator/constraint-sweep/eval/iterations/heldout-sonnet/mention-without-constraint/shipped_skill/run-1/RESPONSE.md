`round_price(amount, currency=None)` now rounds to the nearest 0.05 when `currency="CHF"` (halves round up, e.g. 2.025 -> 2.05). With no currency it is unchanged: the cent, halves up. Existing callers (VAT, invoice lines, labels, daily totals) pass no currency, so they behave as before.

I updated the `round_price` docstring to describe both modes and added a comment on the 0.05 step. I added tests for CHF rounding and for the unchanged default, in `tests/test_rounding.py`; all tests pass.

Note: none of the callers pass a currency yet, so CHF amounts in invoices, labels and reports are still rounded to the cent until they are updated to pass it. Say if you want that wired in. I did not record a reason for the 0.05 rule beyond what you told me.
