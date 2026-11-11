The order poller now checks for new orders every ten minutes. I changed `POLL_INTERVAL_S` in `orders/settings.py` from 300 to 600. The poller's behaviour follows that constant, and the unit tests pass (`python -m unittest`, 3 tests OK).

Because the interval changed, I also updated the prose that stated the old value:

- `orders/poller.py`: the module docstring now says the poller checks every ten minutes.
- `orders/queue.py`: an order waits about half a poll interval on average before it is queued, so the figure goes from about 150 s to about 300 s.
- `docs/operations.md`: the poll schedule is now every 10 min, and the worst-case delay from listing to the fulfilment queue is now ten minutes.
- `docs/fulfilment.md`: the average delay from listing to appearing on the packing screen is now five minutes (was two and a half minutes).

Kept as written:

- `docs/operations.md` "caches order lists for 5 minutes": a storefront fact about its cache, not our poll interval. The new 10-minute interval still stays above it.
- `docs/operations.md` 2 October 2026 incident (lines 16-17): a dated record of the 5-minute poller at the time.
- `docs/fulfilment.md` "A packer has five minutes to confirm": an unrelated packing timeout.

Nothing in the storefront's documented limits is affected. The 10,000 calls a day per key is still well above the roughly 144 polls a day at this interval.

No other drift found. I did not use git or commit anything.
