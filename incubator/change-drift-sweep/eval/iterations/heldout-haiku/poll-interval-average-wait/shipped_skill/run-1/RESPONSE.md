The order poller now checks the storefront every ten minutes instead of every five. The change is `POLL_INTERVAL_S = 600` in `orders/settings.py`. The unit tests pass.

Effects to know about:
- Worst-case delay from storefront listing to the packing queue rises from five to ten minutes, and the average rises from about two and a half to five minutes. The packing team's doc (`docs/fulfilment.md`) and the poller's operations doc (`docs/operations.md`) now say so.
- Ten minutes stays above the storefront's five-minute order-list cache, so no poll is wasted on a cached page. I noted that constraint beside the setting.
- The comments in `orders/poller.py` and `orders/queue.py` now refer to the setting rather than a copied number. The queue comment's average wait is now half the poll interval.
- The 2 October 2026 incident entry still says five minutes. It records what the poller did at the time, so I left it as written.

Nothing in the request conflicts with a stated limit, and I did not find a reason for the change beyond the storefront team's request, so none is recorded in the code.
