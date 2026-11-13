# Nightly orders ETL into the warehouse

## Summary

A scheduler job runs at 02:00 UTC. It reads rows changed since the stored high-water mark (HWM) minus 2 hours from the read replica and loads them into a staging table in the warehouse. In one warehouse transaction it then dedupes, merges into `dw.orders`, advances the HWM and marks the run committed. Because those steps commit together, dashboards see either the old state or the finished night, never a partial load. All pipeline state lives in the warehouse. Nothing is written to the app database.

## Flowchart

```mermaid
flowchart TD
    subgraph SCH["Scheduler - all times UTC"]
        T0["02:00 daily trigger"]
        T6["06:00 freshness check trigger"]
    end

    REPL[("App Postgres<br/>READ REPLICA<br/>read only")]

    subgraph WH["WAREHOUSE - holds all pipeline state"]
        CTL[("etl.control<br/>high_water_mark<br/>one row per pipeline")]
        LOG[("etl.run_log<br/>run_id, run_date, attempt, status<br/>window, row counts, committed_at")]
        STG[("stg.orders_extract<br/>rows tagged with run_id")]
        DW[("dw.orders<br/>one row per order_id<br/>is_deleted flag")]
        RLOG[("etl.recon_log<br/>per-day counts, checksums, action")]
    end

    T0 --> A1

    subgraph NIGHT["Nightly run - attempt n of 3"]
        A1["1 Start attempt<br/>take run lease, insert run_log row status=running<br/>read HWM from etl.control<br/>lower = HWM minus 2h"]
        A2["2 Extract from replica<br/>one read-only REPEATABLE READ snapshot<br/>WHERE updated_at greater than lower<br/>includes rows with deleted_at set"]
        A3["3 Load into staging<br/>drop any leftover rows for this run_id<br/>bulk load; not visible to dashboards"]
        A4["4 COMMIT STEP - one warehouse transaction<br/>a dedupe: keep latest updated_at per order_id<br/>b MERGE into dw.orders<br/>c HWM = GREATEST of HWM and max staged updated_at<br/>d run_log status=committed<br/>e clear this run_id from staging"]
    end

    A1 --> A2
    REPL -->|"changed rows"| A2
    CTL -->|"read HWM"| A1
    A1 -->|"insert running row"| LOG
    A2 --> A3
    A3 -->|"staged rows"| STG
    A3 --> A4
    STG -->|"deduped rows"| A4
    A4 -->|"upsert, newer wins"| DW
    A4 -->|"advance HWM, same txn"| CTL
    A4 -->|"mark committed, same txn"| LOG

    A1 & A2 & A3 & A4 -->|"error or timeout"| FAIL["Attempt failed<br/>transaction rolled back, so dw.orders and HWM unchanged<br/>run_log status=failed<br/>staging rows for run_id dropped"]
    FAIL --> D1{"attempt less than 3?"}
    D1 -->|"yes"| W15["Wait 15 minutes"]
    W15 -->|"attempt n+1, same HWM, full redo"| A1
    D1 -->|"no, third failure"| PAGE["PAGE ON-CALL<br/>run stays failed<br/>HWM not advanced"]

    A4 -->|"success"| D2{"Is the run_date a Sunday?"}
    D2 -->|"no"| DONE["Night complete"]
    D2 -->|"yes"| R1

    subgraph REC["Sunday reconciliation - starts only after Sunday load committed"]
        R1["1 Per creation day for last 30 days<br/>count and checksum of order_id plus updated_at<br/>on replica AND on warehouse"]
        R2{"2 Any day where count or checksum differs?"}
        R3["3 Re-extract each mismatched day from replica<br/>WHERE created_at falls on that day<br/>load to stg.orders_extract under a recon run_id"]
        R4["4 One warehouse transaction<br/>same dedupe and MERGE as nightly<br/>HWM NOT touched<br/>write recon_log, clear staging"]
    end

    REPL -->|"day aggregates"| R1
    DW -->|"day aggregates"| R1
    R1 --> R2
    R2 -->|"no"| RDONE["Reconciliation complete, log all days as matched"]
    R2 -->|"yes"| R3
    REPL -->|"all rows of mismatched days"| R3
    R3 --> R4
    R4 -->|"upsert, newer wins"| DW
    R4 --> RLOG
    R1 --> RLOG
    R1 & R3 & R4 -->|"error"| RFAIL["Reconciliation failed<br/>rolled back; retry per the same 3-attempt, 15 min rule<br/>then page on-call"]
    RFAIL --> PAGE

    T6 --> C1{"run_log shows tonight's run_date<br/>with status=committed?"}
    LOG -->|"read status"| C1
    C1 -->|"yes"| OKDASH["Dashboards refresh at 06:00 on the finished night"]
    C1 -->|"no"| STALE["POST STALENESS ALERT to #data-alerts<br/>dashboards read last committed state<br/>run and retries keep going"]
```

## Where state lives

All state is in the warehouse.

| Object | Purpose |
|---|---|
| `etl.control` | One row per pipeline (`orders`) with `high_water_mark timestamptz`. The only source of truth for where the next night starts. Seeded once at first deploy, either to the earliest `updated_at` or to a chosen backfill start. |
| `etl.run_log` | One row per attempt, with `run_id`, `run_date`, `attempt`, `status` (running, failed, committed), the lower bound used, rows extracted and `committed_at`. It drives the 06:00 check, the retry count and the Sunday trigger. |
| `stg.orders_extract` | Landing table, tagged by `run_id`. Raw replica rows, possibly with duplicates. Dashboards never read it. |
| `dw.orders` | The served table, with one row per `order_id`. |
| `etl.recon_log` | Per-day counts, checksums and whether a reload happened. |

