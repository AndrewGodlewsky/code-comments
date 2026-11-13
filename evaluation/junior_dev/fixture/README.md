# shopfront

A tiny order service used as the fixture for Junior-dev's headless runs. Customers place
orders through `POST /orders`; the service checks stock, charges the card through the
payment provider, and records the order. Orders are kept in `data/orders.json`.

Run it with `python -m src.app`. It needs no database. You will recieve an email receipt
when an order is placed.
