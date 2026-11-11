I moved the content of docs/refunds.md into comments in the files it describes. I left docs/refunds.md in place, so you can delete it when you're ready. I left docs/onboarding.md and README.md unchanged because they don't describe the refund code.

Where each note went:

- **refunds/approval.py**
  - Above `SECOND_APPROVER_THRESHOLD`: the 500 EUR threshold, its source (finance controller's four-eyes rule, PAY-31), and the rule not to raise it without finance's sign-off.
  - In the `can_send()` docstring: a refund that needs a second approver but has only one stays unsendable; if that lasts over a day, ask in #fin-ops, since finance can approve it from the provider dashboard.
- **refunds/provider.py**
  - In the `send_refund()` docstring: the session's API keys are rotated every 90 days by the platform team, and the provider sandbox is wiped every Monday at 06:00 UTC, so test refunds made before then disappear.
  - Beside the `Idempotency-Key` header: the refund's id is the key, so a retried call never pays out twice.

Notes for you:

- The PAY-31 id and the EUR currency come from docs/refunds.md. I did not check them against the ticket or the code, since the code has no currency field.
- The #fin-ops and #it-help channel names and the sandbox schedule may go stale. Check them before you rely on them.
- The 500 EUR threshold is a finance decision. Nothing in the code or tests records a reason beyond the PAY-31 pointer.

Verification: `python -m unittest` runs 3 tests, all passing, and both edited modules compile. I made no git commits.
