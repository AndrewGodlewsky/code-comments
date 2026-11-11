The notification batch size is now 250, up from 100. This is set in `notify/config.py` (`BATCH_SIZE = 250`). Fewer, fuller provider calls should cut the per-call charge.

I updated the text that stated the old figure or a number derived from it:

- `notify/batcher.py` module docstring: "batches of up to 250".
- `notify/sender.py` module docstring: the throughput bound is now 20 calls/s × 250 = 5,000 notifications a second (was 2,000).
- `README.md`: "two hundred and fifty at a time" (was "a hundred at a time").
- `docs/notifications.md`: "sends up to 250 notifications in one provider call".
- `docs/billing.md`: a burst of 1,000 notifications now costs 4 calls (was 10).

The provider's documented limit of 500 notifications per call still holds, since 250 is within it. The test suite passes (`python -m unittest`, 3 tests). The tests use `BATCH_SIZE` symbolically, so they needed no changes.

Mismatch not caused by this change, left as is:

- `docs/notifications.md` says a partial batch is flushed after 60 seconds, but `notify/config.py` sets `FLUSH_INTERVAL_S = 30`. One of the two is out of date, and I did not decide which. The doc's "never held longer than a minute" claim follows the doc's 60 seconds, not the code's 30.

Left unchanged on purpose: the provider's 500-per-call and 20-calls-per-second figures, which are outside facts.
