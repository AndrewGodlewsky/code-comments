I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`. Nothing calls it. `config/routes.ini` does not switch on a `refund_v1` kind, so dispatch never reaches it. CHANGELOG 1.3.0 says the kind is no longer accepted.
- `format_old_receipt`. Nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

I kept these, which are live:

- `handle_refund`, `handle_chargeback` and `handle_payout`. Dispatch reaches the first two by name from `config/routes.ini`, and `payouts/batch.py` imports `handle_payout`.
- `CHARGEBACK_FEE`, used by `handle_chargeback`.
- The `pence` import, used by the live handlers.

I checked the rest of the repo for references to the removed names and found none outside the changelog. No other comments needed changes, since the removed code took its own comment with it and the CHANGELOG already records why. The unit tests pass (5 of 5).

If someone later switches on a `refund_v1` kind in `config/routes.ini`, dispatch will now fail with an AttributeError instead of posting. That needs a deliberate config change, so I did not add a guard.
