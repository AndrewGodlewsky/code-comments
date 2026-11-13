I folded docs/refunds.md into the code. Every claim on the page has a fate below. The page is slimmed, not deleted, because three claims have no code home and must stay in a document.

Fate list, in page order:

1. "`needs_second_approver(amount)` is true for refunds of 500 EUR or more." Split in two:
   - The 500 threshold and the "or more" boundary: **dropped**. `refunds/approval.py` `needs_second_approver()` uses `amount >= SECOND_APPROVER_THRESHOLD`, and that constant is `Decimal("500")`.
   - The EUR unit: **moved** to `refunds/approval.py` `SECOND_APPROVER_THRESHOLD`. The code does not show a currency. Please confirm that amounts are EUR, since this comes only from the page.
2. "The 500 EUR threshold is the finance controller's four-eyes rule (decision PAY-31). Do not raise it without finance's sign-off." **Moved** to the comment on `refunds/approval.py` `SECOND_APPROVER_THRESHOLD`. The rationale, the ticket id PAY-31, and the sign-off rule are kept.
3. "If `can_send()` stays false for more than a day because a second approver is missing, ask in #fin-ops; finance can approve the refund from the provider dashboard." **Kept** as written under `## refunds/approval.py`. It is an operational step. The code has no one-day timeout.
4. "`send_refund()` posts the refund to the payment provider and returns the provider's refund id." **Dropped.** `refunds/provider.py` `send_refund()` posts to `/v2/refunds` and returns `response["refund_id"]`.
5. "The provider refuses a second refund with the same idempotency key." **Moved** to a new docstring on `refunds/provider.py` `send_refund()`. This is an outside provider contract that the code relies on.
6. "`send_refund()` uses the refund's own id as the key, so a retried call never pays out twice." Split in two:
   - "uses the refund's own id as the key": **dropped**. `headers={"Idempotency-Key": refund["id"]}` states it. The test `tests/test_refunds.py` `test_returns_the_provider_id` also asserts it.
   - "so a retried call never pays out twice": **moved** to the same `send_refund()` docstring as the reason for the key.
7. "The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before then disappear." **Kept.** It describes another system that no code here relies on.
8. "The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team." **Kept.** It is a platform-team fact that no code here relies on.

Not migrated: none. Every claim agrees with the code.

Changes:
- `refunds/approval.py`: a three-line comment above `SECOND_APPROVER_THRESHOLD`.
- `refunds/provider.py`: a two-line docstring on `send_refund()`. It has no opening line that restates the code.
- `docs/refunds.md`: removed claims 1, 2, 4, 5 and 6. Kept claims 3, 7 and 8 under their headings, with no note of what was removed. The `# Refunds` title stays.
- README.md, docs/onboarding.md, tests/ and `refunds/__init__.py` are unchanged.

Other items:
- No other file in this repository links to docs/refunds.md or to a removed section.
- No other file states a moved fact. `tests/test_refunds.py` asserts the 500 threshold and the Idempotency-Key value, but it is code, so I left it alone.
- Gaps: the currency unit (EUR), and whether the provider's idempotency behaviour still holds. Both come from the page and are outside this repository.
- Before you delete the page: claims 3, 7 and 8 still need a home. Options are a document outside the code, or your decision to drop them. The page is kept with those three claims, so it is not deleted.
