Raised the notification batch size from 100 to 250.

Changed:
- notify/config.py: BATCH_SIZE = 250. Added a line giving the reason (fewer billed calls, docs/billing.md) and the provider's 500-per-call limit, which 250 respects.
- notify/batcher.py: module docstring now says batches of up to 250.
- notify/sender.py: the rate-limit note said 2,000 notifications a second, which was 20 calls x 100. It now refers to BATCH_SIZE x 20, which is 5,000 at 250.
- README.md: "a hundred at a time" is now "250 at a time".
- docs/notifications.md: "up to 100" is now "up to 250".
- docs/billing.md: the example "1,000 notifications costs 10 calls" is now 4 calls at 250.

Tests: `python -m unittest` passes (3 tests).

Needs your decision: docs/notifications.md says a partial batch is flushed after 60 seconds, but notify/config.py has FLUSH_INTERVAL_S = 30. This mismatch was already there before this change and I did not touch it. Tell me whether 30 or 60 is the intended value and I will align the doc or the code.
