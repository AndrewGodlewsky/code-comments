The order poller now checks the storefront every ten minutes instead of every five.

Changed: `POLL_INTERVAL_S` in `orders/settings.py` is now 600, and its comment records the storefront team's request.

Comments and docs updated because they stated the old timing:
- `orders/poller.py` docstring: "every five minutes" is now "every ten minutes".
- `orders/queue.py`: the average wait before queueing is now about 300 s (half the interval), was about 150 s.
- `docs/fulfilment.md`: the average delay before an order reaches packers is now five minutes, was two and a half.
- `docs/operations.md`: polling is every 10 min and an order reaches the queue at most ten minutes after it is listed, was 5 and five.

Left as written: the 2 October 2026 incident entry in `docs/operations.md` says the poller ran every 5 minutes at the time, which is still true as history.

Checks: the new 10-minute interval stays above the storefront's 5-minute order-list cache, so it does not return stale pages. It also cuts the call rate to about 144 a day, well under the 10,000 daily limit. Tests pass (`python -I -m unittest`, 3 tests).

No conflicts with stated limits were found, and no reason was missing from the request.
