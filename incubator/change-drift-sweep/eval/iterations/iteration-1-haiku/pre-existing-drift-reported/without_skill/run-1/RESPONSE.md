The notification batch size is now 250, down from 100. This cuts the number of provider calls by about 60%, and 250 stays under the provider's 500-notifications-per-call limit.

Changes:
- `notify/config.py`: `BATCH_SIZE = 250`. The batcher and tests read this constant, so no logic changed.
- Docs that stated the old number of 100 now say 250: the `notify/batcher.py` docstring, `README.md`, and `docs/notifications.md`.
- `docs/billing.md`: the example of a 1,000-notification burst now reads 4 calls instead of 10.

The unit tests pass (`python -m unittest`, 3 tests).

One thing I did not change: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. That mismatch was already there before this change. Tell me which value is correct and I will align the doc or the constant.
