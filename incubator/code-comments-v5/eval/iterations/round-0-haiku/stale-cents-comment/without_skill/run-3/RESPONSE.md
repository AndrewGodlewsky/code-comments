I added `add_card_fee(order)` in `orders/fees.py`. It adds the 30-cent card processing fee to `order.total` and returns the same order object. I also added `tests/test_fees.py`. All 6 tests in the repo pass (`python -m unittest discover -s tests -t .`).

The fee is stored as `CARD_PROCESSING_FEE_CENTS = 30` and added directly, because `orders/model.py` documents `Order.total` as "amount due, in integer cents".

Please check this before relying on the fee amount. `tests/test_discounts.py` builds orders with `Decimal` dollar values such as `Decimal("12.50")`, which contradicts the "integer cents" comment in `model.py`. If totals are really dollars, the fee should be `Decimal("0.30")`, not `30`, and adding 30 would charge $30. I did not change `model.py` or the discount code, since resolving which unit is correct is outside this request. Once that is settled, the comment in `model.py` should be corrected or the fee changed to match.
