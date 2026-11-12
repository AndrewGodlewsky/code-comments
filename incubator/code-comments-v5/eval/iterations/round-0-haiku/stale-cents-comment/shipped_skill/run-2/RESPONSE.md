I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The fee is a `Decimal("0.30")` constant, because the order totals in this codebase are dollars stored as `Decimal` (the tests use values like `Decimal("12.50")`).

I also corrected a false comment in `orders/model.py`. The `Order.total` comment said "amount due, in integer cents", but the tests and `apply_discount` both treat the total as dollars in a `Decimal`. I changed it to "amount due, in dollars as a Decimal". If the total really is meant to be integer cents, tell me and I will change the fee to `30` and fix the comment the other way.

Please confirm the total is dollars as a `Decimal`. I checked that `add_card_fee(Order("A-1", Decimal("12.50")))` gives a total of `12.80`. I did not add tests and did not use git.
