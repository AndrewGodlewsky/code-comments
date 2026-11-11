I folded docs/refunds.md into the code and slimmed the page. It is not deleted, because three claims are kept.

Fate list (page order):

1. `needs_second_approver(amount)` is true for refunds of 500 or more. Dropped. refunds/approval.py `needs_second_approver` and `SECOND_APPROVER_THRESHOLD` already state it.
2. "500 EUR": the EUR unit. Moved. refunds/approval.py, comment above `SECOND_APPROVER_THRESHOLD`. The code has no currency, so please confirm EUR.
3. "The 500 threshold is the finance controller's four-eyes rule (decision PAY-31)." Moved. Same comment, PAY-31 kept.
4. "Do not raise it without finance's sign-off." Moved. Same comment.
5. "If `can_send()` stays false for more than a day ... ask in #fin-ops; finance can approve from the provider dashboard." Kept as written. It is an operational step. `can_send` in refunds/approval.py agrees with it.
6. `send_refund()` posts the refund and returns the provider's refund id. Dropped. refunds/provider.py `send_refund` and tests/test_refunds.py `test_returns_the_provider_id` state it.
7. "The provider refuses a second refund with the same idempotency key." Moved. refunds/provider.py, comment above `send_refund`. This is an outside provider contract the code relies on. The repo cannot verify it.
8. "`send_refund()` uses the refund's own id as the key, so a retried call never pays out twice." The key part is dropped, since refunds/provider.py sets `Idempotency-Key` to `refund["id"]`. The reason part is moved to the same comment above `send_refund`.
9. "The provider's sandbox is wiped every Monday at 06:00 UTC." Kept as written. It is a fact about another system that no code here relies on.
10. "The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team." Kept as written. No code here creates or rotates the session, so this is a gap.

Other files that state a moved fact: none. README.md, docs/onboarding.md and the tests do not repeat the threshold or the idempotency reasoning. No file links to docs/refunds.md or to the removed sections.

Gaps for you to fill:
- Confirm the EUR unit (claim 2).
- Confirm the provider's idempotency behaviour (claim 7). It is recorded in code comments only and is not checked by any test here.
- Decide where the kept claims (5, 9, 10) should go, since the page still exists. Claim 10 is about session setup outside this repo.
- Decide whether to delete docs/refunds.md once those three claims are moved or dropped. I did not delete it, because kept claims remain.

Changed files: refunds/approval.py and refunds/provider.py (comments only), docs/refunds.md (slimmed to the three kept claims), and this RESPONSE.md. No code or other files changed.
