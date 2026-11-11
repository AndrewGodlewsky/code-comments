Raised the notification batch size from 100 to 250 in `notify/config.py` (`BATCH_SIZE = 250`). The batcher and sender read the constant, and `python -m unittest` passes (3 tests).

Because the old value was written in prose, I also updated the docs that stated it:

- `notify/batcher.py` docstring: "batches of up to 250".
- `README.md`: "two hundred and fifty at a time".
- `docs/notifications.md`: "up to 250 notifications in one provider call".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (1,000 / 250), down from 10.
- `notify/sender.py` docstring: the per-app ceiling is now 5,000 notifications a second (20 calls/s x 250), up from 2,000.

Kept as written: the provider's 500-per-call and 20-calls-a-second limits in `docs/notifications.md` and `notify/sender.py` are outside facts. 250 is under the 500 cap, so nothing breaks.

Pre-existing drift, not caused by this change, left unchanged: `docs/notifications.md` says a partial batch is flushed after 60 seconds and a notification is never held longer than a minute, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. The doc is wrong against the code today. I did not change either side; say if you want the doc corrected to 30 seconds.
