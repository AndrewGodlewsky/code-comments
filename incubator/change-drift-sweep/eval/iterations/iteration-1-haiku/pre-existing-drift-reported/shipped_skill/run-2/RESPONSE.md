Raised the notification batch size from 100 to 250 (`notify/config.py`, `BATCH_SIZE`). The provider accepts up to 500 notifications per call, so 250 stays within its limit.

Updated the places that stated the old numbers so they match the new behaviour:
- `notify/batcher.py` docstring: batches of up to 250.
- `docs/notifications.md`: up to 250 per provider call.
- `README.md`: sends 250 at a time.
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (was 10).
- `notify/sender.py`: the provider allows 20 calls a second per app, so one app can now push at most 5,000 notifications a second (was 2,000).

The config comment now notes that larger batches cut the per-call charge, taken from your request. The tests pass (`python -m unittest`, 3 tests OK).

Note: the 5,000 figure is 20 calls a second at 250 per call. The batcher does not rate-limit sends, so a burst could exceed the provider's 20-calls-a-second limit; that is unchanged by this edit.
