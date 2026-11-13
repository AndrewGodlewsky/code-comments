# Order poller

The poller asks the storefront for new orders every 5 min.
A new order reaches the fulfilment queue at most five minutes after the storefront lists it.
Each poll fetches at most 100 orders; a busier window waits for the next poll.

## Storefront limits

The storefront API caches order lists for 5 minutes, so polling more often than that returns the same page.
The storefront allows 10,000 calls a day per API key.

## Past incidents

### 2 October 2026: duplicate orders

- At the time, the poller ran every 5 minutes and did not track order ids.
- Two polls 5 minutes apart both returned order 88123 from the storefront's cache, and it was packed twice.
- Fix: the poller now queues each order id once (see `orders/poller.py`).
