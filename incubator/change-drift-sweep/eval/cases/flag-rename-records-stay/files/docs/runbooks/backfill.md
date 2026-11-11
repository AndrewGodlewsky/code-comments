# Runbook: backfill missed nightly exports

1. Find the first day with no file in the exports bucket.
2. From a checkout, call `app.backfill.backfill("orders.csv", first_missing_day, "out")`.
   For a single day, `reportctl export orders.csv --since 2026-05-01 --output out/orders-2026-05-01.csv` does the same.
3. Upload the files in `out/` and tell the data team in their channel.
