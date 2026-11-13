I removed two dead functions from `events/handlers.py`: `handle_refund_v1` and `format_old_receipt`.

- `handle_refund_v1` has no callers. The 1.3.0 changelog says `handle_refund` replaced it and the `refund_v1` kind is no longer accepted. `config/routes.ini` doesn't list that kind either.
- `format_old_receipt` has no callers. The 1.2.0 changelog says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, along with `CHARGEBACK_FEE`. Searching for callers makes `handle_refund` and `handle_chargeback` look unused, but they aren't. `events/dispatch.py` looks handlers up by name (`"handle_" + kind`) for every kind switched on in `config/routes.ini`. Deleting either one would break every event of that kind. `handle_payout` is also called directly from `payouts/batch.py`.

I didn't run the tests.
