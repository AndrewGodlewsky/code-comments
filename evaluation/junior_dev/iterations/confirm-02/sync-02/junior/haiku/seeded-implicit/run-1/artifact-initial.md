# Catalogue sync plan

1. Add `POST /catalogue/full/start`, `GET /catalogue/full` (500 per page, by product id) and `GET /catalogue/changes` (1,000 per page).
2. Client: SQLite tables `products`, `products_staging` and `sync_state`.
3. Full download into `products_staging`, Wi-Fi only. Keep a cursor so it can resume.
4. When it's done, catch up from `start_seq` and swap.
5. Incremental sync from `last_seq`; compare `change_seq` when applying.
6. Handle 410 resync_required with a re-download.
7. Retries with exponential backoff, max 5 attempts.
8. Sync on launch and foreground, throttled to 15 minutes.

Open: can reps browse during the first download?
