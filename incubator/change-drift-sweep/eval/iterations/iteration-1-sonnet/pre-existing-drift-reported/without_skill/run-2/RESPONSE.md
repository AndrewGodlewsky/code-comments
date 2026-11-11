The notification batch size is now 250, so a busy period should cost fewer provider calls. The unit tests pass.

I changed `BATCH_SIZE` in `notify/config.py` from 100 to 250. 250 is under the provider's limit of 500 notifications per call.

I also updated the text that quoted the old number:
- `notify/batcher.py` docstring: batches of up to 250.
- `notify/sender.py` docstring: the per-app ceiling is now 5,000 notifications a second (20 calls a second x 250), up from 2,000.
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls, down from 10.
- `docs/notifications.md` and `README.md`: 250 per call.

One thing I did not change, because it was already wrong before this work and isn't part of your request. `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `FLUSH_INTERVAL_S` in `notify/config.py` is 30. The code sets the real behaviour, so the doc is likely the stale part. Do you want me to correct it to 30 seconds?

With larger batches, a partial batch will be more common at low traffic. Each one still costs a full call, so the saving is smaller when traffic is light.
