I removed `handle_refund_v1` and `format_old_receipt` from `events/handlers.py`. Nothing calls either of them, and the `refund_v1` kind is no longer accepted; their only other mentions are release notes in CHANGELOG.md, which I left alone.

I kept `handle_chargeback`, although nothing names it outside its own definition and the changelog. `events/dispatch.py` builds the handler's name at runtime, `getattr(handlers, "handle_" + kind)`, for every kind that `config/routes.ini` switches on, and `chargeback = on` is listed there. The comment at the top of `routes.ini` says each listed kind is served by `handle_<kind>` and that removing one breaks that kind, so deleting it would have broken every chargeback. `handle_refund` and `handle_payout` are reached the same way.

The tests pass. None of them dispatches a chargeback through the real routes file, so a test for that route would catch this next time.
