`send_alert` now makes six attempts instead of four, so a short gateway blip no longer drops the alert. The retry waits are 1, 2, 4, 8 and 16 s, so an alert is dropped about 31 s after the first try (it was about 7 s).

The change itself is `MAX_ATTEMPTS = 6` in `alerts/config.py`. `alerts/sender.py` picks it up without edits.

Prose that stated the old values, now corrected:
- `alerts/sender.py`: the module docstring says "six attempts"; the wait comment now lists 1, 2, 4, 8 and 16 s and "about 31 s".
- `alerts/worker.py`: the backlog figure was derived from the old 7 s per alert (40 × 7 s = 280 s, "under five minutes"). At 31 s per alert it is 40 × 31 s = 1240 s, so it now reads "about 21 minutes". Under the old figure the sentence was true; under the new one it was not.
- `docs/oncall.md`: "about thirty-one seconds" after the alert was raised (was "seven seconds"); a storm of 50 alerts now sends at most 300 POSTs (50 × 6), not 200.
- `docs/runbooks/gateway-maintenance.md`: the sender retries each alert five times, not three (six attempts is one try plus five retries).

Kept as written:
- No changelog, ADR, dated report or migration note in the repository states the old values, so no record needed a decision.
- `OUTBOX_RETENTION_DAYS` and "7 days" in `docs/oncall.md` (outbox purge) are unrelated to the retry count and unchanged.
- `README.md` states no retry values.
- No instruction files (AGENTS.md, CLAUDE.md) in this repository.

Drift this change did not cause: none found. The re-sweep finds no remaining prose with the old attempt count or old totals; the one leftover "4" is the wait of 4 s, which did not change.

Verification: `python -m unittest` runs 5 tests and all pass. The tests read `MAX_ATTEMPTS` symbolically, so they check six attempts and five waits without edits.

I did not use git and did not commit.
