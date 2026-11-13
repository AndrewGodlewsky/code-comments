I removed `docs/digests.md` and moved its content to where it belongs.

Moved into code comments:
- `notify/digest.py` module docstring: the digest job runs after the nightly notification cleanup, so a digest never includes notifications the cleanup removed.
- `notify/digest.py` `due()` docstring: the next digest is held back until `MIN_HOURS_BETWEEN_DIGESTS` after the last one.
- `notify/digest.py` `build_digest()`: a short docstring saying it groups unread notifications by project.
- `notify/settings.py` above `MIN_HOURS_BETWEEN_DIGESTS`: the reason for the gap (digest floods reported in the 2025 survey, NOTIF-9).
- `notify/mail.py` above `SUBJECT_LIMIT`: the relay folds long subject headers and some clients show them garbled (MAIL-71).

Moved to `docs/oncall.md`, because it is an operational action rather than code behaviour:
- Mail-provider incidents: support pauses sending from the provider dashboard, and you should ask in #mail-ops before pausing.

Please check one discrepancy before this lands. The old doc said `due()` holds a digest back for 24 hours. The code uses `MIN_HOURS_BETWEEN_DIGESTS = 6`. I followed the code and wrote the comments to refer to the setting rather than a number. If 24 hours is the intended value, the setting needs changing, not just the comment.

Tests: `python -m unittest discover -s tests -t .` runs 3 tests, all passing. No other references to `digests.md` remain in the repo. I did not commit anything.
