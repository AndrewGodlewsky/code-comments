docs/refunds.md now holds only what has no code to sit beside. Claim by claim:

- **`needs_second_approver` is true at 500 EUR or more.** Dropped: the function is one comparison against `SECOND_APPROVER_THRESHOLD`.
- **The 500 EUR threshold is the four-eyes rule (PAY-31); don't raise it without finance.** Moved to a comment above `SECOND_APPROVER_THRESHOLD` in refunds/approval.py.
- **Ask #fin-ops when a refund waits a day for a second approver.** Kept on the page: it's a support procedure.
- **`send_refund` posts the refund and returns the provider's id.** Dropped: the code shows it.
- **Retries never pay twice because the refund id is the idempotency key.** Moved to a comment at the top of `send_refund` in refunds/provider.py.
- **The sandbox is wiped every Monday at 06:00 UTC.** Kept on the page: it's about the provider's test system, which no code here touches.
- **API keys rotate every 90 days (platform team).** Kept on the page: no code here handles the keys.

You said the page is going, but those three notes have nothing in the code to sit beside, so I kept them on it rather than lose them; tell me if they should live in another document instead. I took the per-file headings off the page, since what's left isn't about either file. No code changed and I added no files.
