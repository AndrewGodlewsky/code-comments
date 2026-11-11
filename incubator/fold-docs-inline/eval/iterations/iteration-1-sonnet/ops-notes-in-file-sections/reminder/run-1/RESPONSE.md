I checked each claim on docs/refunds.md against the code, moved what could go beside code, and deleted the page. No code changed and no files were created.

**Dropped, because the code already shows it**
- `needs_second_approver` is true at 500 or more (`approval.py`, and the test pins 500 and 499.99).
- `send_refund()` posts to the provider and returns the provider's refund id.
- `send_refund()` uses the refund's own id as the idempotency key (the `Idempotency-Key` header, also tested).

**Moved into comments**
- `refunds/approval.py`, above `SECOND_APPROVER_THRESHOLD`: the threshold is finance's four-eyes rule (PAY-31) and needs finance sign-off to raise.
- `refunds/provider.py`, above the `Idempotency-Key` header: the provider refuses a second refund with the same key, so a retry never pays out twice. Only the provider behaviour is stated, since the code shows the key.

**Kept in a document**
These have no code to sit beside, so I put them in a new "Refund operations" section in `docs/onboarding.md`, the only other doc:
- Ask in #fin-ops if `can_send()` stays false for over a day; finance can approve from the provider dashboard.
- The provider sandbox is wiped Mondays 06:00 UTC.
- API keys behind the session are rotated every 90 days by the platform team. The session is passed in, and nothing in this repo creates it or its keys.

**Contradictions**
None. Nothing on the page conflicts with the code. I couldn't verify the provider-side claims (duplicate-key refusal, sandbox wipe, rotation, PAY-31) from the repo, so they carry over as stated.
