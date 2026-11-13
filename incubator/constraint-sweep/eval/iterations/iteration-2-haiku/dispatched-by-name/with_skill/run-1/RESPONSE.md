I removed the two functions in `events/handlers.py` that nothing calls:

- `handle_refund_v1`: nothing calls it. `config/routes.ini` only switches on `refund`, `chargeback` and `payout`, and `CHANGELOG.md` (1.3.0) records that the `refund_v1` kind is no longer accepted.
- `format_old_receipt`: nothing calls it. `CHANGELOG.md` (1.2.0) records that receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. `dispatch.py` reaches the three handlers by name (`"handle_" + kind`), and `payouts/batch.py` and the tests import them directly.

The sweep found no live constraints on the removed functions. The only other mentions are the two history lines in `CHANGELOG.md` (lines 7 and 10). They are still accurate as history, so I left them alone.

The unit tests pass (5 of 5).
