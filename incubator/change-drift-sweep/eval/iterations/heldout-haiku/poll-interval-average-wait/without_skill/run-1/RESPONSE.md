The order poller now checks the storefront every ten minutes, down from five. The change is `POLL_INTERVAL_S = 600` in `orders/settings.py`. The unit tests pass (`python -m unittest`, 3 tests).

Because the interval is doubled, the timing figures change too, so I updated the docs and comments that stated them:

- `docs/operations.md`: polling every 10 min, and a new order reaches the queue at most ten minutes after the storefront lists it (was five).
- `docs/fulfilment.md`: an order appears on the packing screen on average five minutes after it is listed (was two and a half). The packer's five-minute confirmation window is unchanged.
- `orders/poller.py` docstring and `orders/queue.py` docstring: updated to ten minutes and about 300 s average wait (was five minutes and about 150 s).

Two things to be aware of for the storefront team:

- Each poll still fetches at most 100 orders, so a busy window now waits up to ten minutes for the next poll rather than five. If order volume can exceed 100 per ten-minute window, some orders will be delayed more than before.
- Ten minutes is longer than the storefront's 5-minute order-list cache, so each poll now returns fresh data. The duplicate-order protection (queueing each order id once) is unaffected.
