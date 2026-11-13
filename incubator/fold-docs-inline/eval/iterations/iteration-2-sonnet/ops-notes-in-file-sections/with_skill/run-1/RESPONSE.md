I folded what belongs beside the code into comments and slimmed docs/refunds.md. The page is not deleted, because it still holds operational and outside-system notes with no code to sit beside.

Fate list, in page order:
- `needs_second_approver(amount)` is true for 500 EUR or more: dropped. `needs_second_approver` and `SECOND_APPROVER_THRESHOLD = Decimal("500")` in refunds/approval.py say it, and `test_large_refunds_need_two_people` covers 500 and 499.99.
- The 500 EUR threshold is the finance controller's four-eyes rule (PAY-31): moved to a comment on `SECOND_APPROVER_THRESHOLD` in refunds/approval.py.
- Do not raise it without finance's sign-off: moved, same comment.
- If `can_send()` stays false for more than a day because a second approver is missing, ask in #fin-ops; finance can approve from the provider dashboard: kept. It is an operational step. It names `can_send()`, which exists and behaves as described (refunds/approval.py).
- `send_refund()` posts the refund to the provider and returns the provider's refund id: dropped. `send_refund` in refunds/provider.py does exactly this.
- The provider refuses a second refund with the same idempotency key: moved, as a comment above the `Idempotency-Key` header in `send_refund` (refunds/provider.py). It is an outside contract the code relies on.
- `send_refund()` uses the refund's own id as the key, so a retry never pays out twice: moved, same comment. The code does use `refund["id"]`, and a test checks it.
- The sandbox is wiped every Monday at 06:00 UTC: kept. It is a fact about another system, and no code here relies on it.
- API keys behind `send_refund()`'s session are rotated every 90 days by the platform team: kept. It is a fact about another system, and no code here relies on it.

Nothing was not migrated, because no claim contradicts the code.

Other files that state moved facts: none found. README.md and docs/onboarding.md say nothing about them.
Files linking to docs/refunds.md or a removed section: none.
Gaps: none. The kept items rest on facts about outside systems (Slack channel, sandbox schedule, key rotation) that I could not check against this repository.

docs/refunds.md now holds only the kept claims: the #fin-ops step under refunds/approval.py, and the sandbox and key-rotation notes under refunds/provider.py. Code, tests and other docs are unchanged.
