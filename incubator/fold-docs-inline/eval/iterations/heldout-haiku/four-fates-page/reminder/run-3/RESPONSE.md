I checked each claim on docs/digests.md against the code and moved what remained. I did not change any code, did not create files, and did not delete docs/digests.md; you can remove it once you have read this.

**One claim contradicts the code (not carried over):**
- The page says `due()` holds a digest back until 24 hours after the last one. `notify/settings.py` sets `MIN_HOURS_BETWEEN_DIGESTS = 6`, and `due()` uses that value. I left the 24-hour figure out. Please confirm whether the gap was changed on purpose or the page is stale.

**Left out because the code shows it:**
- `build_digest()` groups a user's unread notifications by project. The code in `notify/digest.py` already says this.

**Moved into code comments:**
- `notify/mail.py`, beside `SUBJECT_LIMIT`: subjects are cut to 78 characters because the company mail relay folds longer subject headers, and some mail clients then show them garbled (MAIL-71). The 78 value matches the code.
- `notify/settings.py`, beside `MIN_HOURS_BETWEEN_DIGESTS`: the reason for the gap, that users on busy projects complained about digest floods in the 2025 survey (NOTIF-9). I kept the reason but not the 24-hour number. The survey may have been about the 24-hour gap, so please check that the reason still applies to 6 hours.

**Moved into documents (no code to sit beside):**
- `README.md`, new "Running" section: the digest job runs after the nightly notification cleanup, so a digest never includes notifications the cleanup removed. This ordering is set by a job outside this repository, and nothing in the code enforces it.
- `docs/oncall.md`, new "Mail-provider incidents" section: during a mail-provider incident, support pauses all sending from the provider's dashboard; ask in #mail-ops before pausing.

Files changed: `notify/settings.py`, `notify/mail.py`, `README.md`, `docs/oncall.md`, and this file, `RESPONSE.md`.
