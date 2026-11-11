I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`: nothing calls it. The `refund_v1` kind isn't in `config/routes.ini`, and the 1.3.0 changelog says `handle_refund` replaced it and the kind is no longer accepted.
- `format_old_receipt`: nothing calls it. The 1.2.0 changelog says receipts moved to the billing service.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`. `handle_chargeback` and `handle_refund` have no direct Python caller, but `events/dispatch.py` looks them up by name (`"handle_" + kind`) for the kinds listed in `config/routes.ini`, so they are live. `handle_payout` is also imported by `payouts/batch.py`. I also kept `CHARGEBACK_FEE`, which `handle_chargeback` uses.

I didn't run the tests. A grep found no remaining references to the two removed functions in code, tests or config. They are still mentioned in `CHANGELOG.md`, which I left as history.