The run lease prevents two attempts from overlapping. The nightly run and the reconciliation also never overlap, because the reconciliation only starts after the Sunday load commits.

## What starts each step

- **02:00 UTC scheduler trigger.** Starts attempt 1.
- **Failure of any step.** Starts the retry. The orchestrator waits 15 minutes and starts the next attempt. This happens at most twice, giving 3 attempts in total.
- **Third failure.** Pages on-call.
- **06:00 UTC scheduler trigger.** Runs a separate check job, independent of the load. It reads `run_log`. If tonight's run is not `committed`, it posts to #data-alerts. A run still in retry at 06:00 keeps going, and dashboards keep the last committed data until it commits.
- **Successful commit on a Sunday run.** Triggers the reconciliation. It is a dependency of that run, not a fixed clock time, so it always runs after that night's load. If Sunday's load fails all 3 attempts, the reconciliation does not run and on-call is already paged.

## Data movement and logic

**Extract.**
- The query is `SELECT * FROM orders WHERE updated_at > :lower`, with `:lower = HWM - interval '2 hours'`.
- It runs against the replica in one read-only `REPEATABLE READ` transaction, so the extract is a consistent snapshot.
- Soft-deleted rows are included, because `deleted_at` is a write that bumps `updated_at`.
- The 2-hour lookback covers the 90-minute bulk-import gap with 30 minutes to spare.

**Stage.**
- Rows are bulk-loaded into `stg.orders_extract` with the `run_id`.
- This load is not transactional with `dw.orders` and doesn't need to be. A failed attempt just deletes its staged rows.
- A retry gets a new `run_id`, so it never mixes with a previous attempt's rows.

**Merge, in one transaction.** Order and the `updated_at` guard make re-runs safe.

```sql
BEGIN;

WITH latest AS (
  SELECT * FROM (
    SELECT s.*, ROW_NUMBER() OVER (PARTITION BY order_id
                                   ORDER BY updated_at DESC) AS rn
    FROM stg.orders_extract s WHERE run_id = :run_id
  ) WHERE rn = 1
)
MERGE INTO dw.orders t
USING latest s ON t.order_id = s.order_id
WHEN MATCHED AND s.updated_at > t.updated_at THEN
  UPDATE SET /* all columns */ ..., is_deleted = (s.deleted_at IS NOT NULL)
WHEN NOT MATCHED THEN
  INSERT (...) VALUES (..., (s.deleted_at IS NOT NULL));

UPDATE etl.control
   SET high_water_mark = GREATEST(high_water_mark,
         (SELECT MAX(updated_at) FROM stg.orders_extract WHERE run_id = :run_id))
 WHERE pipeline = 'orders';   -- skipped if staging is empty

UPDATE etl.run_log SET status = 'committed', committed_at = now() WHERE run_id = :run_id;
DELETE FROM stg.orders_extract WHERE run_id = :run_id;

COMMIT;
```

- **One row per `order_id`.** The dedupe keeps the latest version within the extract. The `MERGE` key keeps one row across nights.
- **Newer wins.** `s.updated_at > t.updated_at` means an older or identical version never overwrites a newer one. Re-running a night, or extracting the same order on two nights, changes nothing.
- **Deleted orders stay.** They are updated in place with `is_deleted = true`, never removed.

**Why the HWM lives in the commit transaction.**
- The HWM, the merge and the `committed` status commit together or not at all. That meets "advances only once loaded" and "no half-loaded night".
- A crash at any point leaves the old HWM and old data, so a rerun is safe.
- The HWM is the max `updated_at` actually staged, never the wall clock. A row that becomes visible late is therefore caught by the next night's lookback.
- `GREATEST` means the HWM never moves backward.

**Sunday reconciliation.**
- For each creation day (`created_at` date, UTC) in the last 30 days, both sides compute `COUNT(*)` and an order-independent checksum.
- The checksum is `SUM` over rows of the first 64 bits of `md5(order_id || '|' || updated_at)`, with `updated_at` normalised to UTC at microsecond text precision. The same expression runs on both sides.
- Warehouse counts include `is_deleted` rows, to match the replica.
- Any mismatched day is re-extracted in full from the replica and merged with the same logic, in one transaction covering all mismatched days.
- The reload only upserts and never touches the HWM.
- If the replica is still behind and the warehouse already holds a newer `updated_at`, the `>` guard keeps the warehouse row. The day may mismatch again next Sunday until the replica catches up. That is logged, not an error.

## Failure behaviour

| Failure | Result |
|---|---|
| Replica unreachable or extract error | Attempt fails, staged rows are dropped, retry after 15 minutes. |
| Staging load fails | Same as above. |
| Merge or HWM update fails | The transaction rolls back, so `dw.orders` and the HWM are exactly as before. Retry. |
| Crash after commit, before the scheduler hears back | Data and HWM are already correct. The retry re-extracts the same window and changes nothing. |
| 3rd attempt fails | Page on-call. The HWM stays put, and the next 02:00 run covers the larger window automatically. |
| Load not committed by 06:00 | Staleness alert to #data-alerts. Dashboards show the last committed state, not a partial one. |
| Reconciliation fails | Rolled back, retried under the same 3-attempt, 15-minute rule, then paged. The nightly path is unaffected. |

## Assumptions

- The warehouse supports multi-statement transactions with `MERGE` or an equivalent delete-and-insert in one transaction. If it doesn't, the same atomicity can come from loading into a shadow table and swapping it in.
- `orders` has an immutable `created_at`, used for the reconciliation day buckets.
- The scheduler can express "retry in 15 minutes, max 3 attempts", a dependent Sunday step, and a separate 06:00 job.
- The reconciliation retry-and-page policy is my choice, since the brief only specifies it for the nightly run.
