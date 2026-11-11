The order poller now checks the storefront every ten minutes instead of every five. This halves our calls to their API.

What changed:
- `orders/settings.py`: `POLL_INTERVAL_S` went from 300 to 600. Nothing else in the code needed to change, and the tests read this setting.
- `orders/poller.py`: the docstring now says ten minutes.
- `docs/operations.md`: the poll frequency and the worst-case delay now say ten minutes.
- `docs/fulfilment.md`: the average delay before an order shows on the packing screen is now five minutes (half the interval), up from two and a half. Packers will notice orders appearing later.

I left some things alone on purpose. The storefront's 5-minute cache note and the 2 October incident record are historical or external facts, and the packer's 5-minute confirm window is unrelated to polling.

One thing to be aware of: each poll fetches at most 100 orders, so a ten-minute window now covers twice the time. If a window ever has more than 100 new orders, the rest wait for the next poll. If you expect busy periods like that, we may want to raise `PAGE_LIMIT`.

I did not run the tests.
