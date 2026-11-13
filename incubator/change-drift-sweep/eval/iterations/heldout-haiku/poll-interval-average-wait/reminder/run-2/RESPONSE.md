The order poller now checks the storefront every ten minutes instead of every five. `POLL_INTERVAL_S` in `orders/settings.py` changed from 300 to 600. The tests pass (`python -m unittest`, 3 tests).

I also updated the text that described the old interval:

- `orders/poller.py`: the module docstring now says "every ten minutes".
- `orders/queue.py`: the average wait before queueing was half a poll interval, so it went from about 150 s to about 300 s.
- `docs/fulfilment.md`: the average delay before an order shows on the packing screen went from two and a half minutes to five minutes.
- `docs/operations.md`: the poll cadence is now every 10 min, and the upper bound on delay is now ten minutes after the storefront lists an order.

I left these unchanged:

- The storefront's 5-minute order-list cache note in `docs/operations.md`. It is an outside fact, and a 10-minute poll still stays above it.
- The 2 October 2026 incident in `docs/operations.md`. It is a dated record of the 5-minute poller at that time.
- The "five minutes to confirm a picked order" line in `docs/fulfilment.md`. It is a packer timeout and does not depend on the poll interval.
- `PAGE_LIMIT` and the 10,000-calls-a-day storefront limit. Neither depends on the poll interval.

I found no mismatches that my change did not cause. The tests use `POLL_INTERVAL_S` by name, so they needed no edit.
