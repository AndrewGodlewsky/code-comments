The notification batch size is now 250, up from 100. The provider accepts at most 500 notifications per call, so 250 stays within its limit.

Changes:
- `notify/config.py`: `BATCH_SIZE = 250`.
- `notify/batcher.py`: the module docstring now says batches of up to 250.
- `notify/sender.py`: the docstring figure is recomputed from 20 calls a second × 250 = 5,000 notifications a second (was 2,000).
- `docs/notifications.md`: now says the batcher sends up to 250 notifications per call.
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (1,000 / 250), not 10.
- `README.md`: now says two hundred and fifty at a time, not a hundred.

Tests: `python -m unittest` runs 3 tests and all pass. They read `BATCH_SIZE` from config, so they needed no changes.

Pre-existing drift, not caused by this change, left as written: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `notify/config.py` sets `FLUSH_INTERVAL_S = 30`. The "never held longer than a minute" claim still holds at 30 seconds. I did not change it because it was already false before this edit. Say if you want the doc corrected to 30 seconds.
