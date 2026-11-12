I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the order. The total is in integer cents, as documented on `Order`, so the fee is stored as `30`.

A quick check with an order totalling 1000 cents gave 1030.

I did not add tests, since you did not ask for them. I also did not commit anything, because this exercise excludes git.
