The order poller now checks for new orders every ten minutes (`POLL_INTERVAL_S` in `orders/settings.py` went from 300 to 600). I did not run the tests.

I also updated the text that described the old interval or figures computed from it:
- `orders/poller.py`: the module docstring now says "every ten minutes".
- `orders/queue.py`: the average wait before an order is queued is now about 300 s, up from 150 s.
- `docs/operations.md`: the poll interval is now 10 min, and the worst-case delay before an order reaches the queue is now ten minutes.
- `docs/fulfilment.md`: the average delay before an order shows up on the packing screen is now five minutes, up from two and a half.

I left these alone on purpose:
- The 2 October 2026 incident entry in `docs/operations.md`, which is a dated record of the old five-minute polling.
- The line saying the storefront API caches order lists for 5 minutes. That is a fact about the storefront, not our setting. Ten-minute polling is longer than the cache window, so each poll should get a fresh page.
- The five-minute packer confirmation window in `docs/fulfilment.md`, which has nothing to do with polling.

I found no existing mismatches that my change didn't cause.
