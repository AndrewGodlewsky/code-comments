I removed two dead functions from `events/handlers.py`: `handle_refund_v1` and `format_old_receipt`.

- **`handle_refund_v1`**: nothing imports or calls it. `config/routes.ini` doesn't list a `refund_v1` kind, so `events/dispatch.py` can't reach it through its name lookup either. `CHANGELOG.md:7` says that kind is no longer accepted.
- **`format_old_receipt`**: no references anywhere. `CHANGELOG.md:10` says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `CHARGEBACK_FEE`. `handle_chargeback` has no direct caller, but `config/routes.ini:3-5` says `dispatch` looks handlers up by name (`handle_<kind>`) for every kind listed there, and `chargeback` is switched on. Removing it would break chargeback events. `handle_refund` and `handle_payout` are used the same way, and also have direct callers in the tests and `payouts/batch.py`.

Nothing stale found. I left `CHANGELOG.md` alone because it records history. I haven't run the tests.
