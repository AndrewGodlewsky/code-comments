I moved two reasons into comments, flagged one claim that disagrees with the code, and kept the page with two claims. I did not delete `docs/digests.md`.

Fate list, in page order:

1. "The digest job runs after the nightly notification cleanup, so a digest never includes cleaned-up notifications." **Kept.** No code in this repo schedules the job or runs the cleanup, so I can't check it. This is a gap.
2. "`build_digest()` groups a user's unread notifications by project." **Dropped.** `notify/digest.py` `build_digest` and `test_groups_unread_by_project` already state it.
3. "`due()` holds back a user's next digest until some time after the last one." **Dropped.** `due` in `notify/digest.py` states it.
4. "...until 24 hours after the last one." **Not migrated.** `notify/settings.py` `MIN_HOURS_BETWEEN_DIGESTS` is 6, not 24. Which is right, the page or the code? I changed no code.
5. "...because users on busy projects complained about digest floods in the 2025 survey (NOTIF-9)." **Moved** to a comment on `MIN_HOURS_BETWEEN_DIGESTS` in `notify/settings.py`, with the ticket id and without the 24-hour value. If 24 hours turns out to be the intended value, this reason was given for that value.
6. "Subjects are cut to `SUBJECT_LIMIT` characters." **Dropped.** `subject` in `notify/mail.py` and `test_subject_is_cut` state it.
7. "...(78)." **Dropped.** `SUBJECT_LIMIT = 78` in `notify/mail.py`.
8. "...because the company mail relay folds longer subject headers and some clients show the subject garbled (MAIL-71)." **Moved** to a comment on `SUBJECT_LIMIT` in `notify/mail.py`, with the ticket id.
9. "During a mail-provider incident, support pauses all sending from the provider's dashboard." **Kept.** It is an operational step with no code to sit beside.
10. "Ask in #mail-ops before pausing." **Kept.** Same reason as 9.

Other files stating the same facts: none. `AGENTS.md`, `README.md` and `docs/oncall.md` do not repeat them.

Files linking to the page: none. No file references `docs/digests.md`.

Gaps for you to fill:
- The job-ordering claim (1) concerns code outside this repo, so I can't check it.
- Which value is right for the digest gap, 24 hours (page) or 6 (code)?

`docs/digests.md` still holds claims 1, 9 and 10, so I did not delete it. Those are operational and cross-system facts with no code to sit beside, so they will need a new home before the page can go. Nothing else changed.
