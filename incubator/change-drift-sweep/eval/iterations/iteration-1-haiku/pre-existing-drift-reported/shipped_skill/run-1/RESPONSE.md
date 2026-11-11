Raised the notification batch size from 100 to 250.

Changed:
- notify/config.py: BATCH_SIZE = 250, with a comment giving the reason (the provider bills per call, so larger batches cut the bill).
- notify/batcher.py: module docstring now says batches of up to 250.
- notify/sender.py: the throughput figure is now 5,000 notifications a second (20 calls a second x 250), up from 2,000.
- README.md and docs/notifications.md: now state 250 instead of 100.
- docs/billing.md: the example burst of 1,000 notifications is now 4 calls instead of 10.

250 is within the provider's documented limit of 500 notifications per call. The tests pass (python -m unittest, 3 tests).

Needs your decision: docs/notifications.md says a partial batch is flushed after 60 seconds, but notify/config.py sets FLUSH_INTERVAL_S = 30. This mismatch was already there and I did not change it. Tell me which value is correct and I will fix the wrong side.
