# Nightly orders ETL into the warehouse

## How to read this

- Rectangles are steps. Cylinders are state or data stores.
- Every store is tagged **[WH]** (warehouse) or **[REPLICA]**. All pipeline state is in the warehouse, because we have no write access to the app database.
- Dotted edges are failure paths.
- There are three triggers: the 02:00 UTC nightly run, the 06:00 UTC staleness watchdog, and the Sunday reconciliation. The reconciliation is chained to the nightly run's success. It is not on its own clock.

```mermaid
flowchart TD
  subgraph TRIG["What starts things"]
    T0["Scheduler cron<br/>02:00 UTC daily<br/>attempt = 1"]
    T1["Scheduler retry timer<br/>15 min after a failed attempt<br/>attempt = previous + 1"]
    T6["Scheduler cron<br/>06:00 UTC daily<br/>staleness watchdog"]
  end

  subgraph ATT["One nightly attempt"]
    A1["1. Start: insert row in etl.run_log<br/>run_id, run_date, attempt, status = running"]
    A2["2. Read hwm from etl.control<br/>lower = hwm minus 2 hours"]
    A3["3. Open read-only REPEATABLE READ transaction on replica<br/>cutoff = replica now"]
    A4["4. Extract all columns for rows with updated_at after lower<br/>and up to cutoff<br/>soft-deleted rows included"]
    A5{"5. Validate staging<br/>staged count = extracted count<br/>order_id not null and unique"}
    A6["6. Warehouse transaction<br/>MERGE stg into dw.orders<br/>UPDATE etl.control SET hwm = cutoff<br/>COMMIT"]
    A7["7. Mark run_log success<br/>set last_success_run_date = run_date"]
  end

  R[("orders table<br/>[REPLICA] read only")]
  CTL[("etl.control<br/>hwm, last_success_run_date<br/>[WH]")]
  LOG[("etl.run_log<br/>one row per attempt<br/>[WH]")]
  STG[("stg.orders_nightly<br/>truncated at start of every attempt<br/>[WH]")]
  DW[("dw.orders<br/>one row per order_id, latest version<br/>[WH]")]

  T0 --> A1
  T1 --> A1
  A1 -->|"write status"| LOG
  A1 --> A2
  CTL -->|"read hwm"| A2
  A2 --> A3
  R -->|"rows in window"| A4
  A3 --> A4
  A4 -->|"bulk load, replaces prior contents"| STG
  STG --> A5
  A5 -->|"pass"| A6
  STG -->|"source rows"| A6
  A6 -->|"upsert, newer or equal updated_at wins"| DW
  A6 -->|"advance hwm in same transaction"| CTL
  A6 --> A7
  A7 -->|"write status"| LOG
  A7 --> DONE(["Night loaded, dashboards see it at next refresh"])

  FAIL["Attempt failed<br/>warehouse transaction rolls back or never started<br/>hwm unchanged<br/>run_log status = failed with error"]
  A1 & A2 & A3 & A4 & A5 & A6 -.->|"any error or timeout"| FAIL
  FAIL -.->|"write status"| LOG
  FAIL -.-> RETRYQ{"attempt less than 3?"}
  RETRYQ -.->|"yes: wait 15 min"| T1
  RETRYQ -.->|"no: third failure"| PAGE["Page on-call<br/>hwm not advanced<br/>next night re-covers the gap"]

  DONE -->|"Sunday only"| C1

  subgraph REC["Sunday reconciliation, after that night's load"]
    C1["a. For each order-creation day in last 30 days<br/>compute row count and checksum of order_id plus updated_at<br/>on replica and on dw.orders"]
    C2{"b. Any day where<br/>count or checksum differs?"}
    C3["c. Extract all rows created on each mismatched day<br/>from replica"]
    C4["d. Warehouse transaction<br/>same MERGE into dw.orders<br/>hwm not touched"]
    C5["e. Log result in etl.run_log"]
  end
  RCSTG[("stg.orders_recon<br/>[WH]")]
  R -->|"per-day aggregates and full rows"| C1
  R -->|"rows for mismatched days"| C3
  DW -->|"per-day aggregates"| C1
  C1 --> C2
  C2 -->|"no"| C5
  C2 -->|"yes"| C3
  C3 -->|"load"| RCSTG
  RCSTG --> C4
  C4 -->|"upsert"| DW
  C4 --> C5
  C5 --> RDONE(["Reconciliation complete"])
  C1 & C3 & C4 -.->|"error"| RFAIL["Reconciliation attempt failed<br/>same policy: retry twice, 15 min apart<br/>then page on-call"]

  T6 --> W1{"etl.control.last_success_run_date<br/>equals today?"}
  CTL -->|"read"| W1
  W1 -->|"yes"| W2(["Fresh, no action"])
  W1 -->|"no: not committed by 06:00"| W3["Post staleness alert to #data-alerts<br/>include run_log status and attempt number"]
  W3 -.->|"run keeps going, may still commit later"| A6

  DASH["Analyst dashboards refresh 06:00 UTC<br/>read dw.orders committed state only"]
  DW -->|"read"| DASH
```

