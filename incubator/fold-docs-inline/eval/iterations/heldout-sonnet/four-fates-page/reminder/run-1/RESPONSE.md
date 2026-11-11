I checked each claim on docs/digests.md against the code. docs/digests.md itself is untouched, since you're removing it.

**Contradicted by the code (not carried over):** the page says `due()` holds a user's next digest back for 24 hours. The code uses `MIN_HOURS_BETWEEN_DIGESTS = 6` in `notify/settings.py`, and the test uses that constant. Either the page is stale or the setting was changed by mistake, so please confirm which. I left out the NOTIF-9 reason (digest-flood complaints in the 2025 survey) because it was given for the 24-hour gap. If 6 hours is intended, that reason could go in a comment on the setting.

**Left out because the code already shows it:** `build_digest()` groups unread notifications by project.

**Moved into a comment:** the reason for `SUBJECT_LIMIT` (78). It is now a comment above it in `notify/mail.py`: the mail relay folds longer subject headers, which garbles the subject in some clients (MAIL-71).

**Kept in documents (no code to sit beside):**
- The digest job runs after the nightly cleanup, so digests never include removed notifications. I added this to README.md.
- The mail-provider incident procedure (support pauses sending from the provider's dashboard; ask in #mail-ops first). I added this to docs/oncall.md.

No code was changed and no files were created.
