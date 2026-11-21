# Nightly `orders` ETL into the warehouse: pipeline plan

## Diagram

```mermaid
flowchart TD
  subgraph APP["App Postgres (we have read-only access to the replica)"]
    PRIM[("Primary: every write sets updated_at, deletes set deleted_at")] -->|replication| REP[("Read replica")]
  end

  subgraph WH["Analytics warehouse (all pipeline state lives here)"]
    CTRL[("etl_watermark: last committed cutoff, one row")]
    LOG[("etl_run_log: one row per attempt")]
    STG[("orders_stage: this run's extract, keyed by run_id")]
    ORD[("orders: one row per order_id, serving table")]
    RECON[("recon_result: one row per creation day per check")]
  end

  CRON["Scheduler fires at 02:00 UTC"] --> START["New run: run_id, attempt n, cutoff fixed at 02:00 UTC for every attempt"]
  START --> LOGSTART["Write attempt start to etl_run_log"]
  LOGSTART --> READHWM["Read hwm from etl_watermark, set lower = hwm minus 2h"]
  CTRL -.->|hwm| READHWM
  READHWM -->|"first run only: lower = configured backfill start"| EXTRACT
  READHWM --> EXTRACT["Extract: updated_at greater than lower and at most cutoff, read-only"]
  REP -.->|rows| EXTRACT
  EXTRACT --> STG["Delete any earlier rows for this run_id, then bulk load extract into orders_stage"]
  STG --> DEDUP["Dedupe in stage: one row per order_id, latest updated_at wins, ties broken by row hash. Compute is_deleted"]
  DEDUP --> TXN["One warehouse transaction: MERGE into orders, then set etl_watermark to cutoff"]
  TXN -->|commit| ORD
  TXN -->|commit| CTRL
  TXN -->|commit| OKLOG["Write success to etl_run_log"]
  TXN -->|"any error: rollback, orders and watermark unchanged"| FAIL["Attempt failed"]
  EXTRACT -->|error| FAIL
  STG -->|error| FAIL
  DEDUP -->|error| FAIL
  FAIL --> FAILLOG["Write failure to etl_run_log, in its own autocommit statement so it survives the rollback"]
  FAILLOG --> DEC{"Attempts used less than 3?"}
  DEC -->|"yes: wait 15 min, same cutoff"| START
  DEC -->|"no: third failure"| PAGE["Page on-call with run_id and last error"]

  CHKCRON["06:00 UTC staleness check, separate job"] --> CHK{"Committed run with cutoff 02:00 UTC today in etl_run_log?"}
  CTRL -.->|read| CHK
  LOG -.->|read| CHK
  CHK -->|no| STALE["Post staleness alert to #data-alerts"]
  CHK -->|yes| NOALERT["No alert"]

  DASH["Analyst dashboards refresh at 06:00 UTC, always from orders"] -.->|read committed state only| ORD

  SUN{"Sunday: night load has committed"} --> RCSTART["For each order-creation day in the last 30 full days: compare replica and warehouse"]
  RCSTART --> CMP["Count and checksum of order_id plus updated_at, both sides, same hash function"]
  REP -.-> CMP
  ORD -.-> CMP
  CMP --> MATCH{"Match?"}
  MATCH -->|yes| RECON
  MATCH -->|no| RECHK["Wait, then recompare once to rule out writes that landed mid-check"]
  RECHK --> MATCH2{"Still mismatched?"}
  MATCH2 -->|"no"| RECON
  MATCH2 -->|"yes, warehouse has a newer updated_at than replica"| RCALERT["Log and alert, do not reload"]
  MATCH2 -->|"yes, rows missing or older in warehouse"| RELOAD["Reload that creation day: full replica extract for the day, same stage, dedupe and MERGE rules"]
  RELOAD --> RECON
  RCALERT --> RECON
