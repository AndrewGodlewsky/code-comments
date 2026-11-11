I deleted docs/refunds.md and moved its content as follows.

Into code comments:
- `refunds/approval.py`: a comment on `SECOND_APPROVER_THRESHOLD` giving the finance controller's four-eyes rule (PAY-31) and the requirement for finance sign-off before raising it.
- `refunds/provider.py`: a comment on the `Idempotency-Key` header explaining that the provider refuses a repeated key, so keying on the refund id makes retries safe.

Into README.md (new "Operations" section), because they are not about any one piece of code:
- Ask in #fin-ops if a refund is stuck for more than a day without a second approver.
- The sandbox wipe, Mondays 06:00 UTC.
- The 90-day API key rotation by the platform team.

I dropped the description of `needs_second_approver` and `send_refund` because the code and tests already say it. Nothing else referred to docs/refunds.md. If you'd rather these three operational notes live in docs/onboarding.md or elsewhere, say so.
