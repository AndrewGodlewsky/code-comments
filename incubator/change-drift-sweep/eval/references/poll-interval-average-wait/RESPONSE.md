The poller now checks every ten minutes: `POLL_INTERVAL_S` in `orders/settings.py` is 600 seconds.

Updated the poller docstring and `docs/operations.md` (the interval, and the longest time a new order
can take to reach the queue, now ten minutes). Two places gave the average wait, which is half the
time between polls: `docs/fulfilment.md` said two and a half minutes and the `orders/queue.py`
docstring said about 150 s. With ten-minute polls that is five minutes (300 s), so I changed the
figures and kept the rest of each sentence.

Left as written:
- The storefront's own limits, its 5-minute cache and 10,000 calls a day. Ten-minute polling sits
  within both.
- The packers' five minutes to confirm a picked order, which has nothing to do with polling.
- The 2 October 2026 incident in `docs/operations.md`, which describes the poller as it was then.

The tests pass.
