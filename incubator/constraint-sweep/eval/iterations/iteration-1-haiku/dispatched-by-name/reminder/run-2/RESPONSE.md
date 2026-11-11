I removed two functions from events/handlers.py that nothing calls any more:

- `handle_refund_v1`. The `refund_v1` kind was retired in 1.3.0 (CHANGELOG.md says "the refund_v1 kind is no longer accepted"). It is not in config/routes.ini, so dispatch.py can never reach it.
- `format_old_receipt`. Receipts moved to the billing service in 1.2.0 (CHANGELOG.md says it "is no longer used here"). Nothing in the repo references it.

Constraints I checked before removing them:

- Grep across every file in the repo found no callers for either name outside their definitions. The only other mentions are the CHANGELOG entries above.
- config/routes.ini says handlers are looked up by name at runtime, so a handler with no Python caller can still be live. For `handle_refund_v1` the routes file settles it: `refund_v1` is not a listed kind, so the lookup never happens.
- The tests do not reference either function.

Kept on purpose:

- `handle_refund`, `handle_chargeback`, `handle_payout` and `CHARGEBACK_FEE`. They are reached through dispatch (refund, chargeback, payout) or imported by payouts/batch.py and tests. Nothing about their return values, ordering or arguments changed.

Verification: `python -m unittest discover -s tests -t .` in the repo passes (5 tests).

I did not change CHANGELOG.md, README.md or any other file. If you want the removals recorded, an "Unreleased" entry in CHANGELOG.md would be the place for it.
