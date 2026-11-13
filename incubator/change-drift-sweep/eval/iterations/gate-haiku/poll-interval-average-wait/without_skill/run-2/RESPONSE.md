The order poller now checks the storefront every ten minutes instead of every five.

Changes:
- `orders/settings.py`: `POLL_INTERVAL_S` is now 600 (was 300). The poller reads this value, so no other code changed.
- `orders/poller.py`: the module docstring now says ten minutes.
- `README.md`: average pickup delay is now five minutes (half the poll interval), up from two and a half.
- `docs/operations.md`: the poll cadence is now every 10 minutes, and the worst-case delay before an order reaches the queue is now ten minutes (was five).

Left alone:
- The incident note from 2 October 2026 still describes the poller as it ran at the time (every 5 minutes). The queue-once fix it describes is unchanged.
- The storefront caches order lists for 5 minutes. A 10-minute poll is longer than that cache, so each poll gets fresh data and the duplicate-order problem from the incident does not come back.

Tests: `python -m unittest` passes (2 tests). The tests read the interval from settings, so they follow the new value.

Please note that the average and worst-case delays for new orders have doubled. If the fulfilment team relies on the five-minute worst case, they should know about it.
