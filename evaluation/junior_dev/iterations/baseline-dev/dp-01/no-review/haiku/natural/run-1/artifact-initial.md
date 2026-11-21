# Nightly orders ETL: pipeline flowchart

```mermaid
flowchart TD
    subgraph SCHED["Scheduler, UTC"]
        START(["02:00 scheduler starts night N, attempt 1"])
        WAIT(["Wait 15 minutes, then start attempt n plus 1"])
        DASH(["06:00 dashboards refresh"])
        CHECK(["06:00 staleness check"])
    end

    subgraph REPL["App Postgres read replica, read-only"]
        SRC[("orders")]
    end

    subgraph WH["Analytics warehouse, holds all pipeline state"]
        WMK[("etl_watermark: hwm")]
        RUNS[("etl_runs: one row per attempt, with window_lo and window_hi")]
        STG[("stg_orders_RUNID: staging")]
        DW[("dw_orders: one row per order_id, with is_deleted")]
    end

    START --> PLAN["Create or load the etl_runs row for night N. First attempt reads hwm H and fixes lo = H minus 2h and hi = T0, the run start time. Retries reuse the stored lo and hi."]
    WMK -.-> PLAN
    PLAN --> EXT["Extract in one REPEATABLE READ transaction on the replica: rows with updated_at after lo and up to hi, keyset-paged by (updated_at, order_id)"]
    SRC -.-> EXT
    EXT -->|"raw rows"| STG
    EXT -->|"error"| FAIL
    STG --> VAL{"Staging checks pass? No null order_id, valid types"}
    VAL -->|"no"| FAIL
    VAL -->|"yes"| DEDUP["Keep one row per order_id. Latest updated_at wins; ties broken by a row hash"]
    DEDUP --> TXN["BEGIN load transaction in the warehouse"]
    TXN --> MERGE["MERGE into dw_orders on order_id. Matched and staged updated_at later than target: update all columns, set is_deleted = deleted_at is not null. Not matched: insert."]
    MERGE -->|"error"| FAIL
    MERGE --> HWMUP["UPDATE etl_watermark SET hwm = hi"]
    HWMUP --> OK["INSERT etl_runs status = succeeded, then COMMIT"]
    OK -.-> RUNS
    OK --> DONE(["Night N committed; dashboards can see it"])
    OK --> SUN{"Sunday?"}
    SUN -->|"no"| END1(["Done"])
    SUN -->|"yes"| RECON["For each creation day in the last 30 days, compare count and checksum of order_id and updated_at between replica and warehouse, both limited to updated_at up to hi"]
    SRC -.-> RECON
    DW -.-> RECON
    RECON --> MISM{"Day matches?"}
    MISM -->|"yes"| END2(["Next day"])
    MISM -->|"no"| RELOAD["Reload that creation day from the replica through the same staging and MERGE path. Watermark is not changed. Failure is logged and does not undo the night load."]
    RELOAD -->|"full-day extract"| STG

    FAIL["Mark attempt failed in etl_runs, ROLLBACK any open load transaction"] -.-> RUNS
    FAIL --> CNT{"Was this attempt number 3?"}
    CNT -->|"no"| WAIT
    WAIT --> PLAN
    CNT -->|"yes"| PAGE["Page on-call. Watermark stays at the last success, so the next night's window covers the gap."]

    DASH --> READ["Dashboards read committed dw_orders only"]
    DW -.-> READ
    CHECK --> STALE{"Is there a succeeded etl_runs row for night N?"}
    RUNS -.-> STALE
    STALE -->|"no"| ALERT["Post staleness alert to #data-alerts"]
    STALE -->|"yes"| NOOP(["No alert"])
```

## Notes

**What starts each step.** The 02:00 UTC scheduler starts night N as attempt 1. A failed attempt starts the next attempt 15 minutes later, up to three attempts in total. The 06:00 UTC dashboard refresh and staleness check are separate scheduled triggers, not part of the load.

**Data movement.** Rows move from the app's replica (read-only) into a per-run staging table in the warehouse, then are merged into `dw_orders`. The app database is never written to. Reconciliation reads the replica and the warehouse and writes only to the warehouse.

**Where state lives.** All bookkeeping is in the warehouse:
- `etl_watermark` holds the high-water mark (`hwm`).
- `etl_runs` holds one row per attempt for each night, with `window_lo`, `window_hi`, attempt number, status and error.
- `stg_orders_RUNID` is the per-attempt staging table, dropped after commit or failure.
- `dw_orders` is the target, with one row per `order_id`, `is_deleted`, and `loaded_run_id`.

**Window and high-water mark.** The night's window is `lo = hwm - 2h` to `hi = T0`, where T0 is the run start time captured once. `hi` is stored on the `etl_runs` row, so retries repeat the exact same window. The high-water mark is set to `hi`, not to the maximum `updated_at` seen, because a late-visible row could sit below the maximum and be skipped. Setting it to `hi` is safe: any row stamped before `hi` that was invisible tonight is inside the next night's window, which starts at `hi - 2h`. That 2-hour overlap covers the 90-minute visibility lag of bulk-import transactions.

**Staging and dedupe.** Extraction is keyset-paged on `(updated_at, order_id)` inside one REPEATABLE READ transaction, so the extract is a consistent snapshot. The staged rows are reduced to one row per `order_id`, keeping the latest `updated_at`. Ties are broken by a row hash so the result is deterministic.

**Merge logic.** The MERGE is keyed on `order_id`. It updates a matched row only when the staged `updated_at` is strictly later than the target's. Unmatched rows are inserted. `is_deleted` is derived from `deleted_at IS NOT NULL` in the same statement. Because the guard is strict, re-running a night or extracting an older version never overwrites newer data, and the result is idempotent.

**Atomic visibility.** The MERGE and the watermark update run in one warehouse transaction that commits once. Dashboards read only committed state, so they see either the previous night or the complete new night, never a partial load. This assumes the warehouse supports multi-statement transactions. If it does not, the fallback is to load into a new table version and swap a view in one step.

**Failure and retry.** A failure at extract, staging checks or MERGE triggers ROLLBACK, marks the attempt failed in `etl_runs`, and leaves the watermark unchanged. Attempts 2 and 3 are 15 minutes apart. After attempt 3 fails, on-call is paged. A failed night does not lose data: the next night's window starts from the last successful `hwm`, so it picks up the gap.

**Staleness.** At 06:00 UTC, the check looks for a succeeded `etl_runs` row for night N. If there is none, it posts to #data-alerts. Dashboards still refresh at 06:00 and show the last committed night, which is consistent but one night old.

**Reconciliation.** Each Sunday, after the night's commit, the job compares each creation day in the last 30 days. Both sides are limited to `updated_at` up to `hi`, so in-flight changes do not cause false mismatches. The checksum is an order-independent aggregate, for example a sum of truncated md5 values of a canonical `order_id|updated_at` string in UTC microseconds, computed identically on both sides. A mismatched day is reloaded in full from the replica through the same staging and MERGE path. The watermark is not touched.

**Assumptions and open points.**
- The brief does not name a creation timestamp. This design assumes `orders` has a `created_at` column, which reconciliation uses to group rows by creation day. Dates are taken in UTC.
- If the replica itself is behind, a reload reproduces the same gap. The job should log days that still mismatch after reload, so they are visible on the next Sunday.
- Hard deletes never happen, so a reload never needs to remove rows from the warehouse.
- The exact checksum expression and the staging-check rules still need to be written and agreed with the team.