Batch size is now 250 (was 100), so each provider call carries 2.5x as many notifications.

Changed:
- `notify/config.py`: `BATCH_SIZE = 250`
- `notify/batcher.py`: module docstring now says "up to 250"
- `docs/notifications.md`: "up to 250 notifications in one provider call"
- `README.md`: "250 at a time" (was "a hundred at a time")

250 is under the provider's documented limit of 500 notifications per call. The tests use `BATCH_SIZE` rather than a hard-coded number, and they pass.

One thing I did not change: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. This mismatch was already there and is unrelated to batch size. I don't know which is intended, so I left both alone. Tell me which is right and I'll fix the other.

A larger batch also takes longer to fill. On quiet traffic more notifications will wait for the flush interval instead of going out as a full batch.
