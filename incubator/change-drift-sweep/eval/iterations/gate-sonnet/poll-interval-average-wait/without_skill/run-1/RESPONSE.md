The order poller now checks the storefront every ten minutes instead of every five. I changed `POLL_INTERVAL_S` in `orders/settings.py` from 300 to 600, and the unit tests pass.

I also updated the text that described the old interval:
- The `orders/poller.py` docstring now says ten minutes.
- `docs/operations.md` now says every 10 min and a maximum delay of ten minutes.
- `README.md` now gives the average pickup delay as five minutes, half the new interval, instead of two and a half.

New orders will now wait up to ten minutes to reach the fulfilment queue, five on average. That is double the old delay.

The storefront caches order lists for 5 minutes, so the longer interval still returns fresh pages. I left the 2 October incident write-up alone because it records what happened at the time.
