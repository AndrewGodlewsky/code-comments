I removed two dead functions from events/handlers.py: handle_refund_v1 and format_old_receipt. The module now holds CHARGEBACK_FEE, handle_refund, handle_chargeback and handle_payout.

- handle_refund_v1: nothing in the repo calls it. config/routes.ini lists only refund, chargeback and payout, so dispatch never looks it up under a refund_v1 kind. CHANGELOG 1.3.0 says the refund_v1 kind is no longer accepted.
- format_old_receipt: nothing calls it. CHANGELOG 1.2.0 says receipts moved to the billing service and this function is no longer used here.

Kept, because something reaches them:
- handle_refund: tests/test_handlers.py.
- handle_chargeback: looked up by name in events/dispatch.py for the kind "chargeback" in config/routes.ini.
- handle_payout: payouts/batch.py and the "payout" kind in config/routes.ini.
- CHARGEBACK_FEE: used by handle_chargeback.

Sweep: config/routes.ini has a comment saying handlers are looked up by name at runtime, so I searched for each handler name and the handle_ prefix across all files. The only mentions of the two removed functions are CHANGELOG.md lines 7 and 10. Those are release history and state no live constraint, so I left them alone. No stale constraints were found in the code I changed.

Verification: python -m unittest discover -s tests -t . ran 5 tests, all passing, and events/handlers.py parses.
