I moved the digest notes from docs/digests.md into the code they describe. I left docs/digests.md in place, since you said it is going away and I did not delete it.

Moved:
- notify/digest.py, above build_digest(): the digest job runs after the nightly notification cleanup, so a digest never includes notifications the cleanup removed.
- notify/mail.py, above SUBJECT_LIMIT: the mail relay folds longer subject headers, and some clients then show them garbled (MAIL-71).
- notify/settings.py, above MIN_HOURS_BETWEEN_DIGESTS: the gap exists because users on busy projects complained about digest floods in the 2025 survey (NOTIF-9).

Needs your decision:
- The doc says digests are held back for 24 hours. The code sets MIN_HOURS_BETWEEN_DIGESTS = 6, and due() uses that constant. I recorded the code's value and did not write 24 anywhere. Please tell me which value is intended. If it is 24, the constant needs changing, and the comment should then state the reason for that value.

Not moved:
- The mail-provider incident note (support pauses sending from the provider's dashboard; ask #mail-ops before pausing) describes an operational procedure, not something this code does. It has no home in the code. docs/oncall.md looks like the natural place for it, so I left it for you to move.

No tests changed. tests/test_digest.py already names what it checks.
