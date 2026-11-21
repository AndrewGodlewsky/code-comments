## Nightly orders ETL into the warehouse

We need a nightly job that copies the app's `orders` table into the analytics warehouse. It also has to keep the warehouse copy correct when rows show up late or change after we've already exported them.

**Fixed requirements and constraints**

- The scheduler starts the job at 02:00 UTC. Read only from the app's Postgres read replica. We have no write access to the app database, so all pipeline bookkeeping lives in the warehouse.
- Every write to an order sets `updated_at` to the write time. The app never hard-deletes. It sets `deleted_at`, which is also a write. Deleted orders must stay in the warehouse, flagged `is_deleted`.
- Bulk-import transactions in the app can stay open for up to 90 minutes, and `updated_at` is stamped when the row is written, not when the transaction commits. So a bulk-imported row can become visible up to 90 minutes after its `updated_at`. To cover this, each night extracts rows whose `updated_at` is later than the last successful high-water mark minus a 2-hour lookback.
- Because of that overlap, the same order will be extracted more than once. The warehouse must hold exactly one row per `order_id`, always its most recent version, and re-running a night must do no harm.
- The high-water mark advances only once the night's data has loaded successfully.
- If a run fails, retry it up to two more times, 15 minutes apart. After the third failed attempt, page on-call.
- Analyst dashboards refresh from the warehouse at 06:00 UTC whether or not we've finished. They must never see a half-loaded night. If the night's load hasn't committed by 06:00, post a staleness alert to #data-alerts.
- Even so, some rows become visible later than the lookback covers, for example when the replica falls behind. A reconciliation handles them every Sunday, after that night's load. For each order-creation day in the last 30 days, it compares the row count and a checksum of `order_id` + `updated_at` between the replica and the warehouse, and reloads any day that doesn't match.

**What I want**

A Mermaid flowchart of the pipeline, with short notes before or after it. Make clear what starts each step, what data moves where, where the pipeline's state lives, and what happens on failure and retry. You decide the merge logic, the staging, and how the high-water mark is stored and updated, but spell them out.
