I moved the content of docs/digests.md into the code it describes and deleted the file. Nothing else referenced it.

Where each point went:

- Digests run after the nightly cleanup, so they never include removed notifications: docstring on `build_digest()` in `notify/digest.py`.
- Digests to one user are spaced by `MIN_HOURS_BETWEEN_DIGESTS`: docstring on `due()` in `notify/digest.py`, which points to settings.py.
- Why digests are spaced out (NOTIF-9, digest floods): comment on `MIN_HOURS_BETWEEN_DIGESTS` in `notify/settings.py`.
- Subject cut at 78 characters because the mail relay folds longer headers (MAIL-71): comment on `SUBJECT_LIMIT` in `notify/mail.py`.
- Mail-provider incident procedure (pause from the provider dashboard, ask in #mail-ops first): this is an operational step rather than something about the code, so I put it in a new section in `docs/oncall.md`.

Please check one thing before merging. docs/digests.md said `due()` holds a user's next digest for 24 hours, but `notify/settings.py` sets `MIN_HOURS_BETWEEN_DIGESTS = 6`. I did not change the code. The comments describe the current value of 6 hours and do not repeat the 24-hour figure. If 24 hours is the intended value, the setting needs changing separately.

No behaviour changed. The unit tests still run with `python -m unittest discover -s tests -t .`.
