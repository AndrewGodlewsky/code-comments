# Nightly orders ETL into the warehouse: pipeline plan

## Diagram

```mermaid
flowchart TD
    subgraph TRIG["What starts each step"]
        T_NIGHT(["Scheduler, 02:00 UTC nightly"])
        T_RETRY(["Retry timer, 15 min after a failed attempt"])
        T_WATCH(["Watchdog, 06:00 UTC, separate scheduled job"])
        T_SUN(["Sunday, after that night's load commits"])
    end

    subgraph REPLICA["App Postgres read replica, read only"]
        R_ORD[("orders")]
    end

    subgraph WH["Warehouse: all pipeline state and the data"]
        W_WM[("etl_watermark: hwm, last committed run, committed_at")]
        W_LOG[("etl_run_log: one row per attempt, status, error")]
        W_STG[("stg_orders_RUN_ID: run-scoped staging, dropped after the attempt")]
        W_CUR[("orders_current: one row per order_id, with is_deleted")]
        W_VIEW["Dashboard views over orders_current"]
    end

    subgraph RUN["Nightly load, one attempt"]
        A1["1. Take pipeline lock, log attempt as running"]
        A2["2. Read hwm from etl_watermark"]
        A3["3. Read cutoff from replica (pg_last_xact_replay_timestamp)"]
        A4["4. Extract orders with updated_at after hwm minus 2h and up to cutoff"]
        A5["5. Bulk load extract into staging"]
        A6["6. Validate: keys and updated_at not null, staged count equals extracted count"]
        A7["7. Keep newest row per order_id"]
        A8["8. MERGE into orders_current: update only if incoming updated_at is newer, insert if new"]
        A9["9. Set hwm = cutoff, write committed run row, COMMIT"]
    end

    ROLL["Roll back, drop staging, log attempt as failed"]
    MORE{"Failed attempts so far is below 3?"}
    PAGE(["Page on-call with run id and error"])

    STALE{"Committed run for tonight at 06:00?"}
    ALERT(["Post staleness alert to #data-alerts"])
    OKW["No action"]
    DASH(["Analyst dashboards"])

    subgraph RECON["Weekly reconciliation"]
        C1["1. For each of the last 30 complete UTC creation days"]
        C2["2. Replica: count and checksum of order_id and updated_at, rows with updated_at up to H"]
        C3["3. Warehouse: same count and checksum, limited to order_ids the replica returned"]
        C4{"Match?"}
        C5["4. Reload that day from replica with the same guarded MERGE"]
        C6["5. Re-compare; still different: alert #data-alerts, no more automatic reloads"]
        C7["Next day"]
    end

    T_NIGHT --> A1
    A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7 --> A8 --> A9

    RUN -->|"error or timeout"| ROLL
    ROLL --> MORE
    MORE -->|"yes, retry"| T_RETRY
    T_RETRY --> A1
    MORE -->|"no, third failure"| PAGE

    A9 -->|"single transaction commit"| W_CUR
    A9 --> W_WM
    A9 --> W_LOG
    W_CUR --> W_VIEW
    W_VIEW -.->|"refresh 06:00 UTC, sees committed data only"| DASH

    T_WATCH --> STALE
    W_WM -.->|"reads committed_at"| STALE
    STALE -->|"no"| ALERT
    STALE -->|"yes"| OKW

    W_WM -.->|"read"| A2
    R_ORD -.->|"read-only query"| A3
    R_ORD -.->|"read-only query"| A4
    A4 -.->|"rows"| A5
    A5 -.->|"write"| W_STG
    W_STG -.->|"read"| A6
    W_STG -.->|"read"| A8
    A8 -.->|"merge"| W_CUR

    T_SUN --> C1 --> C2 --> C3 --> C4
    R_ORD -.-> C2
    W_CUR -.-> C3
    C4 -->|"yes"| C7
    C4 -->|"no"| C5
    C5 -.->|"upsert"| W_CUR
    C5 --> C6
```

## Notes

**Start and schedule.** The nightly run starts at 02:00 UTC from the scheduler. A retry starts 15 minutes after the failed attempt is logged. The 06:00 watchdog is a separate scheduled job, so it still fires if the pipeline hangs. The weekly reconciliation starts after the Sunday night load commits. If that load does not commit, the reconciliation waits for the next successful load.

