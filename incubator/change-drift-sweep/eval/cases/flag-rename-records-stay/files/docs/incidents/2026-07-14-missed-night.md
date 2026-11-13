# Incident: missed nightly export, 14 July 2026

- The nightly job failed at 02:10 while the warehouse was offline for maintenance.
- At 09:30 we exported the missed day by hand: `reportctl export orders.csv --since 2026-07-13 --output out/orders-2026-07-13.csv`.
- The data team had the file by 10:00, and no rows were lost.
