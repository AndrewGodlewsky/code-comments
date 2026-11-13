I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order, following the style of `apply_discount` in `orders/discounts.py`.

`Order.total` is in integer cents, so the fee is stored as `CARD_FEE_CENTS = 30` and added directly. I did not add a test, since you did not ask for one.

Comment check: I added only a module docstring and a function docstring that state the contract. I did not record a reason for the fee beyond your description, so the code does not say why the fee exists or where the 30-cent figure comes from. If you want that recorded beside the constant, please send me the source, such as the processor's pricing terms or a ticket.
