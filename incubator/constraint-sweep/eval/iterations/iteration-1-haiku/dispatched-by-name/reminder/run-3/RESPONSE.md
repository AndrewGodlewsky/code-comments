I removed two dead functions from `events/handlers.py`: `handle_refund_v1` and `format_old_receipt`. Nothing else in the repository calls them.

Removed:
- `handle_refund_v1`: no callers. `config/routes.ini` does not list `refund_v1`, and CHANGELOG 1.3.0 says that kind is no longer accepted. Its only comment ("Refunds before 1.3 were booked against cash only") is historical and now lives in the changelog.
- `format_old_receipt`: no callers. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

Kept, and why:
- `handle_refund`, `handle_chargeback`, `handle_payout`: live. `dispatch.py` looks up `handle_<kind>` by name for each kind switched on in `config/routes.ini`, so they have no direct Python caller. `payouts/batch.py` also calls `handle_payout`. `routes.ini` warns that removing or renaming one of these breaks every event of that kind.
- `CHARGEBACK_FEE`: used by `handle_chargeback`. CHANGELOG 1.1.0 records that the fee is booked.

Constraints checked: I grepped the whole repository, all file types, for the changed names and for `chargeback`, `receipt` and `handlers`. The only remaining references are in `CHANGELOG.md`, which I left unchanged. No test referenced either removed function. `python -m unittest discover -s tests -t .` passes (5 tests).

One behaviour change to know about: if someone switched `refund_v1` on in `routes.ini`, dispatch would now raise `AttributeError` instead of posting. That kind is already documented as not accepted, so I judged this acceptable, but it is the only path that changed.
