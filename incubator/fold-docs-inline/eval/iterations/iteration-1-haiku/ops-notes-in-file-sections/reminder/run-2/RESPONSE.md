I moved what belonged next to the code out of docs/refunds.md. The page now holds only a pointer and can be deleted.

Checked against the code and left out, because the code already shows it:
- `needs_second_approver()` is true at 500 or more.
- `send_refund()` posts to the provider and returns the provider's refund id.
- The idempotency key is the refund's own id.

Moved into code comments:
- `refunds/approval.py`, beside `SECOND_APPROVER_THRESHOLD`: the threshold is in EUR, it is the finance controller's four-eyes rule (decision PAY-31), and it must not be raised without finance's sign-off.
- `refunds/approval.py`, in `can_send()`: if it stays False for more than a day because a second approver is missing, ask in #fin-ops, where finance can approve from the provider dashboard.
- `refunds/provider.py`, beside the `Idempotency-Key` header: the provider refuses a repeated key, so a retried call cannot pay out twice.
- `refunds/provider.py`, above `session.post`: the API keys behind the session are rotated every 90 days by the platform team. This is a judgment call. The code does not manage keys, but the function depends on the session's credentials, so I placed it there rather than in a document.

Moved into a document:
- `docs/onboarding.md`, new "Provider sandbox" section: the sandbox is wiped every Monday at 06:00 UTC, so test refunds made before then disappear. No code governs this, and it is about the external environment, so a document is the right home.

Contradictions: I found none between the page and the code.

Things to check:
- The retry claim holds, but the behaviour may surprise a caller. If the first send succeeded and the response was lost, the retry is refused and `send_refund()` raises `ProviderError` rather than returning the original refund id. The comment says only that payouts cannot repeat. I did not change any code.
- I could not verify decision PAY-31 or the #fin-ops and #it-help channel names from the repository. They are carried over as written.
- The README needed no change.
- I did not delete docs/refunds.md, since you said it is going but did not ask me to delete it.

Only comments and the onboarding section were added. No code was changed and no new files were created. The unit tests pass (3 of 3) with the comments in place.
