The order poller now checks every ten minutes: `POLL_INTERVAL_S` in `orders/settings.py` went from 300 to 600. I haven't run the tests.

I also corrected the comments and docs that still described the five-minute interval or figures computed from it:
- `orders/poller.py`: the docstring now says "every ten minutes".
- `docs/operations.md`: "every 10 min", and a new order reaches the queue "at most ten minutes" after the storefront lists it.
- `orders/queue.py`: the average wait before queueing is now about 300 s (was 150 s).
- `docs/fulfilment.md`: the average delay is now five minutes (was two and a half).

I left these unchanged on purpose:
- The 2 October 2026 incident entry in `docs/operations.md` still says the poller ran every 5 minutes. That was the interval at the time, and the entry is a dated record.
- The storefront's 5-minute cache is an outside fact. At ten minutes the poller now polls less often than the cache refreshes, so each poll should get fresh data.
- The packer's five-minute confirmation window in `docs/fulfilment.md` is unrelated to the poll interval.
- The 100-order page limit and the 10,000 calls a day limit are unaffected. A 100-order page now covers a ten-minute window instead of a five-minute one, so a busy period may need more than one poll to clear.

I found no existing mismatches that my change didn't cause.
