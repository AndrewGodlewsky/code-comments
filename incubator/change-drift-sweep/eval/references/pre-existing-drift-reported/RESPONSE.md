Raised `BATCH_SIZE` in `notify/config.py` from 100 to 250. Updated the batcher docstring,
the README and the first line of `docs/notifications.md`. 250 is within the provider's
limit of 500 notifications per call.

Two figures were worked out from the old size, so I recomputed them:
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls, not 10.
- the `notify/sender.py` docstring: at the provider's 20 calls a second, one app can now
  push at most 5,000 notifications a second, not 2,000.

One thing I found but did not change: `docs/notifications.md` says a partial batch is
flushed after 60 seconds ("never held longer than a minute"), but `FLUSH_INTERVAL_S` in
`notify/config.py` is 30. That mismatch was already there and isn't part of this change,
and I can't tell whether the doc or the code has the intended value. Which is right? I
can then fix the doc or the setting.

The tests pass.
