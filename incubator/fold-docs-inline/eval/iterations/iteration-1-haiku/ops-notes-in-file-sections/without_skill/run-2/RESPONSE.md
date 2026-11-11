I moved the refund notes from docs/refunds.md into the code they describe. Behaviour is unchanged; only comments and docstrings were added.

- `refunds/approval.py`
  - The 500 EUR second-approver threshold now carries the PAY-31 four-eyes note and the "do not raise without finance's sign-off" rule.
  - `can_send()` docstring now has the #fin-ops escalation for approvals stuck for more than a day, including that finance can approve from the provider dashboard.
- `refunds/provider.py`
  - Module docstring now records the sandbox wipe (every Monday 06:00 UTC).
  - `send_refund()` docstring now explains the idempotency key (the refund id), so retries never pay out twice, and the 90-day API key rotation by the platform team.

Nothing else changed. `docs/onboarding.md` is not about refunds, so I left it alone. Nothing in README.md or onboarding.md links to `docs/refunds.md`, so removing it breaks no links. I did not delete `docs/refunds.md`; say the word and I will.

The unit tests still pass and both edited modules compile.
