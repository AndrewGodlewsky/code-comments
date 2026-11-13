I added `add_card_fee(order)` in `orders/fees.py`. One thing in the codebase was wrong and affects the fee.

**Wrong claim:** `Order.__init__` in `orders/model.py` has the comment `# amount due, in integer cents`. The code and tests treat the total as a Decimal in dollars. `tests/test_discounts.py` builds orders with `Decimal("12.50")`, and `apply_discount` divides by 100, which would turn integer cents into floats. If I had trusted the comment, the fee would have been `30` and would have added 30 dollars. I corrected the comment to `# amount due, a Decimal in dollars`. No code changed there.

**What I built:** `add_card_fee` adds `Decimal("0.30")` to `order.total` and returns the order. The fee is a named constant, `CARD_PROCESSING_FEE`. I added `tests/test_fees.py` with two tests (12.50 becomes 12.80, and the same order object is returned). The full test suite passes.

**Checked and trusted:** `apply_discount`'s docstring (percent 0 to 100, returns the order) matches its body and tests. I left it as written.
