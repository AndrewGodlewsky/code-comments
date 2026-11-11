The order poller now checks the storefront every ten minutes instead of every five. The change is `POLL_INTERVAL_S` in `orders/settings.py`, from 300 to 600 seconds. The unit tests pass (`python -m unittest`, 3 tests).

Because the poll interval changed, I also updated the docs and comments that stated the old timing:

- `orders/poller.py`: the module docstring now says the poller checks every ten minutes.
- `orders/queue.py`: an order now waits about 300 s on average before it is queued (half the new interval), up from about 150 s.
- `docs/operations.md`: the poll cadence is now every 10 min, and a new order reaches the queue at most ten minutes after the storefront lists it.
- `docs/fulfilment.md`: an order now shows up on average five minutes after the storefront lists it, up from two and a half minutes.

Kept as written:

- `docs/operations.md`, "2 October 2026: duplicate orders" section. It is an incident record that was true at the time.
- `docs/operations.md`, "The storefront API caches order lists for 5 minutes". This is an outside fact about the storefront, not our poller.
- `docs/fulfilment.md`, "A packer has five minutes to confirm a picked order". It is unrelated to the poll interval.

Worth a check: the storefront caches order lists for 5 minutes and the poller now polls every 10 minutes, so each poll gets fresh data. The duplicate-order fix (tracking order ids) still covers any overlap. Nothing else in the repository states the old value.