## What starts each step

| Step | Trigger |
|---|---|
| Nightly attempt 1 | Scheduler cron, 02:00 UTC. |
| Retry attempts 2 and 3 | The scheduler's retry timer fires 15 minutes after the previous attempt fails, not after it started. |
| Page on-call | The third failed attempt. |
| Sunday reconciliation | Success of Sunday's nightly load, so it runs after the load and never alongside it. If Sunday's night ends in a page, reconciliation is skipped that week. The next night's catch-up window still covers the gap, and the following Sunday's reconciliation looks back 30 days. |
| Staleness check | Scheduler cron, 06:00 UTC, separate from the job. It still fires if the job hangs or the scheduler never started it. |

## Where the state lives

All state is in the warehouse.

- **`etl.control`** has one row per pipeline, `orders_nightly`.
  - `hwm` is a UTC timestamptz.
  - `last_success_run_date` is the date of the last committed run.
  - It is the only authority on the high-water mark.
- **`etl.run_log`** has one row per attempt, for both nightly and reconciliation runs.
  - Columns are `run_id`, `run_date`, `kind`, `attempt`, `cutoff`, `rows_extracted`, `status`, `error` and timestamps.
  - It is for audit and alert content. The pipeline's correctness does not depend on it.
- **`stg.orders_nightly`** and **`stg.orders_recon`** are scratch tables. They are truncated at the start of every attempt, so a failed or repeated attempt leaves nothing behind.
- **`dw.orders`** is the target.
  - It has a primary key on `order_id`.
  - It has `created_at` (needed by reconciliation), `updated_at`, `deleted_at` and `is_deleted`.
  - `is_deleted` is derived on load as `deleted_at IS NOT NULL`.
  - Deleted orders are kept.
- **Attempt count and retry timer** belong to the scheduler. Each attempt also records its number in `run_log`.

The scheduler is the only state outside the warehouse. The replica holds no pipeline state.

## Extraction

- **Window.** `updated_at > hwm - 2h AND updated_at <= cutoff`.
  - The cutoff is taken once, as `now()` on the replica when the snapshot transaction opens.
  - The query runs in a read-only `REPEATABLE READ` transaction, so one night gets one consistent snapshot with a fixed upper bound.
  - Soft-deleted rows match like any other write, because setting `deleted_at` bumps `updated_at`.
- **Margin.** The 2-hour lookback covers the 90-minute bulk-import window with 30 minutes of margin. Replica lag beyond that margin is what the Sunday reconciliation exists for.
- **Per-attempt re-read.** Each retry re-reads `hwm` and takes a new cutoff. It never reuses the failed attempt's cutoff, so a retry cannot skip rows.
- **First run.** If `etl.control` has no row, seed `hwm` at the epoch for a full initial load.

## Staging and validation

- The extract bulk-loads into `stg.orders_nightly`.
- Before touching the target, check that the staged count equals the extracted count, that `order_id` is non-null, and that `order_id` is unique.
- Uniqueness is expected, because one snapshot returns each order once. The check is a guard against bad data, not a dedupe step.
- A failed check fails the attempt.

## Merge logic

Everything happens in a single warehouse transaction:

1. `MERGE INTO dw.orders t USING stg.orders_nightly s ON t.order_id = s.order_id`
   - `WHEN MATCHED AND s.updated_at >= t.updated_at THEN UPDATE` all columns, with `is_deleted = (s.deleted_at IS NOT NULL)`.
   - `WHEN NOT MATCHED THEN INSERT`.
