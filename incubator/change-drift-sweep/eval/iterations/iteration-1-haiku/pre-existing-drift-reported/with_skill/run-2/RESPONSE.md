The notification batch size is now 250, up from 100, so each push provider call carries up to 250 notifications. That is within the provider's 500-per-call limit. The unit tests pass.

Prose I corrected to match:
- `notify/config.py`: `BATCH_SIZE = 250`.
- `notify/batcher.py` (module docstring): "batches of up to 250".
- `docs/notifications.md`: "sends up to 250 notifications in one provider call".
- `README.md`: "two hundred and fifty at a time".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (1000 / 250), not 10.
- `notify/sender.py` (module docstring): the provider allows 20 calls a second per app, so one app can push at most 5,000 notifications a second (20 × 250), not 2,000. This assumes each call carries a full batch.

Not changed, because the request was only about batch size:
- `docs/notifications.md` says a partial batch is flushed after 60 seconds, and "never held longer than a minute". `notify/config.py` sets `FLUSH_INTERVAL_S = 30`. This drift was already there before my change. The doc and the code disagree (60 s in the doc, 30 s in the code). Which one is right is your call. I left both as they were.

Left as is:
- The provider's 500-notifications-per-call limit in `docs/notifications.md` is an outside fact, and 250 is under it.
- The 1,000-notification burst in `docs/billing.md` is an example count, not a batch-size figure.
