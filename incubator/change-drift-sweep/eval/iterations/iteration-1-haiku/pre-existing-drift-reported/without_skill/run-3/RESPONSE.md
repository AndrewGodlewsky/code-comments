Done. The notification batch size is now 250, up from 100.

Changes:
- notify/config.py: BATCH_SIZE = 250
- notify/batcher.py: module docstring now says batches of up to 250
- docs/notifications.md: "up to 250 notifications in one provider call"
- README.md: "sends them to the push provider 250 at a time"

250 is within the provider's limit of 500 notifications per call, so the change should not be rejected. Each full batch now costs one provider call per 250 notifications, down from one per 100. The existing tests pass (python -m unittest, 3 tests OK).

One pre-existing mismatch I did not change: docs/notifications.md says a partial batch is flushed after 60 seconds, but notify/config.py sets FLUSH_INTERVAL_S = 30. Let me know which value is intended and I will align the doc or the config.
