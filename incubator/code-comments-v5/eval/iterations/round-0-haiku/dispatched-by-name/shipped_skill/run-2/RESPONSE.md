I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. Nothing calls it. Dispatch reaches handlers only by the name `handle_<kind>`, and `refund_v1` is not in `config/routes.ini`. CHANGELOG 1.3.0 says the `refund_v1` kind is no longer accepted.
- `format_old_receipt`. Nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service.

I kept everything else. `handle_refund`, `handle_chargeback` and `handle_payout` are live: the first two are reached through dispatch by kind, and `handle_payout` is called by `payouts/batch.py`. `CHARGEBACK_FEE` and the `pence` import are still used.

The module's docstring, the comment in `config/routes.ini` and the README entry for `events/handlers.py` are still accurate, so I left them alone. I did not touch CHANGELOG.md; its history entries still describe the removed names, which is expected for release notes.

The test suite passes (5 tests). I did not use git, so nothing is committed.
