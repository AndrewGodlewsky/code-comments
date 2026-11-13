I moved the contents of docs/digests.md next to the code and deleted the file. The test suite still passes (3 tests).

Moved:
- notify/digest.py module docstring: the digest job runs after the nightly notification cleanup, so a digest never includes notifications the cleanup removed.
- notify/settings.py above MIN_HOURS_BETWEEN_DIGESTS: users on busy projects complained about digest floods in the 2025 survey (NOTIF-9).
- notify/mail.py above SUBJECT_LIMIT: the company mail relay folds longer subject headers, and some mail clients then show the subject garbled (MAIL-71).
- docs/oncall.md, new "Mail-provider incidents" section: the pause-sending instruction (ask in #mail-ops before pausing). I put this here rather than in code because it is an operational procedure, not something the code enforces.

Needs your decision:
- The docs say digests are held back for 24 hours, but notify/settings.py sets MIN_HOURS_BETWEEN_DIGESTS = 6. I did not change the code and did not write "24 hours" into any comment. The 24-hour figure looks stale, or the setting is wrong. Please confirm which is intended, and I will make the comment match.
