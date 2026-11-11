I raised the notification batch size from 100 to 250.

Changes:
- `notify/config.py`: `BATCH_SIZE = 250`. The batcher reads this constant, so no logic changed.
- `notify/batcher.py`: the module docstring now says batches of up to 250.
- `docs/notifications.md`: now says the batcher sends up to 250 notifications per provider call.
- `README.md`: now says notifications go out 250 at a time.

250 is within the provider's limit of 500 notifications per call, so the change is safe. The unit tests pass (`python -m unittest`, 2 tests OK).

Pre-existing drift I found but did not change: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. Either the doc or the config is wrong, and I did not decide which. Tell me which value is intended and I will align them.
