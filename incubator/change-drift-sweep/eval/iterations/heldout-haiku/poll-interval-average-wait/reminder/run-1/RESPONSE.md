The order poller now checks the storefront every ten minutes instead of every five.

Changes:
- `orders/settings.py`: `POLL_INTERVAL_S` is now 600 (was 300).
- `orders/poller.py`: the module docstring says ten minutes.
- `orders/queue.py`: the average wait before queueing is now about 300 s (half the interval). It was about 150 s.
- `docs/fulfilment.md`: the average delay before an order shows on the packing screen is now five minutes (was two and a half).
- `docs/operations.md`: the poll cadence is now every 10 min, and the at-most delay is now ten minutes (was five).

Left unchanged on purpose:
- The 2 October 2026 incident entry in `docs/operations.md` still says the poller ran every 5 minutes. That is a dated record of what was true then.
- The storefront's 5-minute order-list cache and its 10,000-calls-a-day limit are outside facts. Polling every 10 minutes is still slower than the cache, so the cache note stays accurate.
- The packer's five-minute confirmation window in `docs/fulfilment.md` is not derived from the poll interval.

Mismatches not caused by this change: none found. The unit tests (`python -m unittest`) pass with the new value. They read the constant, so they needed no edits.
