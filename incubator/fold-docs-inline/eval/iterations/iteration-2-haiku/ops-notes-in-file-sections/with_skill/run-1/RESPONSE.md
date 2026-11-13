Folded docs/refunds.md into the code. Every claim on the page has a fate below. The page is not deleted, because some claims are kept.

Fate list (page order):

1. "`needs_second_approver(amount)` is true for refunds of 500 or more" - Dropped. Code states it: refunds/approval.py:5 `SECOND_APPROVER_THRESHOLD = Decimal("500")`, :9 `amount >= SECOND_APPROVER_THRESHOLD`; tests/test_refunds.py:23-24.
2. "...of 500 EUR" (currency part) - Kept, as a gap. The code has no currency anywhere, so it cannot be checked here. Page keeps: "The 500 threshold is in EUR."
3. "The 500 threshold is the finance controller's four-eyes rule (decision PAY-31)" - Moved to refunds/approval.py, symbol SECOND_APPROVER_THRESHOLD (reason plus ticket id).
4. "Do not raise it without finance's sign-off." - Moved to refunds/approval.py, symbol SECOND_APPROVER_THRESHOLD (constraint stated by the page).
5. "If `can_send()` stays false for more than a day because a second approver is missing, ask in #fin-ops; finance can approve the refund from the provider dashboard." - Kept (operational escalation step). Checked: refunds/approval.py:12-15 `can_send` returns false until a second approver exists, which matches the step.
6. "`send_refund()` posts the refund to the payment provider and returns the provider's refund id." - Dropped. Code states it: refunds/provider.py:9-16; tests/test_refunds.py:30-32.
7. "The provider refuses a second refund with the same idempotency key." - Moved to refunds/provider.py, docstring of symbol send_refund (outside contract the code relies on).
8. "`send_refund()` uses the refund's own id as the key" - Dropped. Code states it: refunds/provider.py:12 `headers={"Idempotency-Key": refund["id"]}`; tests/test_refunds.py:33.
9. "so a retried call never pays out twice" - Moved to refunds/provider.py, docstring of send_refund (reason the page gives for the key).
10. "The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before then disappear." - Kept. Fact about another system; no code here relies on it.
11. "The API keys behind `send_refund()`'s session are rotated every 90 days by the platform team." - Kept. The session is passed in by the caller; rotation happens outside this repository. Cannot be checked here (see gaps).

Not migrated: none. No claim contradicts the code.

Other files that state a moved fact: none. The threshold, the four-eyes rule and PAY-31 appear only in docs/refunds.md before this change, and nothing else in the folder links to the page.

Files linking to the page or to a removed section: none.

Gaps for you to fill:
- Currency: the code has no currency, so confirm that the 500 threshold and the refund amounts are EUR. Line 2 is kept until then.
- PAY-31: the decision record is not in this repository. Confirm it still exists and still names this rule.
- Sandbox wipe (Mondays 06:00 UTC) and the 90-day key rotation by the platform team: external facts, not checkable here.
- Page status: docs/refunds.md is not deleted. It still holds the #fin-ops escalation step, the sandbox fact and the key-rotation fact. The "# Refunds" title and the two section headings stay because each still has a kept claim under it. Once those are moved elsewhere or retired, the page can go.
