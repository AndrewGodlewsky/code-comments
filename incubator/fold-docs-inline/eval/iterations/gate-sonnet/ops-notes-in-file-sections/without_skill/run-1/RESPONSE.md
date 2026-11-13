I removed docs/refunds.md and moved its content as follows.

In code comments:
- refunds/approval.py: the 500 EUR threshold is the finance controller's four-eyes rule (PAY-31) and needs finance's sign-off to raise. It is a comment on `SECOND_APPROVER_THRESHOLD`.
- refunds/provider.py: a docstring on `send_refund()` for what it does and returns, plus a comment that the refund id is the idempotency key, so a retry never pays out twice.

Not in code, in a new "Operations" section of README.md:
- The #fin-ops escalation when a second approver is missing for more than a day.
- The Monday 06:00 UTC sandbox wipe.
- The 90-day API key rotation by the platform team.

These are runbook facts about people and external systems, not about what the code does, so they would go stale in comments. If you would rather not keep them in the README, say so and I'll drop or relocate them. I did not touch docs/onboarding.md or the tests.
