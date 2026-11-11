I moved the contents of docs/refunds.md into the code it describes and deleted that file.

- refunds/approval.py
  - Above `SECOND_APPROVER_THRESHOLD`: the 500 EUR second-approver rule, that it is the finance controller's four-eyes rule (PAY-31), and that it must not be raised without finance's sign-off.
  - In the `can_send()` docstring: the #fin-ops escalation when approval stays missing for more than a day, and that finance can approve from the provider dashboard.
- refunds/provider.py
  - In the `send_refund()` docstring: that it returns the provider's refund id, that the refund's own id is the idempotency key so a retry never pays out twice, that the provider sandbox is wiped Mondays at 06:00 UTC, and that the API keys behind the session are rotated every 90 days by the platform team.

No code behaviour changed. The unit tests pass (3 of 3).

I left docs/onboarding.md in place. It covers getting a provider dashboard login, which is not about any file in the refunds code, so it has no code section to move into. It will need a home or a deletion decision when the docs folder is cut down.

I also deleted docs/refunds.md on the assumption that "is going" means it should be removed once its content is moved. If you want it kept until the next cut, restore it from version control.
