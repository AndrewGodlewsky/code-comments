docs/digests.md now keeps only what has no code to sit beside. Claim by claim:

- **The job runs after the nightly cleanup.** Kept on the page. It's about how two jobs are scheduled, and neither schedule is in this repository. You could also put it in the `notify/digest.py` module docstring; tell me if you'd prefer that.
- **`build_digest()` groups unread notifications by project.** Dropped: the function shows it.
- **`due()` holds the next digest for 24 hours, because of the digest-flood complaints (NOTIF-9).** Split. The NOTIF-9 reason moved to a comment in `due()` in notify/digest.py. The 24 hours did not move, and I took them off the page, because they're wrong: `due()` waits `MIN_HOURS_BETWEEN_DIGESTS`, which notify/settings.py sets to 6. I didn't change the setting. If 24 hours is what you want, say so and I'll change it.
- **Subjects are cut to 78 characters because the mail relay folds longer headers (MAIL-71).** Moved to a comment above `SUBJECT_LIMIT` in notify/mail.py.
- **Ask in #mail-ops before pausing sending during an incident.** Kept on the page: it's a support procedure.

AGENTS.md and docs/oncall.md are untouched. No code changed and I added no files.
