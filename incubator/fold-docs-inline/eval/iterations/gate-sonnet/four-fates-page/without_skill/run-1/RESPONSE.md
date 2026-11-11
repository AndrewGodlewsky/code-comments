Moved the code-related parts of docs/digests.md into comments:

- notify/settings.py: why digests are spaced out (digest floods, NOTIF-9) on `MIN_HOURS_BETWEEN_DIGESTS`.
- notify/mail.py: why subjects are cut (relay folds long headers, MAIL-71) on `SUBJECT_LIMIT`.
- notify/digest.py: the module docstring now says the job must run after the nightly cleanup; `build_digest()` got a one-line docstring about grouping unread by project.

Not a code comment: the "pause sending during a provider incident, ask in #mail-ops" note is an operational procedure, so I added it to docs/oncall.md instead of dropping it.

One discrepancy for you to decide: digests.md says `due()` waits 24 hours, but `MIN_HOURS_BETWEEN_DIGESTS` is 6. I did not carry the 24 over and did not change the code. Either the doc was stale or the setting was changed by mistake; the comment states only the reason for the gap, not a number.

docs/digests.md itself is untouched; delete it when ready.
