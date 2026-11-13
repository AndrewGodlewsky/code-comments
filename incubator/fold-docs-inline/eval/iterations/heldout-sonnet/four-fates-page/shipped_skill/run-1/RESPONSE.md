I moved the facts from docs/digests.md that belong with code into comments, and put the support runbook step in docs/oncall.md. I did not delete docs/digests.md.

- notify/mail.py: a comment on `SUBJECT_LIMIT` says the company mail relay folds longer subject headers and some clients then show them garbled (MAIL-71).
- notify/digest.py: the `build_digest()` docstring says to run it after the nightly notification cleanup, so a digest never includes removed notifications.
- docs/oncall.md: added the incident step (support pauses all sending from the provider's dashboard; ask in #mail-ops first). It is a human procedure, not a code fact.
- Not moved: the "groups unread notifications by project" line, because the code already shows it.

Needs your decision: docs/digests.md says `due()` holds a user's next digest back for 24 hours, because of the 2025 survey about digest floods (NOTIF-9). `MIN_HOURS_BETWEEN_DIGESTS` in notify/settings.py is 6. I left the code alone and wrote no comment for it, since I can't tell whether 6 is a deliberate change or a bug. Which value is intended? Once you say, I'll add the NOTIF-9 reason beside the setting. The test uses the constant, so it passes either way.
