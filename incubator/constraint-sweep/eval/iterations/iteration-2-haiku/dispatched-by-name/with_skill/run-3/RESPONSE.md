I removed two dead functions from `events/handlers.py`:

- `handle_refund_v1`: nothing calls it. `dispatch` only reaches `handle_<kind>` for kinds switched on in `config/routes.ini`, and `refund_v1` is not listed there. CHANGELOG 1.3.0 says that kind is no longer accepted.
- `format_old_receipt`: nothing calls it. CHANGELOG 1.2.0 says it is no longer used here.

I kept `CHARGEBACK_FEE`, `handle_refund`, `handle_chargeback` and `handle_payout`. `handle_refund` and `handle_chargeback` are reached through the runtime lookup in `events/dispatch.py`, and `config/routes.ini` (lines 2-4) says those handlers have no direct Python caller and must not be removed or renamed. `handle_payout` is imported by `payouts/batch.py`.

Constraint sweep: `config/routes.ini` is the only file that states a constraint about these handlers, and it covers only the kinds listed there, so it does not apply to the two removed functions. No stale text needed correcting. The CHANGELOG entries that mention the removed functions are historical and still accurate, so I left them alone.

One behaviour change: if a caller passed `kinds={"refund_v1"}` to `dispatch` directly, it would now fail with an AttributeError instead of posting entries. The normal path (kinds loaded from `config/routes.ini`) already rejects `refund_v1` with a KeyError, so no event flow changes.

Tests: `python -m unittest discover -s tests -t .` runs 5 tests, all passing.
