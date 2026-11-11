I moved the refund notes from docs/refunds.md into the code they describe. Nothing else changed, and I left docs/refunds.md in place so you can delete it with the rest of the folder.

- refunds/approval.py: the 500 EUR threshold comment (four-eyes rule, decision PAY-31, no change without finance sign-off). The #fin-ops escalation for a refund stuck without a second approver is in the can_send docstring.
- refunds/provider.py: the Monday 06:00 UTC sandbox wipe is in the module docstring. The 90-day API key rotation is in the send_refund docstring. The idempotency reasoning (refund id as Idempotency-Key, so retries never pay out twice) is a comment above the request.

Not moved:
- docs/onboarding.md (provider dashboard access) is not about refunds code, so I left it alone. Decide whether it moves or goes.
- The statement that the threshold is in EUR is taken from docs/refunds.md. The code uses a bare Decimal with no currency, so nothing enforces that.

The unit tests pass (python -m unittest discover -s tests -t .).
