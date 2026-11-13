I removed `handle_refund_v1` and `format_old_receipt` from `events/handlers.py`. I did not run the tests.

Both had no callers. Nothing imports them, no test uses them, `config/routes.ini` has no `refund_v1` kind, and nothing else refers to either name. The only mentions are in `CHANGELOG.md` lines 7 and 10, which already describe them as replaced and no longer used.

I kept `handle_refund`, `handle_chargeback` and `handle_payout`, even though `handle_chargeback` has no direct caller. `events/dispatch.py:23` looks handlers up by name with `getattr(handlers, "handle_" + kind)`, and `config/routes.ini:3-4` says removing one of these breaks events of its kind. `chargeback = on` is enabled there. `CHARGEBACK_FEE` is still used by `handle_chargeback`, so it stays too.
