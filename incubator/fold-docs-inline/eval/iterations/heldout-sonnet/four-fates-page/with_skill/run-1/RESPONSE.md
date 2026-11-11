I moved two reasons into comments and slimmed docs/digests.md to the two claims that have no code home. The page is not deleted, because those two remain.

Fate list, in page order:

1. "The digest job runs after the nightly notification cleanup, so a digest never includes notifications that the cleanup removed." Kept. No code in this repo schedules the job or runs the cleanup, so I can't check it (gap).
2. "`build_digest()` groups a user's unread notifications by project." Dropped. `notify/digest.py` `build_digest` and `test_groups_unread_by_project` state it.
3. "`due()` holds back a user's next digest until some time after the last one." Dropped. `due` and `MIN_HOURS_BETWEEN_DIGESTS` state it.
4. "... until 24 hours after the last one." Not migrated. `notify/settings.py` `MIN_HOURS_BETWEEN_DIGESTS` is 6, not 24. Which side is right? I changed no code.
5. "... because users on busy projects complained about digest floods in the 2025 survey (NOTIF-9)." Moved, at `notify/settings.py` `MIN_HOURS_BETWEEN_DIGESTS`, beside the existing comment. I wrote it as a reason for spacing digests out, with no number and no survey claim. The page tied this reason to 24 hours, so confirm it still justifies 6.
6. "Subjects are cut to `SUBJECT_LIMIT` (78) characters." Dropped. `notify/mail.py` `subject` and `SUBJECT_LIMIT = 78` state it, and the value matches.
7. "... because the company mail relay folds longer subject headers, and some mail clients then show the subject garbled (MAIL-71)." Moved, as a comment on `SUBJECT_LIMIT` in `notify/mail.py`.
8. "During a mail-provider incident, support pauses all sending from the provider's dashboard." Kept. It is an operational step with nothing in the code to sit beside.
9. "Ask in #mail-ops before pausing." Kept, for the same reason.

Other files that state a moved fact: none. AGENTS.md, README.md and docs/oncall.md do not mention them.

Files linking to docs/digests.md: none.

Gaps and what remains: item 1 needs someone who knows the job scheduler to confirm it. docs/digests.md still holds items 1, 8 and 9 under its heading. If you do want to retire the page, those need a new home.
