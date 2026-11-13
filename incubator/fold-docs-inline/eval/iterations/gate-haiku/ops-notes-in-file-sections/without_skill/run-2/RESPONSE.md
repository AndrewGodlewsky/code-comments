I moved the refund notes from docs/refunds.md into the code they describe, then deleted docs/refunds.md.

- refunds/approval.py: the 500 EUR second-approver threshold now has a comment with the four-eyes rule reference (PAY-31) and the rule not to raise it without finance sign-off. The `can_send()` docstring now carries the ops escalation: if it stays False for more than a day because a second approver is missing, ask in #fin-ops, and finance can approve from the provider dashboard.
- refunds/provider.py: the `send_refund()` docstring now explains what it does and returns, and that the refund id is the Idempotency-Key so retries never pay out twice. It also has two ops notes: the session's API keys are rotated every 90 days by the platform team, and the provider sandbox is wiped every Monday at 06:00 UTC, so test refunds made before then disappear.

I left docs/onboarding.md in place. It covers getting a provider dashboard login and is not about the refunds code, so it does not belong in a code comment. README.md did not reference docs/refunds.md, so it is unchanged. No code behaviour changed; the existing three unit tests pass.
