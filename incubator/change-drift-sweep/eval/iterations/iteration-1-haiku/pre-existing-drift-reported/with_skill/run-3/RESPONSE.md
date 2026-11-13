Notification batch size is now 250, up from 100. Since each provider call is billed, this means fewer calls for the same notifications.

Changed:
- notify/config.py: `BATCH_SIZE = 250`.
- notify/batcher.py: docstring now says batches of up to 250.
- docs/notifications.md: "sends up to 250 notifications in one provider call".
- README.md: "two hundred and fifty at a time".
- docs/billing.md: the 1,000-notification example now costs 4 calls, not 10 (1000 // 250 = 4). Each partial batch still costs one more.
- notify/sender.py: the ceiling is now 5,000 notifications a second, not 2,000 (20 calls/s x 250 per call). The 500-per-call provider limit still holds at 250.

Tests: `python -m unittest` passes (3 tests). The batch-size tests read the constant, so they follow the change.

Not changed, but please check: docs/notifications.md says a partial batch is flushed after 60 seconds, but notify/config.py sets `FLUSH_INTERVAL_S = 30`. This mismatch was already there before this change. I left it alone because it is outside the batch-size request. The fix is either to change the doc to 30 seconds or the config to 60.
