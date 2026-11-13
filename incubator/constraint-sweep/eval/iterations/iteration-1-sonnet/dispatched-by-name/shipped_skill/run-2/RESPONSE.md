I removed two functions from `events/handlers.py` and left the rest alone.

**Removed**
- `handle_refund_v1`: nothing calls it. `CHANGELOG.md` 1.3.0 says `handle_refund` replaced it and that the `refund_v1` kind is no longer accepted. `config/routes.ini` doesn't list that kind either.
- `format_old_receipt`: nothing calls it. `CHANGELOG.md` 1.2.0 says receipts moved to the billing service.

**Kept**
- `handle_refund`, `handle_chargeback` and `handle_payout` look unused if you search for callers. They are live, though. `events/dispatch.py` finds them by name (`"handle_" + kind`), and `config/routes.ini` says removing or renaming one breaks every event of its kind. `handle_payout` is also imported by `payouts/batch.py`.

**Comments**
- The only comment that went was the one inside `handle_refund_v1`. The module docstring and the `CHARGEBACK_FEE` comment are still accurate, so I left them as they were.
- I didn't edit the `CHANGELOG.md` entries. They are release history, and they still read correctly after the removal.

The tests still pass (5 tests).
