I removed two functions from events/handlers.py: `handle_refund_v1` and `format_old_receipt`. Nothing else changed.

**Why those two are dead.** I grepped every file in the repo. Neither name appears anywhere except the CHANGELOG. 1.3.0 says `handle_refund_v1` was replaced and the `refund_v1` kind is no longer accepted. 1.2.0 says `format_old_receipt` is no longer used here. `config/routes.ini` doesn't list a `refund_v1` kind.

**What I kept.** `handle_refund` and `handle_chargeback` look unused in Python, but `config/routes.ini` says `events/dispatch.py` finds `handle_<kind>` by name at runtime (`getattr(handlers, "handle_" + kind)`). Removing either would break every event of that kind, so both stay. `handle_payout` is imported by `payouts/batch.py`, and `CHARGEBACK_FEE` is used by `handle_chargeback`, so both stay too.

**Check.** The existing tests pass.
