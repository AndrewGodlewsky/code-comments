## Nightly orders ETL

Scheduled at 02:00 UTC. Copies `orders` from the app replica to the warehouse.

```mermaid
flowchart LR
  scheduler[Scheduler] --> extract[Extract]
  extract --> staging[stg_orders]
  staging --> merge[Merge]
  merge --> fact[fact_orders]
  watermark[(etl_watermark)]
  runs[(etl_runs)]
  recon[Sunday reconciliation]
  deadline["06:00 check"]
  alerts[Alerts]
```

- Incremental on `updated_at`, with a 2h lookback for late rows.
- Merge on `order_id`, latest version wins.
- Soft deletes become `is_deleted`.
- Retries on failure, then pages.
- Reconciliation covers the last 30 days.
- Deadline check at 06:00.
