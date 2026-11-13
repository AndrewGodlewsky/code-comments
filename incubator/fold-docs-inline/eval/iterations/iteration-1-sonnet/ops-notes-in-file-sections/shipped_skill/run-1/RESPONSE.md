I removed docs/refunds.md and moved its content as follows.

Into code comments:
- refunds/approval.py: the 500 EUR threshold is the finance controller's four-eyes rule (decision PAY-31), and it must not be raised without finance's sign-off. This is a comment on `SECOND_APPROVER_THRESHOLD`. I also added a one-line docstring on `needs_second_approver` stating the 500 EUR-or-more rule.
- refunds/provider.py: a docstring on `send_refund` saying it returns the provider's refund id. A comment explains that the provider refuses a repeat idempotency key and that the refund's own id is used as the key, so a retry never pays out twice.

Into README.md, under a new "Operations" heading, because these are not facts about the code:
- Ask in #fin-ops if `can_send()` stays false for more than a day for lack of a second approver. Finance can approve from the provider dashboard.
- The provider sandbox is wiped every Monday at 06:00 UTC.
- API keys are rotated every 90 days by the platform team.

If you would rather not keep these in the README, they can go to docs/onboarding.md or a runbook. I did not put them in code comments.

I did not run the tests, and I did not change any code behaviour.
