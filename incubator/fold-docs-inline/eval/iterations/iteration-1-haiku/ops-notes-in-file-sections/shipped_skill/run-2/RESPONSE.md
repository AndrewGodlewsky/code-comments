I moved the refund notes from docs/refunds.md into the files they describe. I left docs/refunds.md in place, since you may want to delete it yourself. Nothing else changed, and the tests still run.

What moved, and where:

- refunds/approval.py
  - The 500 EUR threshold now has a comment citing the finance controller's four-eyes rule (PAY-31) and saying not to raise it without finance's sign-off.
  - The can_send() docstring now says: if it stays False for more than a day because a second approver is missing, ask in #fin-ops, since finance can approve from the provider dashboard.
- refunds/provider.py
  - The send_refund() docstring now says the Idempotency-Key is the refund's id, so a retried call never pays out twice.
  - It also records that the API keys behind the session are rotated every 90 days by the platform team, and that the provider sandbox is wiped every Monday at 06:00 UTC, so test refunds made before then disappear.

Not moved:

- docs/onboarding.md is not about code, so I left it alone. It is still in the docs folder, so you may want to decide whether it goes too.

Please check:

- The threshold comment says "EUR" because docs/refunds.md says so. The code itself has no currency.
- The sandbox and key-rotation notes are facts about the provider environment, not something this code enforces. If they change, these comments will go stale.
