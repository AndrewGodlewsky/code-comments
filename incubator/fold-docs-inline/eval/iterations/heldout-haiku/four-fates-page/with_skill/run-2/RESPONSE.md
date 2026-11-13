# Fate list for docs/digests.md

Page: `docs/digests.md`. It is slimmed, not deleted, because two kept claims remain.

1. "The digest job runs after the nightly notification cleanup, so a digest never includes notifications that the cleanup removed." **Kept.** The ordering depends on a cleanup job and a schedule that are not in this repo. `notify/digest.py` says it "schedules" digests, but no scheduling code exists here. Gap: confirm where the cleanup job and its schedule live.
2. "`build_digest()` groups a user's unread notifications by project." **Dropped.** `notify/digest.py` `build_digest()` groups by `note["project"]` for unread notes. `tests/test_digest.py` `test_groups_unread_by_project` checks it.
3. "`due()` holds back a user's next digest until ... after the last one." **Dropped.** `notify/digest.py` `due()` compares the gap against `MIN_HOURS_BETWEEN_DIGESTS`. `tests/test_digest.py` `test_due_after_the_gap` checks it.
4. "... until 24 hours after the last one, because users on busy projects complained about digest floods in the 2025 survey (NOTIF-9)." **Not migrated.** `notify/settings.py` `MIN_HOURS_BETWEEN_DIGESTS = 6`, which is 6 hours, not 24. I quoted the whole sentence, including the reason, and removed it from the page. I treated the reason as part of the contradicted value. If you want the survey reason kept as history, say so. Which side is right, 24 or 6? If 6 is right, the NOTIF-9 reason needs a new home or should be dropped.
5. "Subjects are cut to `SUBJECT_LIMIT` (78) characters." **Dropped.** `notify/mail.py` `SUBJECT_LIMIT = 78` and `subject()` truncate to it. `tests/test_digest.py` `test_subject_is_cut` checks it.
6. "because the company mail relay folds longer subject headers, and some mail clients then show the subject garbled (MAIL-71)." **Moved** to a comment above `SUBJECT_LIMIT` in `notify/mail.py`. The ticket id MAIL-71 is kept.
7. "During a mail-provider incident, support pauses all sending from the provider's dashboard. Ask in #mail-ops before pausing." **Kept.** Operational steps with no code home.

## Changes

- `notify/mail.py`: two-line comment added above `SUBJECT_LIMIT` (claim 6).
- `docs/digests.md`: the `build_digest`, `due` and subject bullets are removed (claims 2 to 6). The heading, claim 1 and claim 7 remain as written.
- `RESPONSE.md`: this file.
- No other file changed. No code changed, and no test was changed.

## Other files and links

- No other file states the moved fact (MAIL-71, the 78 limit, or the mail relay reason). Checked by search.
- No file links to `docs/digests.md`.
- `AGENTS.md` and `README.md` do not mention digest timing or subjects.

## Gaps for the user

- The cleanup job and its schedule (claim 1) are outside this repo.
- Whether the digest gap is 24 or 6 hours (claim 4).
- Whether `docs/digests.md` can be deleted. Once claims 1 and 7 have a new home, or you accept keeping them, the page can go.
