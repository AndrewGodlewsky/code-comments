I went through every claim in docs/refunds.md and gave each one a fate. The page is not deleted yet: three claims have no home in the code, so they stay in the page.

Fate list, in page order:

1. "`needs_second_approver(amount)` is true for refunds of 500 EUR or more." Dropped. `refunds/approval.py` `needs_second_approver` returns `amount >= SECOND_APPROVER_THRESHOLD` (Decimal "500"), and `tests/test_refunds.py` asserts 500 is true and 499.99 is false. The EUR currency is not stated anywhere in the code (gap, see below).
2. "The 500 EUR threshold is the finance controller's four-eyes rule (decision PAY-31). Do not raise it without finance's sign-off." Moved to `refunds/approval.py`, above `SECOND_APPROVER_THRESHOLD`. The comment gives the reason, the PAY-31 id and the sign-off constraint. "EUR" was left out because the code does not show it.
3. "If `can_send()` stays false for more than a day because a second approver is missing, ask in #fin-ops; finance can approve the refund from the provider dashboard." Kept as written. This is an operational step. `can_send` does return false when fewer than two distinct approvers are present, but the code has no timing and no Slack or dashboard reference.
4. "`send_refund()` posts the refund to the payment provider and returns the provider's refund id." Dropped. `refunds/provider.py` `send_refund` posts to "/v2/refunds" and returns `response["refund_id"]`.
5. "The provider refuses a second refund with the same idempotency key." Moved to `refunds/provider.py` `send_refund`, above the `session.post` call. It is an outside provider contract that the retry safety depends on. It cannot be checked against this repo.
6. "`send_refund()` uses the refund's own id as the key" Dropped. The header `"Idempotency-Key": refund["id"]` states it, and `test_returns_the_provider_id` asserts it.
7. "so a retried call never pays out twice." Moved to the same comment in `refunds/provider.py`, together with the instruction to keep the key stable.
8. "The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before then disappear." Kept as written. It is a fact about another system, and no code here relies on it. The tests use a fake `Session`.
9. "The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team." Kept as written. `send_refund` takes `session` as a parameter and does not manage keys. The 90-day rotation cannot be checked here.

Not migrated: none. No claim is contradicted by the code.

Changes:
- `refunds/approval.py`: 3-line comment above `SECOND_APPROVER_THRESHOLD`.
- `refunds/provider.py`: 2-line comment above `response = session.post(` in `send_refund`.
- `docs/refunds.md`: claims 1, 2, 4, 5, 6 and 7 removed. Claims 3, 8 and 9 kept as written. Headings kept because each still has content.
- `docs/refunds.md` was not deleted. Deletion is allowed only when no kept claim remains, and three remain. Before you delete it, give the #fin-ops approval step, the sandbox wipe schedule and the key rotation a home (for example a runbook or the platform team's docs).
- No other file was changed. Tests pass (`python -m unittest tests.test_refunds`, 3 tests OK).

Other files:
- README.md and docs/onboarding.md do not link to docs/refunds.md.
- No file in the repo states a moved fact in a second place. There is no AGENTS.md or CLAUDE.md in this repo.

Gaps for you to fill:
- Currency: the code never says EUR. Confirm that the threshold is in EUR, and add it to the comment if you want it recorded.
- PAY-31: the decision record is not in this repo. Confirm the id is correct.
- Provider idempotency behaviour: confirm that the provider refuses duplicate keys, since the retry guarantee depends on it.
- Kept claims 3, 8 and 9 need a home before the page can be deleted.
