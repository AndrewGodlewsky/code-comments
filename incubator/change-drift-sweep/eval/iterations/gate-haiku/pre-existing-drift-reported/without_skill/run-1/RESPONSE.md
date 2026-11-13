Done. The notification batch size is now 250, up from 100.

Changes:
- `notify/config.py`: `BATCH_SIZE = 250`. The batcher reads this constant, so no logic changed.
- `notify/batcher.py`: module docstring now says batches of up to 250.
- `docs/notifications.md`: now says the batcher sends up to 250 notifications per call.
- `README.md`: now says 250 notifications at a time.

Tests: `python -m unittest` passes (2 tests). The tests use the `BATCH_SIZE` constant, so they follow the new value.

The push provider accepts up to 500 notifications per call, so 250 is within its limit. It also allows 20 calls a second per app, which this change does not affect.

One existing mismatch I did not change: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. Tell me which value is intended and I will align the code or the docs.
