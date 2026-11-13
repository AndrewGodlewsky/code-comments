The order poller now checks for new orders every ten minutes (`POLL_INTERVAL_S` in `orders/settings.py` is 600, up from 300). The tests pass.

I also fixed the text that described the old five-minute timing:
- `orders/poller.py`: the module docstring now says every ten minutes.
- `orders/queue.py`: an order has now waited about 300 s on average when it is queued (was 150 s).
- `docs/operations.md`: polls every 10 min, and a new order reaches the queue at most ten minutes after the storefront lists it.
- `docs/fulfilment.md`: the packing team's average delay is now five minutes (was two and a half).
- `orders/settings.py`: a short note that the interval is ten minutes to keep load on the storefront API low, at their team's request.

Things to know:
- The packing team will see orders later, up to ten minutes and five on average. Tell them before this ships.
- I left the storefront's 5-minute cache note and the 2 October duplicate-order incident as written, because they are still true. Ten minutes is above the cache window, so every poll gets a fresh page. Order de-duplication is unchanged.
- At 144 polls a day the poller is well inside the 10,000-calls-a-day quota.