**Window and high-water mark.** Each run reads `hwm - 2h` through `cutoff`. The cutoff is the replica's replay timestamp (`pg_last_xact_replay_timestamp()`), not the wall clock, and a null value fails the attempt. Replay order means every transaction committed at or before the cutoff is already visible on the replica. A row not yet visible has an `updated_at` at least 90 minutes before its commit time, so it is later than `cutoff - 90min`, which is inside the 2-hour lookback. Replica lag therefore does not open a gap. The residual risks are a transaction open longer than 90 minutes, which breaks the bound, and app clocks that skew from the database clock. Reconciliation is the backstop for both. On a quiet primary the replay timestamp can stay old. The window then stops moving but nothing is lost. The first run has no watermark, so it does a one-time full extract from a configured start date.

**Staging.** Each attempt creates its own staging table, `stg_orders_RUN_ID`, in the warehouse. Staging is rebuilt on every attempt and dropped afterwards. Validation rejects null keys or timestamps, and it rejects a staged count that differs from the extracted count. Deduplication keeps one row per `order_id`, chosen by the highest `updated_at`, with a row hash as the tie-breaker. An equal `updated_at` with different content is logged as an anomaly.

**Merge.** The merge is keyed on `order_id`. A matched row is updated only when the incoming `updated_at` is strictly newer, and `is_deleted` is set from `deleted_at IS NOT NULL`. An unmatched row is inserted. Because deletes are writes that bump `updated_at`, a soft delete flows through the same rule and the row stays. Re-running a window is a no-op for unchanged rows. An older bulk-imported version cannot overwrite a newer one that was loaded earlier.

**State location.** All state lives in the warehouse. `etl_watermark` holds `hwm`, `last_committed_run_id` and `committed_at`. `etl_run_log` holds one row per attempt, with its status and error. The pipeline lock is a row in the warehouse too. The app database is read only.

**Atomic visibility.** The merge, the watermark update and the run-log commit happen in one warehouse transaction. Dashboards read committed state only, so they never see a half-loaded night. If the warehouse cannot commit a MERGE together with a table update, build `orders_current_next` from the merge and swap it in with one atomic rename in the same transaction.

**Failure, retry and alerts.** Any error or timeout rolls back the transaction, drops staging, and logs the attempt as failed. Each attempt starts from the same `hwm`, so a retry covers the same window and leaves no gap. Attempts run at 02:00, 02:15 and 02:30 if each fails quickly. A hung attempt is cut by an attempt timeout, and the next attempt waits for the lock. After the third failed attempt the on-call page goes out with the run id and error. At 06:00 the watchdog checks `etl_watermark.committed_at` for a commit since 02:00. If there is none, it posts a staleness alert to #data-alerts. A load that commits after 06:00 is visible at the next dashboard refresh, and the alert needs a follow-up message in the same channel. Manual reruns use the same entry point and the same lock.

**Reconciliation (Sunday).** Let `H` be the high-water mark committed by that night's load. For each of the last 30 complete UTC creation days, the replica and the warehouse each compute a count and an order-independent checksum over `order_id|updated_at` in UTC microseconds, using rows with `updated_at <= H`. For example, the checksum is the sum of a 64-bit hash of each string, modulo 2^64, computed the same way on both sides. The warehouse side is limited to the `order_id`s the replica returned. Without that limit, a row edited after `H` would look like a mismatch: the replica would drop its new version while the warehouse still held the old one. A mismatched day is reloaded from the replica with the same guarded MERGE, which is an upsert and never deletes. The day is then compared again. If it still differs, the job alerts #data-alerts and does not reload again automatically. The reconciliation does not move the watermark.

## Assumptions to confirm

- `orders` has `created_at` (needed for creation-day reconciliation), `deleted_at`, and a non-null `updated_at` that is set on every write.
- The app database is PostgreSQL, so the replica exposes `pg_last_xact_replay_timestamp()`.
- The warehouse supports a multi-statement transaction with MERGE. If not, use the swap fallback above.
- App and database clocks are synchronized to within a few minutes.
- Bulk-import transactions stay open for at most 90 minutes.
- The reasoning in the window section is analytical and has not been tested against a live replica.