I folded docs/digests.md into the code. Comments changed in two files, and the page is slimmed to the claims that have no code home. Nothing else changed.

Fate list, in page order:

1. "The digest job runs after the nightly notification cleanup, so a digest never includes notifications that the cleanup removed." Fate: Kept. Evidence: the cleanup job and the scheduler are not in this repo. build_digest (notify/digest.py:14-19) filters only on the read flag and does not depend on the cleanup. This is a gap: I could not check it here.
2. "`build_digest()` groups a user's unread notifications by project." Fate: Dropped. Evidence: notify/digest.py:14-19 (filters on `not note["read"]`, groups by `note["project"]`).
3. "`due()` holds back a user's next digest until ... after the last one." Fate: Dropped. Evidence: notify/digest.py:9-11.
4. "...until 24 hours after the last one." Fate: Not migrated. Evidence: notify/settings.py:4 sets `MIN_HOURS_BETWEEN_DIGESTS = 6`, and notify/digest.py:11 uses that constant. Which is right: 24 hours (page) or 6 hours (code)?
5. "because users on busy projects complained about digest floods in the 2025 survey (NOTIF-9)." Fate: Moved to notify/settings.py, comment on `MIN_HOURS_BETWEEN_DIGESTS`. The reason is moved without the 24-hour figure. Please confirm the reason still applies at 6 hours.
6. "Subjects are cut to `SUBJECT_LIMIT` (78) characters." Fate: Dropped. Evidence: notify/mail.py:3 (`SUBJECT_LIMIT = 78`) and notify/mail.py:8 (truncates to that limit).
7. "...because the company mail relay folds longer subject headers, and some mail clients then show the subject garbled (MAIL-71)." Fate: Moved to notify/mail.py, comment on `SUBJECT_LIMIT`.
8. "During a mail-provider incident, support pauses all sending from the provider's dashboard." Fate: Kept. Operational step about an external system; no code here relies on it.
9. "Ask in #mail-ops before pausing." Fate: Kept. Operational step.

Changes:
- notify/settings.py: added a comment line under the existing one, which is unchanged. Added the NOTIF-9 reason.
- notify/mail.py: added a two-line comment above `SUBJECT_LIMIT` with the MAIL-71 reason.
- docs/digests.md: removed the moved, dropped and not-migrated bullets. The heading, the intro paragraph and the incident bullet remain as written. The page is not deleted because kept claims remain.

Other files:
- No other file states a moved fact. NOTIF-9 and MAIL-71 now appear only in the new comments.
- No file links to docs/digests.md or to a removed section.

Gaps for you to fill:
- Decide the 24-hour versus 6-hour conflict (item 4). The code currently uses 6.
- Items 1, 8 and 9 describe systems outside this repo (the nightly cleanup, the mail provider and its incident process). I could not verify them here.
- docs/digests.md still exists with the kept claims. Delete it only after those three are moved elsewhere, such as a runbook or the team's ops docs.
- The overview question does not arise here: the page has no whole-module overview.
- The code-comments skill named in AGENTS.md is not in the available skill list, so I followed the existing comment style in these files (`#` comments and the module docstrings).
