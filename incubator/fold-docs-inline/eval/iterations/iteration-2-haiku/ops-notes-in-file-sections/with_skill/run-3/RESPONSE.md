# docs/refunds.md: fate list

I moved the facts that belong beside the code into comments, and removed the claims that the code already states or that the code contradicts. Three claims stay in `docs/refunds.md` because nothing in the code can hold them, so the page is not deleted yet.

## Fate list (page order)

| # | Claim | Fate | Evidence |
|---|---|---|---|
| 1a | `needs_second_approver(amount)` is true for refunds of 500 or more | Dropped | `refunds/approval.py`: `needs_second_approver` returns `amount >= SECOND_APPROVER_THRESHOLD`, where the threshold is `Decimal("500")` |
| 1b | "EUR" (the unit of the 500) | Moved | `refunds/approval.py`, `SECOND_APPROVER_THRESHOLD`: the code has no currency, so the comment now says the amount is in EUR |
| 2a | The threshold is 500 EUR | Dropped | `refunds/approval.py` line 5 |
| 2b | The threshold is the finance controller's four-eyes rule (decision PAY-31) | Moved | `refunds/approval.py`, `SECOND_APPROVER_THRESHOLD` comment |
| 3 | Do not raise it without finance's sign-off | Moved | `refunds/approval.py`, `SECOND_APPROVER_THRESHOLD` comment |
| 4 | If `can_send()` stays false for more than a day because a second approver is missing, ask in #fin-ops; finance can approve the refund from the provider dashboard | Kept | Operational step. Still on the page. `can_send()` matches the described behaviour |
| 5 | `send_refund()` posts the refund to the payment provider and returns the provider's refund id | Dropped | `refunds/provider.py`: `send_refund` posts to `/v2/refunds` and returns `response["refund_id"]` |
| 6 | The provider refuses a second refund with the same idempotency key | Moved | `refunds/provider.py`, `send_refund`: comment above the `Idempotency-Key` header |
| 7a | `send_refund()` uses the refund's own id as the key | Dropped | `refunds/provider.py`: `headers={"Idempotency-Key": refund["id"]}`; `tests/test_refunds.py` asserts this header |
| 7b | ...so a retried call never pays out twice | Moved | Same comment as claim 6 |
| 8 | The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before then disappear | Kept | Fact about an external system that no code here relies on. Still on the page. Listed as a gap below |
| 9 | The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team | Kept | Fact about an external system. No code here sets or rotates keys; `send_refund` takes `session` as an argument. Still on the page. Listed as a gap below |

No claim was classed as not migrated: nothing on the page contradicts the code.

## Edits

- `refunds/approval.py`: comment above `SECOND_APPROVER_THRESHOLD` (claims 1b, 2b, 3).
- `refunds/provider.py`: two-line comment above the `Idempotency-Key` header inside `send_refund` (claims 6, 7b).
- `docs/refunds.md`: removed claims 1, 2, 3, 5, 6, 7. Kept claims 4, 8, 9 as written under their original headings. The headings stay because kept claims remain under each.
- No other file changed. Code, tests, `README.md` and `docs/onboarding.md` are byte-identical.

## Other files

- Stated moved facts elsewhere: none. `README.md`, `docs/onboarding.md` and `tests/test_refunds.py` do not repeat the threshold rule, decision PAY-31 or the idempotency reasoning. The test file already checks the 500 boundary and the `Idempotency-Key` header.
- Links to the page or to a removed section: none. Nothing in the repository refers to `refunds.md`.

## Gaps for you to fill

1. **Page not deleted.** Claims 4, 8 and 9 have no code home, so `docs/refunds.md` still holds them. Once you decide where they go (for example a runbook or the onboarding page), the file can be deleted. I did not delete it.
2. **Claim 8 (sandbox wipe, Mondays 06:00 UTC).** Cannot be checked against this repository. Please confirm it is still true.
3. **Claim 9 (key rotation every 90 days).** Cannot be checked against this repository. Please confirm it is still true and who owns the rotation.
4. **Currency.** The "EUR" unit comes only from the page. The code does not state a currency. Please confirm that the amounts are in EUR.
