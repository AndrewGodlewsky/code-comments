send_alert now makes six attempts (`MAX_ATTEMPTS = 6` in `alerts/config.py`). The waits are 1, 2, 4, 8 and 16 s, so a dropped alert is dropped about 31 s after the first try, up from 7 s.

I swept all the code comments and docs for the old value (four attempts, three retries, 7 s) and for figures derived from it. Corrected:

- `alerts/sender.py`: the docstring now says "at most six attempts". The wait comment now lists 1, 2, 4, 8 and 16 s and says about 31 s.
- `alerts/worker.py`: the docstring said a backlog of 40 alerts clears in under five minutes. Each dropped alert now holds the worker for 31 s, so 40 x 31 = 1240 s, about 20.7 minutes. It now says "under 21 minutes".
- `docs/oncall.md`: "about seven seconds" is now "about 31 seconds". The storm figure was 50 alerts x 4 = 200 POSTs; it is now 50 x 6 = 300.
- `docs/runbooks/gateway-maintenance.md`: "retries each alert three times" is now "five times". This is a living description of how the sender behaves, not a dated record, so I corrected it.

Kept as written:

- `OUTBOX_RETENTION_DAYS = 7` in `alerts/config.py` and "7 days" in `docs/oncall.md`. These are about outbox retention, not the retry wait.
- There are no records, outside facts, ADRs, instruction-file lines or changelog in this repository, so none needed keeping or changing.

Drift that predates my change: none found.

I did not run the tests. The existing tests use `MAX_ATTEMPTS` and `BASE_DELAY_S` rather than literals, so they should adapt.

One thing to be aware of. During a full outage the worker is now blocked about 31 s per alert, so a backlog drains much more slowly than before, and the alerts behind it wait longer.
