The order poller now checks the storefront every ten minutes instead of every five. The change is `POLL_INTERVAL_S = 600` in `orders/settings.py`, and the unit tests pass.

Because the interval is longer, I also updated the figures that depended on it:

- `docs/operations.md`: polling every 10 min, and new orders reach the queue at most ten minutes after the storefront lists them.
- `docs/fulfilment.md`: the average delay before an order appears on the packing screen is now five minutes, up from two and a half.
- `orders/poller.py` and `orders/queue.py` docstrings: "every ten minutes", and about 300 s average wait before queueing.

Two things stayed the same on purpose:

- The storefront caches order lists for 5 minutes. Ten-minute polling is still longer than that, so every poll gets a fresh list.
- Call volume drops to about 144 polls a day per API key, well inside the 10,000-call limit.

Expect new orders to show on the packing screen about five minutes later on average, and up to ten minutes later at worst. The packing team should know this before the change goes live.
