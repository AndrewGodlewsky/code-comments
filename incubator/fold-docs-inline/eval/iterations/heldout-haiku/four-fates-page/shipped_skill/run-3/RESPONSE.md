I moved the parts of docs/digests.md that belong beside the code into comments. I left docs/digests.md in place so you can delete it once you have checked the moves. The unit tests pass (3 of 3). I changed comments only.

Moved:
- notify/digest.py, `build_digest` docstring: the digest runs after the nightly notification cleanup, so it never includes notifications the cleanup removed. The function does not check for removed notifications itself, so that ordering has to hold.
- notify/mail.py, above `SUBJECT_LIMIT`: the company mail relay folds longer subject headers, and some clients then show the subject garbled (MAIL-71).
- notify/settings.py, under `MIN_HOURS_BETWEEN_DIGESTS`: users on busy projects complained about digest floods in the 2025 survey (NOTIF-9).

Needs your decision:
- The gap value conflicts with the doc. docs/digests.md says a user's next digest waits 24 hours, but `MIN_HOURS_BETWEEN_DIGESTS` is 6. I did not write either value into a comment. Please confirm which is intended. If 6 is a deliberate change, the reason is missing and I need it before I can record it.

Not moved:
- docs/digests.md says that during a mail-provider incident, support pauses all sending from the provider's dashboard, and that someone should ask in #mail-ops before pausing. This is an operational procedure, not a fact about the code, so I did not put it in a comment. It should go to docs/oncall.md or another runbook before docs/digests.md is deleted, or it will be lost.

No git operations were run, per the task instructions.