2. `UPDATE etl.control SET hwm = GREATEST(hwm, :cutoff), last_success_run_date = :run_date`
3. `COMMIT`

Why this design:

- **One row per order, always the latest version.** The `updated_at >= t.updated_at` guard means an older copy can never overwrite a newer one. An out-of-order reload, such as a reconciliation reload, can't regress a row.
- **`>=` rather than `>`.** Re-applying an identical row is harmless, so reruns are idempotent.
- **Re-extracted rows.** The overlap from the lookback re-extracts rows that are already loaded. The merge turns them into no-op updates.
- **No half-loaded night.** Dashboards read committed state only. Either the whole night's merge and the hwm advance are visible, or none of it is.
- **Atomic hwm.** The high-water mark moves in the same transaction as the data. It advances to `cutoff` only if the data committed, and `GREATEST` keeps it monotonic.
- **Warehouse assumption.** This assumes the warehouse supports a transactional `MERGE` or an equivalent delete-and-insert in one transaction. If it doesn't, load into a shadow table and swap it in atomically, keeping the same hwm rule.

## Failure and retry

- **Where a failure can happen.**
  - Any failure before the commit means rollback or no write to `dw.orders`.
  - `hwm` is unchanged and staging is discarded on the next attempt.
  - The `failed` status goes to `run_log` outside the merge transaction, so it survives the rollback.
- **Retries.** Attempts 2 and 3 start 15 minutes after the previous failure. They run the whole sequence again from step 1.
- **After the third failure.** Page on-call. `hwm` stays where it was. The next night's window starts at the old `hwm - 2h`, so the next night's job loads the missed data without a gap. The page asks a human to investigate, and the data catches up on its own once the cause is fixed.
- **Rerunning a night.** A manual rerun of a night that already succeeded is safe. It re-reads the current `hwm`, which is later, extracts a window that mostly overlaps, and merges as no-ops.
- **Late commit.** If a run is still going at 06:00, it continues. If it commits later, dashboards pick it up at their next refresh. The watchdog alert stands, so post a recovery note in #data-alerts when `last_success_run_date` becomes today.

## Staleness alert (06:00 UTC)

The watchdog is independent of the job. It only reads `etl.control.last_success_run_date`.

- If that date is not today, post to #data-alerts. Include the `run_log` status and attempt number so the channel can see whether it is retrying, hung or paged.
- The dashboards refresh at 06:00 regardless. Because of the single-transaction commit, they show either the previous night's complete state or the new night's complete state.

## Sunday reconciliation

It runs after Sunday's nightly load succeeds and covers late arrivals that the lookback misses, for example when the replica falls behind.

- **Per-day comparison.**
  - For each `created_at` day in the last 30 days, compute `count(*)` and an order-independent checksum.
  - The checksum is the sum of a 64-bit hash of the canonical string `order_id || '|' || updated_at` in UTC at microsecond precision.
  - The format must be identical on both sides. Compute it with the same definition on the replica and on `dw.orders`.
  - It catches missing rows, extra rows, and rows whose `updated_at` differs. A soft-delete changes `updated_at`, so it is detected too.
- **Reload.** For each mismatched day, extract all of that day's rows from the replica, including deleted ones, into `stg.orders_recon`, then run the same guarded `MERGE`. It does not touch `hwm`, so it can't affect the nightly window.
- **Timing quirk.** A day that mismatches only because orders changed on the replica after the nightly cutoff is also reloaded. This is harmless, because the merge is idempotent and the next nightly picks those rows up anyway.
- **Reconciliation failure.** It uses the same policy as the nightly run: retry twice, 15 minutes apart, then page on-call. It does not change the nightly job's status or the staleness check.

## Decisions worth confirming

- **`hwm = cutoff` rather than `max(updated_at)`.** This keeps the mark moving on quiet nights. It is safe because the 2-hour lookback and the Sunday reconciliation cover rows that become visible later.
- **Retry timing.** The 15 minutes is measured from the failure of the previous attempt, as the brief says. Three attempts at the worst case fit well before 06:00 unless an attempt itself runs long.
