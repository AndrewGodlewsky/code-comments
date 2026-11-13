I deleted docs/refunds.md and moved its content as follows.

Into code comments:
- refunds/approval.py: the 500 EUR threshold is the finance controller's four-eyes rule (PAY-31), not to be raised without finance sign-off. This is now a comment on `SECOND_APPROVER_THRESHOLD`.
- refunds/provider.py: `send_refund()` now has a docstring saying it returns the provider's refund id. A comment next to the header explains that the refund id is the idempotency key, so retries never pay out twice.

Dropped: the line saying `needs_second_approver` is true at 500 EUR or more. The code already says so.

Moved to README.md under a new "Operations" heading, not into code comments:
- the #fin-ops escalation when a second approver is missing for over a day
- the Monday 06:00 UTC sandbox wipe
- the 90-day API key rotation by the platform team

These are runbook facts about people and the environment, not about the code, and they would go stale inside source files. If you would rather lose them or put them elsewhere, such as docs/onboarding.md, it is a small change.

I did not run the tests.
