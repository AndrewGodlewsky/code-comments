I moved the contents of `docs/digests.md` into the code and deleted the file. `python -m unittest discover -s tests -t .` passes (3 tests).

Where each point went:

- **Digest job runs after the nightly cleanup, so cleaned notifications never appear.** Now in the `notify/digest.py` module docstring.
- **`due()` holds back the next digest, and the reason (NOTIF-9 survey complaints).** Now in the `due()` docstring. The docstring names `MIN_HOURS_BETWEEN_DIGESTS` rather than a number.
- **`build_digest()` groups unread notifications by project.** Now in the `build_digest()` docstring.
- **Subjects are cut to 78 characters because the mail relay folds longer headers (MAIL-71).** Now as a comment above `SUBJECT_LIMIT` in `notify/mail.py`, with a docstring on `subject()`.
- **Mail-provider incident: pause sending from the dashboard, ask in #mail-ops first.** This is an ops procedure, not code behaviour, so I added it to `docs/oncall.md` under a new "Mail-provider incidents" heading.

Please check one conflict before this ships. The doc said digests are held back for 24 hours, but `notify/settings.py` sets `MIN_HOURS_BETWEEN_DIGESTS = 6`. I kept the code's value of 6 and did not write "24 hours" anywhere. If 24 is the intended gap, the setting needs changing, and the `due()` docstring then stays correct as written.

I also added a one-line comment to `settings.py` saying `digest.due()` enforces the gap. No code logic changed.
