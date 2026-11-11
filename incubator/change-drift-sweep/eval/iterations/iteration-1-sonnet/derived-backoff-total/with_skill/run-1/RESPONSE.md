send_alert now makes up to six attempts (`MAX_ATTEMPTS = 6` in `alerts/config.py`). The waits are 1, 2, 4, 8 and 16 s, so an alert is dropped about 31 s after the first try (it was 7 s). Tests pass.

**Corrected (prose that still stated the old values)**
- `alerts/sender.py`: the docstring "at most four attempts" is now six. The wait comment is now "1, 2, 4, 8 and 16 s ... about 31 s" (it said 1, 2, 4 and 7 s).
- `alerts/worker.py`: the docstring said a 40-alert backlog takes "under five minutes" (40 x 7 s = 280 s). It now says "about 21 minutes" (40 x 31 s = 1240 s).
- `docs/oncall.md`: "about seven seconds" is now "about 31 seconds". "50 alerts sends at most 200 POSTs" is now 300 (50 x 6).
- `docs/runbooks/gateway-maintenance.md`: "retries each alert three times" is now "five times" (five retries after the first try).

**Kept**
- `OUTBOX_RETENTION_DAYS = 7` in `alerts/config.py` and "7 days" in `docs/oncall.md`: outbox retention, unrelated to the retry count.
- No changelog, ADR or instruction file mentions the old values.

**Not caused by this change**
- None found.

**Heads-up**
- Each alert now holds the worker for up to 31 s in an outage, so the 40-alert backlog takes about 21 minutes. Check that this is acceptable for draining the outbox.
