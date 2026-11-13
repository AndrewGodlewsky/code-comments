I moved the two claims that belong beside the code into comments and removed them from `docs/refunds.md`, along with the two claims the code already states. I kept `docs/refunds.md` because four operational claims remain on it. I did not run the tests; the edits are comments only.

Fate list, in page order:

**refunds/approval.py**
1. `needs_second_approver(amount)` is true for refunds of 500 EUR or more. Dropped. The function and `SECOND_APPROVER_THRESHOLD = Decimal("500")` state it, and `test_large_refunds_need_two_people` checks 500 and 499.99.
2. The 500 EUR threshold is the finance controller's four-eyes rule (PAY-31). Moved to a comment on `SECOND_APPROVER_THRESHOLD` in `refunds/approval.py`.
3. Do not raise the threshold without finance's sign-off. Moved to the same comment.
4. If `can_send()` stays false for more than a day because a second approver is missing, ask in #fin-ops. Kept. This is an operational step.
5. Finance can approve the refund from the provider dashboard. Kept. This is an operational step and a fact about another system.

**refunds/provider.py**
6. `send_refund()` posts the refund to the provider and returns the provider's refund id. Dropped. The code and `test_returns_the_provider_id` state it.
7. The provider refuses a second refund with the same idempotency key. Moved to a comment in `send_refund` in `refunds/provider.py`. This is an outside contract the code relies on.
8. `send_refund()` uses the refund's own id as the key, so a retried call never pays out twice. Moved to the same comment. The code shows the key (`refund["id"]`), but not why it is that value.
9. The provider's sandbox is wiped every Monday at 06:00 UTC. Kept. It is a fact about another system that no code here relies on. It is also not checkable against this repository, so it is a gap.
10. The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team. Kept. Same reason as 9, and the session is built outside this repository.

Nothing was not migrated. The page and the code agree everywhere.

Other files:
- No other file states a moved fact. `README.md` and `docs/onboarding.md` do not mention the threshold or the idempotency key.
- No file links to `docs/refunds.md`.
- The page does not state the 500 EUR currency, and the code has no currency, so "EUR" is not in the comment. Add it there if you want it.

`docs/refunds.md` now holds only claims 4, 5, 9 and 10, so I did not delete it. The #fin-ops and dashboard steps and the sandbox and key-rotation facts have no code to sit beside. If you still want the page gone, they need another home, for example a runbook. Tell me where and I will move them.
