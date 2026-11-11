The notification batch size is now 250, up from 100. Each push provider call carries up to 250 notifications, so a burst of 1,000 notifications now costs 4 calls instead of 10.

Changes:
- `notify/config.py`: `BATCH_SIZE = 250`.
- `notify/batcher.py`: module docstring now says batches of up to 250.
- `README.md`: "a hundred at a time" is now "two hundred and fifty at a time".
- `docs/notifications.md`: now says the batcher sends up to 250 notifications per provider call.
- `docs/billing.md`: the 1,000-notification example now costs 4 calls.
- `notify/sender.py`: the derived throughput figure is now 5,000 notifications a second per app (20 calls a second times 250), up from 2,000.

Left unchanged, because the provider limits are outside facts and still hold: the 500-notifications-per-call cap (250 is under it) and the 20-calls-a-second limit per app.

Mismatch not caused by this change, reported only and not corrected: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `notify/config.py` sets `FLUSH_INTERVAL_S = 30`. One of the two is stale; someone who knows the intended interval should decide which to fix.
