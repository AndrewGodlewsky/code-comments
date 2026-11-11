I removed two functions from `events/handlers.py` that nothing calls any more:

- `handle_refund_v1`. Nothing in the code calls it. `config/routes.ini` does not list a `refund_v1` kind, so dispatch can never reach it. CHANGELOG 1.3.0 says the kind is no longer accepted.
- `format_old_receipt`. Nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. Each one is still in use. Dispatch reaches the three handlers by name, as `routes.ini` describes. `payouts/batch.py` calls `handle_payout`, and `CHARGEBACK_FEE` is used by `handle_chargeback`.

The unit tests pass (5 of 5). I did not change `CHANGELOG.md`, `README.md` or `config/routes.ini`. Their comments are still accurate after the removal.
