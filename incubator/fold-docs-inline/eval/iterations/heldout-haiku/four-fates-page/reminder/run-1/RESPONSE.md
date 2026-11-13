I moved the content of docs/digests.md out and deleted the file. No code changed, and no new files were created.

Moved into comments:
- notify/settings.py, beside MIN_HOURS_BETWEEN_DIGESTS: the 2025 survey complaint about digest floods (NOTIF-9).
- notify/mail.py, beside SUBJECT_LIMIT: the mail relay folding long subject headers and garbling them in some clients (MAIL-71).

Moved into documents:
- README.md, new "Timing" section: the digest job runs after the nightly notification cleanup. I could not verify this from the code, since nothing in this repo schedules the job or runs the cleanup. It is carried over as stated.
- docs/oncall.md, new "Mail-provider incidents" section: support pauses all sending from the provider's dashboard, and the team asks in #mail-ops before pausing.

Left out because the code already shows it:
- build_digest() groups unread notifications by project.
- Subjects are cut to SUBJECT_LIMIT (78) characters.

Not carried over because the code contradicts it:
- The docs said due() holds a user's next digest back until 24 hours after the last one. The code uses MIN_HOURS_BETWEEN_DIGESTS = 6, and due() compares against that value. I did not write 24 hours anywhere. The survey reason was written for a 24-hour gap, and I kept it beside the 6-hour setting without checking whether it still holds at 6 hours. Please confirm the value and the reason, and decide whether the survey still justifies the current gap.
