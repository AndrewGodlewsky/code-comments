I removed two functions from `events/handlers.py`: `handle_refund_v1` and `format_old_receipt`. The tests pass (5 run).

- **`handle_refund_v1`**: it has no callers. The `refund_v1` kind is no longer accepted, and `config/routes.ini` doesn't list it. The CHANGELOG for 1.3.0 says `handle_refund` replaced it.
- **`format_old_receipt`**: it has no callers. The CHANGELOG for 1.2.0 says receipts moved to the billing service.

I left `handle_refund`, `handle_chargeback` and `handle_payout` alone. They look unused if you search for callers, but `events/dispatch.py` finds them by name at runtime (`"handle_" + kind`) for the kinds in `config/routes.ini`. `payouts/batch.py` also imports `handle_payout` directly. Removing any of them would break events of that kind.

No comments needed changing. The remaining ones in `handlers.py` and `routes.ini` are still accurate. The CHANGELOG entries mentioning the removed functions describe past releases, so I left them as they are.
