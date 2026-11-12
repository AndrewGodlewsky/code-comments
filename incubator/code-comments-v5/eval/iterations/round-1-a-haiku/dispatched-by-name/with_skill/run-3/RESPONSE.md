I removed two functions from `events/handlers.py` that nothing calls any more:

- `handle_refund_v1`. Nothing references it, and the `refund_v1` kind is not in `config/routes.ini`, so dispatch can never reach it. CHANGELOG 1.3.0 records that the kind was dropped.
- `format_old_receipt`. Nothing references it. CHANGELOG 1.2.0 records that receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. `dispatch.py` reaches the `handle_<kind>` handlers by name through `getattr`, and `config/routes.ini` switches on `refund`, `chargeback` and `payout`. `payouts/batch.py` and `tests/test_handlers.py` also call them directly. The comment in `routes.ini` says the same thing, so I left it alone.

No comment in the remaining code became false, so I changed no others. I left the CHANGELOG history entries as written.

The test suite passes (5 tests, `python -m unittest discover -s tests -t .`). I did not commit anything, because this exercise excluded git.
