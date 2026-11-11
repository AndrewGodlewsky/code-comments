I moved everything from docs/refunds.md into comments next to the code it describes, then deleted docs/refunds.md. The test suite still passes (3 tests).

What went where:

- refunds/approval.py, above SECOND_APPROVER_THRESHOLD: the 500 EUR second-approver rule, the four-eyes decision reference (PAY-31), and the instruction not to change the threshold without finance's sign-off.
- refunds/approval.py, docstring of can_send(): the one-day rule. If it stays false for more than a day because a second approver is missing, ask in #fin-ops, and finance can approve from the provider dashboard.
- refunds/provider.py, docstring of send_refund(): what it returns, the idempotency behaviour (the refund's own id is the key, so retries never pay out twice), the 90-day API key rotation by the platform team, and the Monday 06:00 UTC sandbox wipe.

Judgement calls to check:

- The key-rotation note is about the session that callers pass in, and that session is created outside this repo. I put it on send_refund() because that is the only code here that uses it. If you would rather keep it out of the code, it belongs in the platform team's runbook.
- The sandbox wipe is a fact about the provider's test environment, so I put it on send_refund() as well. It is the call that hits that sandbox.

Left alone:

- docs/onboarding.md is not about refunds (it covers getting a provider dashboard login), so it stays. It has no link to refunds.md.
- README.md has no link to refunds.md, so nothing needed updating.

No other file referenced docs/refunds.md. I did not use git or any task tracking.
