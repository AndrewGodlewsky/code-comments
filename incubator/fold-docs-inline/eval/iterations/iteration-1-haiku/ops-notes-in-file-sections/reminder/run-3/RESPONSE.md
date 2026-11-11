I moved the refund notes out of docs/refunds.md and deleted that page. Nothing was changed except comments and the onboarding doc.

Checked against the code, nothing was contradicted. The code already shows the 500 threshold, the `>=` comparison, and that `send_refund()` returns the provider's refund id, so I left those out.

Moved into code comments:
- refunds/approval.py, above `SECOND_APPROVER_THRESHOLD`: the four-eyes rule from the finance controller (PAY-31), the 500 EUR currency, and "do not raise without finance's sign-off". The code has no currency, so EUR lives only in this comment.
- refunds/provider.py, above the `send_refund` `Idempotency-Key` post: the provider rejects a repeated key, so a retry with the refund's id cannot pay out twice.
- refunds/provider.py, above `send_refund`: the API keys behind `session` are rotated every 90 days by the platform team. The keys belong to the session the caller passes in, so the comment sits on `send_refund`.

Moved into docs/onboarding.md, under a new "Refunds ops notes" section, because no code governs them:
- Ask #fin-ops when a refund stays unapproved for more than a day because its second approver is missing. Finance can approve it from the provider dashboard.
- The provider sandbox is wiped every Monday at 06:00 UTC, so test refunds made before then disappear.

Judgement calls to check:
- The 90-day key rotation is a property of the session the caller passes in, not something this repo creates. I put it on `send_refund` as the code it governs. If you'd rather keep it with the ops notes, it moves easily.
- The sandbox wipe went to the document, not a comment, because no code in the repo selects the sandbox.
- I deleted docs/refunds.md since it is now empty. Restore it from the original if you wanted to keep it as a stub.
- The comments and onboarding text are not verified against the provider or finance. They are copied from the old page.
- No code was changed and no new files were created. I did not run the tests.
