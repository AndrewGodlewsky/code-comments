The order poller now checks the storefront every ten minutes. `POLL_INTERVAL_S` in `orders/settings.py` went from 300 to 600. I haven't run the tests, but they use that constant, so they should follow the change.

I also updated the text that was tied to the old interval:
- `orders/poller.py` docstring: "every ten minutes".
- `orders/queue.py` docstring: the average wait before an order is queued is now about 300 s, was 150 s.
- `docs/operations.md`: polls every 10 min, and a new order reaches the queue at most ten minutes after the storefront lists it.
- `docs/fulfilment.md`: an order now shows up on the packing screen about five minutes after the storefront lists it on average, was two and a half. Packers will see orders arrive later than before, so you may want to tell the fulfilment team.

I left the October 2026 incident notes alone, since they describe the 5-minute setup at the time.

Two things to check:
- Each poll still fetches at most 100 orders (`PAGE_LIMIT`), and each poll now covers a window twice as long. If the storefront gets busy, orders will wait for later polls more often. Raise the limit if that's a concern.
- Ten minutes is longer than the storefront's 5-minute cache, so polls will not return cached pages. Daily calls drop from about 288 to about 144, well under the 10,000 limit.
