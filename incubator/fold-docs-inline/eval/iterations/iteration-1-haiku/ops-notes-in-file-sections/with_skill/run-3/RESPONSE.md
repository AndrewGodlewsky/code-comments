I folded docs/refunds.md into the code and slimmed the page. I did not delete it, because four claims have no home in the code.

Fate list, in page order:

1. "`needs_second_approver(amount)` is true for refunds of 500 EUR or more." Split. The 500 threshold and the `>=` test are dropped: `refunds/approval.py` has `SECOND_APPROVER_THRESHOLD = Decimal("500")` and `needs_second_approver` returns `amount >= SECOND_APPROVER_THRESHOLD`. The EUR unit is kept, because the code has no currency. The bullet stays on the page as written, since its number and unit share one sentence.
2. "The 500 EUR threshold is the finance controller's four-eyes rule (decision PAY-31)." Moved to `refunds/approval.py`, comment above `SECOND_APPROVER_THRESHOLD`, with the ticket id PAY-31.
3. "Do not raise it without finance's sign-off." Moved to the same comment.
4. "If `can_send()` stays false for more than a day ... ask in #fin-ops; finance can approve the refund from the provider dashboard." Kept as written. It is an operational step. `can_send` in `refunds/approval.py` does return false while approvers are missing. The code here cannot show that a dashboard approval updates `approvers`.
5. "`send_refund()` posts the refund to the payment provider and returns the provider's refund id." Dropped. `refunds/provider.py` posts to `/v2/refunds` and returns `response["refund_id"]`.
6. "The provider refuses a second refund with the same idempotency key." Moved to the `send_refund` docstring, as an outside contract the code relies on. The provider's key retention window is not stated anywhere, so it is a gap.
7. "`send_refund()` uses the refund's own id as the key, so a retried call never pays out twice." Split. The key itself is dropped: `headers={"Idempotency-Key": refund["id"]}`. The reason is moved to the same docstring, together with claim 6.
8. "The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before then disappear." Kept as written. No code here calls the sandbox. The tests use a fake `Session`.
9. "The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team." Kept as written. The code here does not create the session or hold keys, so the phrase "behind `send_refund()`'s session" cannot be checked here. It is a gap.

Not migrated: none.

Other files: no file links to docs/refunds.md. No other file states a moved fact. README.md and docs/onboarding.md are unrelated to these claims.

Changed files:
- refunds/approval.py: comment above `SECOND_APPROVER_THRESHOLD`.
- refunds/provider.py: docstring on `send_refund`.
- docs/refunds.md: now holds only kept claims 1, 4, 8 and 9.

Gaps to fill:
- Confirm the EUR unit. Only the page states it.
- Confirm that dashboard approval sets `approvers` for `can_send`.
- Confirm the provider's idempotency key retention window.
- Confirm where the session and its keys come from.

Decision for you: the page is not deleted. Its four kept claims are operational or outside facts, so they need a new home, such as a runbook, before the page can go. The threshold line duplicates the code except for the currency.
