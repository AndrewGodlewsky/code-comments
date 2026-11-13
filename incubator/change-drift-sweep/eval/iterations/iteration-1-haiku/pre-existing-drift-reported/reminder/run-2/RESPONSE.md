Raised the notification batch size from 100 to 250 in `notify/config.py` (`BATCH_SIZE = 250`), so each push provider call now carries up to 250 notifications.

Updated the figures and comments that the change made stale:
- `notify/batcher.py` docstring: "batches of up to 250".
- `README.md`: now says the batches go to the provider "250 at a time".
- `docs/notifications.md`: "sends up to 250 notifications in one provider call".
- `notify/sender.py` docstring: 20 calls a second per app now allows 5,000 notifications a second (was 2,000, which was 20 x 100).
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (was 10).

Left unchanged: the provider limit of 500 notifications per call still holds, since 250 is under it.

Tests: `python -m unittest` passes (3 tests).

Mismatch not caused by this change, left as is: `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `notify/config.py` sets `FLUSH_INTERVAL_S = 30`. One of the two needs correcting; I did not pick which.
