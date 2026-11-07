# Return stock when an order is cancelled

Cancelled orders currently keep their units reserved forever. Add
`release(stock, sku, qty)` to `inventory.py`. It puts `qty` units of `sku` back
into `stock` and, like `reserve`, returns how many units of that SKU are in
stock afterwards. A SKU with no entry in `stock` yet starts from zero. Treat
bad quantities the way `reserve` does.

`reserve` should keep working as it does now.
