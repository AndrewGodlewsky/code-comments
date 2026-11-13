I moved the code-related facts from `docs/digests.md` into comments, moved the one operational note to `docs/oncall.md`, and deleted `docs/digests.md`.

- `notify/digest.py` (module docstring): the digest job must run after the nightly notification cleanup, so digests never include removed notifications.
- `notify/settings.py`: the reason a gap between digests exists is digest-flood complaints in the 2025 survey (NOTIF-9).
- `notify/mail.py`: `SUBJECT_LIMIT` exists because the mail relay folds longer subject headers and some clients then show them garbled (MAIL-71).
- `docs/oncall.md`: the incident procedure (support pauses sending from the provider dashboard, ask in #mail-ops first). It is a runbook step with no code to attach to, so I kept it as a doc.
- Dropped: the `build_digest()` grouping bullet, since the code already says that.

Conflict to check: `digests.md` said digests are held back for 24 hours, but `MIN_HOURS_BETWEEN_DIGESTS` is 6. I did not change the code, and I did not write "24" into any comment. The NOTIF-9 note only says a gap exists. Please confirm which value is intended. If 24 is right, the setting needs changing, and if 6 is right, the doc was stale.
