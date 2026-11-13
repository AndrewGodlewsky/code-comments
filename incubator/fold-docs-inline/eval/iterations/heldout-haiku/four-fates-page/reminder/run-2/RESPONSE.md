I moved the contents of docs/digests.md and deleted the file. I checked each claim against the code first.

**Left out, because the code already shows it**
- `build_digest()` groups unread notifications by project.
- `due()` enforces the gap between digests.
- Subjects are cut to `SUBJECT_LIMIT`, and the limit is 78.

**Not carried over, because the code contradicts it**
- The page says `due()` holds a user's next digest until 24 hours after the last one. `MIN_HOURS_BETWEEN_DIGESTS` in `notify/settings.py` is 6. I left the 24-hour figure out. Either the page is stale or the setting is wrong, and you should decide which.

**Moved into code comments**
- `notify/settings.py`, beside `MIN_HOURS_BETWEEN_DIGESTS`: the 2025 survey complaint about digest floods (NOTIF-9). That reason was written for the 24-hour gap. Please confirm it still holds at 6 hours.
- `notify/mail.py`, beside `SUBJECT_LIMIT`: the mail relay folds long subject headers, which garbles some clients' display (MAIL-71).

**Moved into documents, because no code sits beside them**
- `README.md`, new "Scheduling" section: the digest job runs after the nightly notification cleanup. Nothing in this repository schedules that job or runs the cleanup, so I could not verify the ordering. It is unverified.
- `docs/oncall.md`, new "Mail-provider incidents" section: support pauses all sending from the provider's dashboard during an incident, and the on-call should ask in #mail-ops before pausing.

**Other notes**
- I did not change any code, only comments, and I created no new files.
- I deleted `docs/digests.md` because you said it is going away. Restore it from history if you wanted it kept until review.
- The 2025 survey and the MAIL-71 and NOTIF-9 tickets are cited as the page cites them. I did not check them.
