Done: the notification batch size is now 250 (was 100). A full batch is 250 notifications per provider call, which is under the provider's 500-per-call limit.

Changed:
- `notify/config.py`: `BATCH_SIZE = 250`
- `notify/batcher.py`: module docstring said "up to 100"; now 250
- `notify/sender.py`: docstring said one app could push at most 2,000 notifications a second; now 5,000 (20 calls/s x 250)
- `docs/notifications.md` and `README.md`: "100" / "a hundred" now 250
- `docs/billing.md`: example burst of 1,000 notifications now costs 4 calls (was 10)

Tests pass.

One thing I did not change: the flush timeout is out of sync with the docs. `FLUSH_INTERVAL_S` in `notify/config.py` is 30 seconds, but `docs/notifications.md` says a partial batch is flushed after 60 seconds. This was already the case before my change and is unrelated to batch size. I left both as they were because I can't tell which one is right. Please tell me which value you want and I'll align the other. Also note that a longer batch means partial batches are the main remaining per-call cost, and the flush interval controls how many of those you pay for.
