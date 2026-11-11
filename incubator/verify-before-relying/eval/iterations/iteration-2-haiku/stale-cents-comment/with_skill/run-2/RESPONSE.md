I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order.

The fee is `Decimal("0.30")`, dollars, because the tests use `Decimal` dollar amounts (`Decimal("12.50")`) and the code runs that way. The code has no integer-cents convention.

Premise check: `orders/model.py` said `total` was "amount due, in integer cents". That was false. The tests pin dollars as `Decimal`, and a probe confirmed it: `Decimal("12.50") + Decimal("0.30")` gives `Decimal('12.80')`. I corrected that comment in place to "amount due, in dollars as Decimal" and changed no code. The fee is added in the same unit.

Checks: `add_card_fee` on a `Decimal("12.50")` order gives `Decimal('12.80')` and status `open`. The existing test suite passes (3 tests). I did not add a test for the new function.
