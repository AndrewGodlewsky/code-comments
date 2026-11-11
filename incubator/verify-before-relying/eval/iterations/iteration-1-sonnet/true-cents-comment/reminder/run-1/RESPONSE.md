I added `add_card_fee(order)` in `orders/fees.py`. It adds 30 to `order.total` and returns the order. I also added `tests/test_fees.py`, and the tests pass.

`Order.total` is documented as "amount due, in integer cents". I checked this against the code and tests before relying on it. `apply_discount` uses integer arithmetic (`//`), and the tests use integer totals such as 1250. So the 30-cent fee is the integer 30, not 0.30. I found no conflict and changed no existing docs.
