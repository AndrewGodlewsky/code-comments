# Refunds

## refunds/approval.py

- `needs_second_approver(amount)` is true for refunds of 500 EUR or more.
- The 500 EUR threshold is the finance controller's four-eyes rule (decision PAY-31). Do
  not raise it without finance's sign-off.
- If `can_send()` stays false for more than a day because a second approver is missing,
  ask in #fin-ops; finance can approve the refund from the provider dashboard.

## refunds/provider.py

- `send_refund()` posts the refund to the payment provider and returns the provider's
  refund id.
- The provider refuses a second refund with the same idempotency key. `send_refund()`
  uses the refund's own id as the key, so a retried call never pays out twice.
- The provider's sandbox is wiped every Monday at 06:00 UTC; test refunds made before
  then disappear.
- The API keys behind `send_refund()`'s session are rotated every 90 days by the
  platform team.
