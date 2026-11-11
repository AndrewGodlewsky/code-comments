I moved the parts of `docs/digests.md` that belong next to the code into comments, and the rest into `docs/oncall.md`. I did not delete `docs/digests.md`. The tests pass.

**Now in comments**
- `notify/mail.py`: a comment on `SUBJECT_LIMIT` explains why subjects are cut to 78 characters. The mail relay folds longer subject headers and some clients then garble them (MAIL-71).
- `notify/digest.py`, `due()`: the docstring gives the reason for the gap between digests, which is the digest-flood complaints in the 2025 survey (NOTIF-9).
- `notify/digest.py`, module docstring: it now says the digest job runs after the nightly cleanup, so digests never include cleaned-up notifications. The job itself is not in this package, so I could not attach this to code. I noted that in the docstring.
- `notify/digest.py`, `build_digest()`: a one-line docstring saying it groups unread notifications by project.

**Moved to `docs/oncall.md`**
- The note that support pauses all sending from the provider's dashboard during a mail-provider incident, and to ask in #mail-ops first. This is an operational runbook step with no code to sit next to, so it fits the on-call doc. It now has its own "Mail-provider incident" section there.

**Please check: the doc and the code disagree**
- `docs/digests.md` says a digest is held back for 24 hours. The code, `MIN_HOURS_BETWEEN_DIGESTS` in `notify/settings.py`, is 6. I did not copy the 24 anywhere, and the comments carry only the reason for the gap. Either the doc was out of date or the setting changed by mistake.

Nothing else in the repo pointed at `docs/digests.md`, so removing it should not leave a dangling link.
