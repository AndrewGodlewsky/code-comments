Batch size is now 250 (`notify/config.py`, `BATCH_SIZE`). I swept the prose for the old value and what follows from it.

Corrected, by file:
- `notify/config.py`: `BATCH_SIZE = 250`. The comment names no value, so it stays as is.
- `notify/batcher.py`: module docstring says "up to 250".
- `notify/sender.py`: the derived ceiling is 20 calls/s x 250 = 5,000 notifications a second per app (was 2,000).
- `docs/notifications.md`: "up to 250 notifications in one provider call".
- `docs/billing.md`: 1,000 notifications now cost 4 calls (1,000 / 250), not 10.
- `README.md`: "250 at a time" (was "a hundred").

Kept as written:
- `docs/notifications.md`: the provider limits of 500 notifications per call and 20 calls a second per app are outside facts. 250 is within the 500 cap, so nothing conflicts.
- `tests/test_batcher.py`: it uses `BATCH_SIZE`, so nothing to change.

Drift that was already there, not caused by this change:
- `docs/notifications.md` said a partial batch is flushed after 60 seconds. The code has `FLUSH_INTERVAL_S = 30`. I corrected the figure to 30 seconds, toward the code, and left the "never held longer than a minute" clause, which is still true.

Cost note: 250 a call cuts the call count for a burst by 2.5x. Each partial batch still costs one call.
