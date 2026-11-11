I moved the refund notes from docs/refunds.md into the files they describe and deleted docs/refunds.md. The unit tests still pass (3 tests, OK).

Where each note went:

- refunds/approval.py
  - Above SECOND_APPROVER_THRESHOLD: the 500 EUR two-approver rule, the PAY-31 four-eyes decision, and the instruction not to raise the threshold without finance's sign-off.
  - In the can_send() docstring: if it stays False for more than a day because a second approver is missing, ask in #fin-ops, and finance can approve from the provider dashboard.
- refunds/provider.py, in the send_refund() docstring
  - The refund id is the Idempotency-Key, so a retried call never pays out twice.
  - The API keys behind the session are rotated every 90 days by the platform team.
  - The provider sandbox is wiped every Monday at 06:00 UTC, so test refunds made before then disappear.

Not moved:

- docs/onboarding.md is not about the refund code, so I left it alone. It is still the only file left in docs/, so you may want to move or delete it as part of the cut.
- The #it-help login note is in onboarding.md, not in refunds.md, so it was not touched.

Things to check:

- The sandbox wipe schedule and the 90-day key rotation are time-based facts that will go stale. The comments state them as current, so whoever owns them should update the comments when they change.
- The 500 EUR threshold is compared against a bare Decimal with no currency field. The comment says EUR because that is what the old doc said. Nothing in the code enforces that.
