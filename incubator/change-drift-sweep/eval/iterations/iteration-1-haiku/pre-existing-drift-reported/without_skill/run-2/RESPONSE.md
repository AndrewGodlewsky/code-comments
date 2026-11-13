I raised the notification batch size from 100 to 250 by changing `BATCH_SIZE` in `notify/config.py`. The batcher now sends a full batch once it holds 250 notifications, so each provider call carries 250 instead of 100. The push provider accepts up to 500 notifications per call, so 250 is within its limit.

I also updated the places that stated the old number so they match:
- `notify/batcher.py` docstring: "batches of up to 250"
- `docs/notifications.md`: "sends up to 250 notifications in one provider call"
- `README.md`: "250 at a time"
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls, down from 10

The partial-batch flush interval is unchanged. I did not run the test suite.

One existing mismatch I did not fix: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. The code value is what the batcher uses, so the doc is probably wrong, but please confirm which value you want before I change either one.
