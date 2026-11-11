I moved the facts that belong to the code into comments and removed `docs/refunds.md`. I haven't run the tests.

**Now in the code**
- `refunds/approval.py`: a comment on `SECOND_APPROVER_THRESHOLD` says the 500 EUR limit is the finance controller's four-eyes rule (PAY-31) and needs finance's sign-off to raise. `needs_second_approver` also has a one-line docstring about the 500 EUR threshold.
- `refunds/provider.py`: `send_refund` has a docstring saying it returns the provider's refund id. A comment in the function says the provider refuses a repeated idempotency key, so keying on the refund id means a retry never pays out twice.

**Not code facts, so I moved them to `docs/onboarding.md`** under a new "Refund operations" section:
- Escalate to #fin-ops if `can_send()` stays false for more than a day.
- The provider sandbox is wiped every Monday at 06:00 UTC.
- The API keys are rotated every 90 days by the platform team.

If you'd rather not keep those three notes at all, delete that section. If you'd rather they live somewhere else, say where.
