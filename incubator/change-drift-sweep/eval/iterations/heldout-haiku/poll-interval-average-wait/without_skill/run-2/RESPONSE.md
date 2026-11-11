The order poller now checks the storefront every ten minutes instead of every five. The change is `POLL_INTERVAL_S = 600` in `orders/settings.py`, and the unit tests pass.

I also updated the docs that quoted the old timing:
- `docs/operations.md`: the poll interval is now 10 min, and the worst-case delay before an order reaches the queue is now ten minutes.
- `docs/fulfilment.md`: the average delay before an order appears on the packing screen is now five minutes, up from two and a half.
- `orders/poller.py`: the module docstring says ten minutes.

Two things to be aware of:
- The storefront caches order lists for 5 minutes, and ten-minute polls are still longer than that, so the duplicate-order fix from the October incident still holds.
- Polling less often also means fewer storefront calls, which helps with the 10,000-calls-a-day limit.
