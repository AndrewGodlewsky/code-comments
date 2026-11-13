`round_price` now takes an optional `currency` argument. `round_price(amount, "CHF")` rounds to the nearest 0.05 with halves rounding up, so 1.03 becomes 1.05 and 1.02 becomes 1.00. With no currency, and for any currency other than "CHF", it rounds to the cent exactly as before.

No caller passes a currency yet, so VAT, invoice lines, labels and daily totals come out as they did, and the notes in those files about round_price still hold. I added a test for the CHF case to tests/test_rounding.py, and the tests pass.
