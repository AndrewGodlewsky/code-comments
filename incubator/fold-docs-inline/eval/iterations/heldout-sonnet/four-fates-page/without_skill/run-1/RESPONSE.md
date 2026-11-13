I moved the content of docs/digests.md into the code comments and docs/oncall.md, so you can delete it. I haven't deleted it and I didn't run the tests.

- `notify/mail.py`: a comment on `SUBJECT_LIMIT` says why subjects are cut (the relay folds long headers and clients garble them, MAIL-71).
- `notify/settings.py`: the comment on `MIN_HOURS_BETWEEN_DIGESTS` now gives the reason for holding digests back (digest-flood complaints in the 2025 survey, NOTIF-9).
- `notify/digest.py`: `build_digest()` has a docstring. It says it groups unread notifications by project and that the job runs after the nightly cleanup.
- `docs/oncall.md`: the paragraph on pausing sending during a mail-provider incident is now a "Mail-provider incidents" section. It is an operational step, not a code fact, so I put it where on-call staff look.

**Needs your decision:** docs/digests.md says the gap between digests is 24 hours. `notify/settings.py` sets `MIN_HOURS_BETWEEN_DIGESTS = 6`. I kept the code's value and wrote no number in the comments. Either the doc was stale or the setting was changed by mistake. Please confirm which is right.

I left out the doc's line that `due()` holds back digests, since the code already says that.
