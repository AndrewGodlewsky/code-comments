## Nightly orders ETL: app replica to warehouse

**Where state lives.** Everything is in the warehouse. The app database is read-only to us.
- `etl_watermark`: one row holding W, the extract upper bound of the last successful attempt.
- `etl_runs`: one row per attempt, holding the night, attempt number, lower bound, upper bound and status.
- `stg_orders`: scratch copy of one extract. It is emptied at the start of every attempt and every reconciliation reload. Dashboards never read it.
- `fact_orders`: one row per `order_id`, holding the latest version plus `is_deleted`. It is the only table dashboards read.

```mermaid
flowchart TD
  T1(["02:00 UTC: scheduler starts tonight's load"]) --> A1

  subgraph ATTEMPT["One attempt (at most 3 per night)"]
    A1["Step 1: insert etl_runs row: attempt n, status running<br/>TRUNCATE stg_orders"]
    A2["Step 2: read W from etl_watermark<br/>lower = W minus 2 h"]
    A3["Step 3: open one read snapshot on the replica<br/>upper = replica clock at snapshot start<br/>select orders with updated_at after lower, up to upper<br/>is_deleted = deleted_at is not null"]
    A4["Step 4: bulk-copy extracted rows into stg_orders"]
    A5["Step 5: ONE warehouse transaction<br/>MERGE stg_orders into fact_orders on order_id:<br/>no match: insert<br/>match, staged updated_at newer: update<br/>match, not newer: skip<br/>set W = upper in etl_watermark<br/>set etl_runs row to succeeded<br/>COMMIT"]
    A1 --> A2 --> A3 --> A4 --> A5
  end

  ATTEMPT -- "any step fails: nothing committed to fact_orders or W" --> F{"Fewer than 3 attempts tonight?"}
  F -- "yes" --> WAIT["Mark etl_runs row failed<br/>wait 15 min"]
  WAIT --> A1
  F -- "no" --> PAGE["Mark etl_runs row failed<br/>page on-call"]

  A5 --> SUN{"Sunday?"}
  SUN -- "no" --> DONE(["Night finished"])
  SUN -- "yes" --> R1["Reconcile the last 30 order-creation days<br/>per day: row count and checksum of order_id + updated_at<br/>replica vs fact_orders"]
  R1 --> R2{"Any day mismatched?"}
  R2 -- "no" --> DONE
  R2 -- "yes" --> R3["TRUNCATE stg_orders<br/>re-extract every order created on a mismatched day<br/>same conditional MERGE, own transaction<br/>W is NOT changed"]
  R3 --> DONE
  R1 -- "fails" --> RA["Post to data-alerts channel<br/>tonight's committed load stands"]
  R3 -- "fails" --> RA

  T2(["06:00 UTC: scheduler runs the deadline check"]) --> C{"Succeeded etl_runs row for tonight?"}
  C -- "yes" --> QUIET(["No action"])
  C -- "no" --> STALE["Post staleness alert to data-alerts channel<br/>dashboards keep showing the last committed fact_orders"]
```

**Notes**
- **Late rows.** Bulk imports hold transactions open for up to 90 min, and `updated_at` is stamped at write time, not at commit. A bulk-imported row can therefore appear on the replica up to 90 min after its `updated_at`. Each night starts at W minus 2 h, so it re-reads the last 2 h of the previous night's window and picks such rows up. A row that becomes visible too late even for that lookback (for example while the replica is behind) is not picked up by any nightly extract unless the order is written again. If that order was created in the last 30 days, the next Sunday reconciliation finds the mismatch on its creation day and reloads that day. Orders created earlier are not checked.
- **Updates after export.** Every app write bumps `updated_at`. Deletes are always soft: the app sets `deleted_at`, which is also a write, and never hard-deletes a row. The next night extracts the changed row again, and the MERGE replaces the older version. Soft deletes arrive as `is_deleted = true`. No row is ever removed from `fact_orders`.
- **Why overlap and retries are safe.** They bring back copies that are already loaded. The MERGE skips any copy that is not newer, so each `order_id` still has exactly one row.
- **Failure.** Step 5 is a single transaction, so a failed attempt leaves `fact_orders` and W unchanged. The next attempt empties `stg_orders`, reads the same W, takes a fresh upper bound and re-extracts. A night gets three attempts in total, 15 min apart. After the third failure, on-call is paged.
- **06:00 deadline.** Dashboards refresh at 06:00 UTC regardless of the load. Step 5 commits everything at once, so they see either all of tonight's changes or none of them. If `etl_runs` has no succeeded row for tonight, a staleness alert goes to #data-alerts. A load that commits after 06:00 is kept.
- **Reconciliation** runs only after Sunday's load succeeds. It reuses `stg_orders` and the same conditional MERGE, and it never changes W. If it fails, it posts to #data-alerts, and the nightly load stays committed.
