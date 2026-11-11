`round_price(amount, currency=None)` now takes an optional currency. With "CHF" it rounds to the nearest 0.05 (halves round up, as before). With no currency, or any currency other than "CHF", it behaves exactly as it did, rounding to the cent. I added tests for CHF and for the unchanged default; the full suite passes.

Comments: I updated the `round_price` docstring, which said it always rounds to the cent, and added a one-line note on the CHF increment. The comments elsewhere (invoice lines, VAT, labels, reports) describe the default cent rounding, which still holds because none of those callers pass a currency, so I left them alone. If you later pass "CHF" from any of them, their "to the cent" wording will need revisiting.

I did not change any caller to pass a currency. You gave no reason for halves rounding up at 0.05, so I kept the existing half-up rule and recorded no rationale for it.
