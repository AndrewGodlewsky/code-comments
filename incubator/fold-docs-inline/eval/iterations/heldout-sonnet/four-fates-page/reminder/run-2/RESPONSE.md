I checked each claim on docs/digests.md against the code. No code was changed and no files were created.

**Needs your decision: the page contradicts the code.** It says `due()` holds a digest back for 24 hours. `MIN_HOURS_BETWEEN_DIGESTS` in `notify/settings.py` is 6, and `due()` and the test both use it. I did not carry the 24-hour claim over. I also left out the NOTIF-9 survey rationale, because it explains the 24-hour figure. Either the page is stale or the setting is wrong. Once you know which, the rationale can go in a comment beside the setting.

**Moved into a comment:**
- The mail relay folds subject headers longer than 78 characters and some clients then garble them (MAIL-71). It is now a comment above `SUBJECT_LIMIT` in `notify/mail.py`.

**Left out because the code already shows it:**
- `build_digest()` groups unread notifications by project.
- Subjects are cut to 78 characters. The number and the truncation are both in the code.

**Kept in documents, since there is no code to put a comment beside:**
- The digest job runs after the nightly cleanup, so digests never include removed notifications. I added this to `README.md`.
- Support pauses all sending from the mail provider's dashboard during an incident, and you should ask in #mail-ops first. I added this to `docs/oncall.md`.

I did not touch `docs/digests.md` itself, so you can delete it when you're ready.
