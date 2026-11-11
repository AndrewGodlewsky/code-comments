I slimmed docs/refunds.md rather than deleting it, because it still holds operational claims with no code to sit beside. Two comments were added; the tests pass.

Fate list, in page order:

1. `needs_second_approver(amount)` is true for refunds of 500 EUR or more. **Dropped.** `refunds/approval.py` `needs_second_approver` and `SECOND_APPROVER_THRESHOLD = Decimal("500")` state it, and `tests/test_refunds.py` checks 500 and 499.99. The code has no currency, so "EUR" is not stated anywhere in the code.
2. The 500 EUR threshold is the finance controller's four-eyes rule (PAY-31); do not raise it without finance's sign-off. **Moved** to a comment on `SECOND_APPROVER_THRESHOLD` in `refunds/approval.py`. I left out the number and the currency, since the constant already shows 500.
3. If `can_send()` stays false for over a day for lack of a second approver, ask in #fin-ops; finance can approve from the provider dashboard. **Kept.** It is an operational step, and `can_send` exists in `refunds/approval.py` and agrees with it.
4. `send_refund()` posts the refund to the provider and returns the provider's refund id. **Dropped.** `refunds/provider.py` `send_refund` posts to `/v2/refunds` and returns `response["refund_id"]`, and `test_returns_the_provider_id` covers it.
5. The provider refuses a second refund with the same idempotency key; `send_refund()` uses the refund's own id as the key, so a retry never pays out twice. **Moved** to a comment at the top of `send_refund` in `refunds/provider.py`. The code sets `Idempotency-Key` to `refund["id"]`, so it agrees. The provider's refusal behaviour is outside this repository and can't be checked here.
6. The provider's sandbox is wiped every Monday at 06:00 UTC. **Kept.** It is a fact about another system that no code here relies on. It can't be checked here, so it is a gap.
7. API keys behind `send_refund()`'s session are rotated every 90 days by the platform team. **Kept.** It is a fact about another system, and the session is created outside this repository. It can't be checked here, so it is a gap.

Other files that state a moved fact: none. README.md and docs/onboarding.md do not mention the threshold or idempotency.

Files linking to docs/refunds.md or a removed section: none found.

Gaps for you to fill: claims 5, 6 and 7 are about the provider and the platform team, and I could not verify them against this code. The page still holds claims 3, 6 and 7. No code, tests or other files were changed.
