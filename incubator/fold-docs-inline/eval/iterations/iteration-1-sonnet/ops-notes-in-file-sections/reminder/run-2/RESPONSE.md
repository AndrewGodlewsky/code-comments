I moved two facts into code comments and trimmed docs/refunds.md. I changed no code and created no files. I didn't run the tests.

**Moved into comments**
- `refunds/approval.py`: a comment above `SECOND_APPROVER_THRESHOLD` says the 500 EUR threshold is the finance controller's four-eyes rule (PAY-31) and shouldn't be raised without finance's sign-off.
- `refunds/provider.py`: a comment beside the `Idempotency-Key` header says the provider refuses a second refund with the same key. Keying on the refund id therefore means a retry never pays out twice.

**Dropped because the code already shows it**
- `needs_second_approver` is true at 500 or more (`>=` against the constant, and the test checks 500 and 499.99).
- `send_refund()` posts to the provider and returns its refund id.

**Contradictions**: none. Every claim on the page matches the code.

**Kept in docs/refunds.md, with no code to sit beside**
- The #fin-ops escalation when `can_send()` stays false for more than a day.
- The sandbox wipe every Monday at 06:00 UTC.
- The 90-day API key rotation by the platform team. The session is passed in, so no code here owns the keys.

I reorganised the page under "Approval" and "Provider" headings, since the file headings pointed at code that no longer carries those notes. This page can't be deleted yet unless you want those three notes moved somewhere else, such as docs/onboarding.md.
