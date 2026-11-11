I slimmed docs/refunds.md rather than deleting it, because three operational claims have no code to sit beside. Four claims moved into two comments, three were dropped, and nothing contradicted the code.

Fate list, in page order:

1. "`needs_second_approver(amount)` is true for refunds of 500 EUR or more." **Dropped.** `refunds/approval.py` `needs_second_approver` and `SECOND_APPROVER_THRESHOLD = Decimal("500")` state it, and `test_large_refunds_need_two_people` checks 500 and 499.99.
2. "The 500 EUR threshold is the finance controller's four-eyes rule (decision PAY-31)." **Moved** to a comment on `SECOND_APPROVER_THRESHOLD` in `refunds/approval.py`.
3. "Do not raise it without finance's sign-off." **Moved**, same comment.
4. "If `can_send()` stays false for more than a day... ask in #fin-ops; finance can approve from the provider dashboard." **Kept.** It is an operational step.
5. "`send_refund()` posts the refund to the payment provider and returns the provider's refund id." **Dropped.** The code in `refunds/provider.py` `send_refund` does this, and `test_returns_the_provider_id` checks it.
6. "The provider refuses a second refund with the same idempotency key." **Moved** to a comment in `send_refund` in `refunds/provider.py`. It is an outside contract the code relies on.
7. "`send_refund()` uses the refund's own id as the key." **Dropped** as a statement of what the code does: `headers={"Idempotency-Key": refund["id"]}`, which the test also checks. The reason is in the moved comment from claim 6.
8. "...so a retried call never pays out twice." **Moved**, in the same comment as claim 6.
9. "The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before then disappear." **Kept.** It is a fact about another system that no code here relies on.
10. "API keys behind `send_refund()`'s session are rotated every 90 days by the platform team." **Kept.** It is a fact about another system, and the code here does not show it. Nothing in this repository lets me check it, so it is a gap for you to confirm.

Not migrated: none.

Other files that state a moved fact:
- None. README.md and docs/onboarding.md do not mention the threshold or idempotency.

Files that link to the page:
- None found. README.md and docs/onboarding.md do not link to docs/refunds.md.

docs/refunds.md still exists because it holds the three kept claims above (4, 9 and 10). It is not deleted. If you want it gone, those operational notes need another home, such as a runbook.

Only docs/refunds.md and the comments in refunds/approval.py and refunds/provider.py changed. No code was touched.
