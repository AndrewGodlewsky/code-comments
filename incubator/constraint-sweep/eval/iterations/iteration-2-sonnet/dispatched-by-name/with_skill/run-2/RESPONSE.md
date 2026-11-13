I removed two functions from `events/handlers.py`: `handle_refund_v1` and `format_old_receipt`. Nothing calls either one. I did not run the tests.

- `handle_refund_v1` has no importer, no test, and no `refund_v1` entry in `config/routes.ini`. `events/dispatch.py` only reaches handlers by `"handle_" + kind` for kinds switched on there, so this one is unreachable. `CHANGELOG.md:7` says the same: the `refund_v1` kind is no longer accepted.
- `format_old_receipt` has no caller anywhere. `CHANGELOG.md:10` says receipts moved to the billing service.

I kept `handle_chargeback` and `handle_refund`, even though nothing imports `handle_chargeback`. `config/routes.ini:2-4` says `events/dispatch.py` looks handlers up by name at runtime, and `chargeback = on` is set there, so removing it would break every chargeback event. `handle_payout` is imported by `payouts/batch.py:2`. `CHARGEBACK_FEE` is used by `handle_chargeback`.

I found no stale constraints. The `CHANGELOG.md` lines only describe the removals and are still accurate, so I left them.
