I moved docs/refunds.md into the code and README and deleted the page. No code changed; I only added comments.

Checked against the code, nothing was contradicted.

What went where:

- refunds/approval.py, beside SECOND_APPROVER_THRESHOLD: the threshold is in EUR (the code has no currency), it is the finance controller's four-eyes rule (PAY-31), and it should not be raised without finance sign-off.
- refunds/approval.py, in can_send(): if it stays False for more than a day because the second approver is missing, ask in #fin-ops, where finance can approve from the provider dashboard.
- refunds/provider.py, beside the Idempotency-Key header: the provider refuses a second refund with the same key, and the refund id is the key, so a retry never pays out twice.
- README.md, new "Operations" section (no code to sit beside): the provider sandbox is wiped Mondays 06:00 UTC, so test refunds before then disappear; the API keys behind send_refund()'s session are rotated every 90 days by the platform team.

Left out because the code already shows them: the 500 threshold value and its >= comparison, send_refund() posting and returning the refund id, and the 2-approver logic in can_send().

Things to check before you rely on this:

1. The #fin-ops note says finance can approve from the provider dashboard. Nothing in this repo reads provider-side approvals; can_send() only counts refund["approvers"]. I carried the note over because the code does not contradict it, but a dashboard approval may not make can_send() return True.
2. The idempotency comment says a retry never pays out twice. It does not say what the caller sees. If the first call succeeded, a retry will likely be refused, and send_refund() raises ProviderError rather than returning the original refund id. Callers may need to handle that.
3. The EUR currency and decision PAY-31 come from the page and are not verifiable in the code.
