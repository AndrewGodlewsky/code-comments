The order poller now checks the storefront every ten minutes instead of every five. The change is `POLL_INTERVAL_S = 600` in `orders/settings.py`.

I also updated the text that described the old interval or figures computed from it:

- `orders/poller.py`: the module docstring now says "every ten minutes".
- `orders/queue.py`: the average wait before queueing was half the old interval (about 150 s), so it is now about 300 s.
- `docs/operations.md`: the poll cadence is now 10 min, and the worst-case delay from listing to queueing is now ten minutes.
- `docs/fulfilment.md`: the average delay before an order appears on the packing screen was two and a half minutes, which was half the old interval. It is now five minutes, half the new interval.

Left unchanged on purpose:

- The 2 October 2026 incident in `docs/operations.md` is a dated report, so its "every 5 minutes" and "5 minutes apart" stay as written.
- The storefront's 5-minute order-list cache is an outside fact. Polling every 10 minutes still does not hit the cache window, so nothing there is now wrong.
- The packer's five-minute confirmation window in `docs/fulfilment.md` is not derived from the poll interval.
- `tests/test_poller.py` reads the constant, so it needed no change. I did not run the tests.

Mismatch my change did not cause: `docs/operations.md` says the incident fix means "the poller now queues each order id once". The `seen` set in `run()` is local to a single call, so this only holds within one run. Duplicates can still be queued across restarts or separate runs. The documentation overstates the fix.
