I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`: nothing calls it. `dispatch` only reaches a handler for a kind listed in `config/routes.ini`, and `refund_v1` is not listed. CHANGELOG 1.3.0 says the kind is no longer accepted.
- `format_old_receipt`: nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

Kept, because something reaches them:

- `handle_refund`, `handle_chargeback`: named in `config/routes.ini` and looked up by `getattr` in `events/dispatch.py`. The routes file comment says the same.
- `handle_payout`: imported by `payouts/batch.py`.
- `CHARGEBACK_FEE` and `pence` use: used by the kept handlers.

Checks: the sweep searched the whole repository, hidden files included, for each removed name and for the `handle_` lookup pattern. The only remaining hits are the two CHANGELOG entries, which are history and so are left as they are. `python -m unittest discover -s tests -t .` passes (5 tests). Nothing was committed.
