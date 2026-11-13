I moved the contents of `docs/digests.md` and deleted the file. Tests pass (`python -m unittest discover -s tests -t .`, 3 tests).

Where each point went:

- **Cleanup runs before the digest job.** Module docstring in `notify/digest.py`, since the ordering constrains the job that calls this code.
- **Groups unread notifications by project.** Docstring on `build_digest()`.
- **Next digest held back until the gap has passed (NOTIF-9).** Rationale comment on `MIN_HOURS_BETWEEN_DIGESTS` in `notify/settings.py` (per AGENTS.md, settings live there), plus a pointer from `due()`.
- **Subject cut to `SUBJECT_LIMIT` because the relay folds long headers (MAIL-71).** Comment above `SUBJECT_LIMIT` in `notify/mail.py`.
- **Pause sending during a mail-provider incident, ask #mail-ops first.** This is an operational step, not something the code does, so I put it in `docs/oncall.md` under a new "Mail-provider incidents" heading.

**Needs your decision:** the old doc said digests are held back for **24 hours**, but `notify/settings.py` sets `MIN_HOURS_BETWEEN_DIGESTS = 6`, and the `due()` test uses that value. I followed the code and did not carry over "24 hours". The comment now gives the rationale without a number. Please confirm whether 6 or 24 is intended. If it should be 24, change the setting and the test follows it.

Other notes:
- No other file referenced `docs/digests.md`.
- `SUBJECT_LIMIT` lives in `notify/mail.py`, not `settings.py` as AGENTS.md suggests. I left it where it was to keep this change to moving docs.
