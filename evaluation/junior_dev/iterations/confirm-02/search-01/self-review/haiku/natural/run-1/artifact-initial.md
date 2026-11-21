# Search sync plan: CDC indexer and zero-downtime rebuild

## Notes before the diagram

**Decisions**
- **Version:** convert `commit_lsn` from `"X/Y"` (hex) to an unsigned 64-bit integer: `(X << 32) | Y`. Use external versioning, so a write applies only if its version is at least the stored one. An equal version re-applies harmlessly, which makes redelivery safe.
- **Concrete index names:** the sync path writes to `products_v3` (or `products_v4` during a rebuild) by name. Only the alias swap touches the alias `products`.
- **Rows that leave `active`:** drafts and archived rows are deleted from the index, not just skipped, so the search rule holds for rows that stop being active.
- **Delete of a missing id:** a not-found result counts as applied.
- **Kafka offsets:** commit the highest contiguous acknowledged offset per partition. A DLQ write counts as an acknowledgement.
- **Cron:** disable `existing/indexer_cron.py` before the live group starts writing `products_v3`. Its unversioned writes could overwrite versioned documents. Remove it at cutover.
- **Latency:** the 5 s target covers connector lag, Kafka, batching, and index refresh. Set the refresh interval to 1 s or less. Measure with canary rows updated about once a second in a reserved id range, and alert when p95 stays above 5 s for 10 minutes.

**Assumptions to verify before build (hypotheses, not demonstrated)**
1. The store keeps delete versions (tombstones) longer than the 2.5 h backfill. Many stores drop tombstones after about 60 s. If they drop earlier, a backfill write at version S could bring back a row deleted after S. The reconcile step is the only guard in that case.
2. The snapshot point S may not match the topic offsets exactly. A commit in flight at S can have a `commit_lsn` below S while missing from the snapshot, and the version rule cannot catch that. Fixes: create a slot with an exported snapshot (needs DBA approval for a second slot), or rely on reconcile.
3. Documents written by the old cron have no version. Confirm that the store accepts a first versioned write over them.

## Diagram

```mermaid
flowchart TD
  subgraph LIVE ["A. Live sync, steady state"]
    PG[("catalog-primary: products table")]
    SLOT[("Replication slot search_slot: WAL kept until the connector confirms it")]
    DBZ["Debezium connector: reads slot, emits one event per committed row change with commit_lsn"]
    TOPIC[/"Topic catalog.products: 12 partitions keyed by product id, 7 day retention"/]
    GRP["Indexer service, group products-indexer-v3: one worker per partition, in offset order"]
    ROUTE{"Delete event, or after.status is not active?"}
    DELREQ["Delete request for id, version = commit_lsn as integer"]
    DOCREQ["Index request for id, version = commit_lsn, doc built from after row"]
    BATCH["Per-partition batch: flush at 500 docs or 100 ms"]
    BULK["_bulk to concrete index products_v3, never the alias"]
    RES{"Result for each document"}
    ACK["Applied: searchable after next refresh"]
    STALE["Version conflict: stale change, counted, not an error"]
    NF["Delete of missing id: already gone, counted as applied"]
    RETRY["Timeout, 5xx or 429: wait 1 s, doubling, cap 60 s, resend the failed documents only"]
    INVALID["Index refuses document as invalid"]
    DLQ[/"Topic catalog.products.dlq: error text plus original event"/]
    ALERT["Alert raised, processing continues with next event"]
    COMMIT["Commit Kafka offset: highest contiguous acknowledged offset per partition"]
    METRIC["Metrics: commit to searchable latency p95, consumer lag, stale count, DLQ count"]
  end

  subgraph GUARD ["B. WAL guard, runs alongside A"]
    WATCH["Watchdog: retained WAL bytes for search_slot, checked every minute"]
    WAL20["Alert at 20 GB retained"]
    DROP["At 50 GB ops drop search_slot to protect the primary"]
    LOST["Live stream ends: only a full rebuild in C brings search back"]
  end

  subgraph REB ["C. Rebuild into products_v4, zero downtime"]
    RB0["Trigger: operator starts rebuild for a new mapping or after data loss"]
    RB1["Create products_v4 with new mapping, no alias; products still on products_v3"]
    RB2["Open REPEATABLE READ transaction on primary; record S as pg_current_wal_lsn and topic offsets taken just before"]
    RB3["Same transaction: count active rows as N"]
    RB4["Start group products-indexer-v4 at recorded offsets, writes to products_v4 with the same version rules"]
    RB5["Backfill: read active rows by id range at up to 5000 rows/s, write each with version = S"]
    STATE[("Rebuild state table in ops DB: job id, S, offsets, last acknowledged id")]
    RB6{"Backfill finished?"}
    RB7["Catch-up: v4 group lag measured against topic end"]
    RB8{"Gate: lag under 5 s AND products_v4 count within 0.5 percent of N"}
    RB9["Reconcile: compare id sets of products_v4 and primary active rows, delete extras, report misses"]
    RB10["Alias swap in one request: remove products_v3, add products_v4 on products"]
    RB11["Keep group products-indexer-v3 running for 48 h, so products_v3 stays current"]
    RB12["After 48 h: stop v3 group, delete products_v3"]
    ROLL["Rollback at any time in 48 h: point alias back to products_v3, already current"]
  end

  PG --> SLOT --> DBZ --> TOPIC --> GRP --> ROUTE
  ROUTE -->|"no"| DOCREQ
  ROUTE -->|"yes"| DELREQ
  DOCREQ --> BATCH
  DELREQ --> BATCH
  BATCH --> BULK --> RES
  RES -->|"2xx"| ACK
  RES -->|"409"| STALE
  RES -->|"404 on delete"| NF
  RES -->|"timeout 5xx 429"| RETRY
  RETRY --> BULK
  RES -->|"400 invalid"| INVALID --> DLQ --> ALERT
  ACK --> COMMIT
  STALE --> COMMIT
  NF --> COMMIT
  ALERT --> COMMIT
  COMMIT --> METRIC

  SLOT -.-> WATCH
  WATCH -->|"20 GB"| WAL20
  WATCH -->|"50 GB"| DROP --> LOST

  RB0 --> RB1 --> RB2 --> RB3 --> RB4
  PG -.->|"one long read, 5000 rows/s"| RB2
  RB2 --> RB5
  RB5 -->|"timeout 5xx: backoff, cursor held"| RB5
  RB5 -.-> STATE
  RB5 --> RB6
  RB6 -->|"no: resume from cursor"| RB5
  RB6 -->|"yes"| RB7
  TOPIC -.->|"offsets from recorded point"| RB4
  RB4 -.-> STATE
  RB4 --> RB7
  RB7 --> RB8
  RB8 -->|"fail: keep catching up, alias unchanged"| RB7
  RB8 -->|"pass"| RB9 --> RB10 --> RB11 --> RB12
  RB11 -.->|"v3 group keeps consuming"| GRP
  RB10 -.->|"switch back target"| ROLL
  LOST -.->|"rebuild needed, new S"| RB0
```

## Notes after the diagram

| Failure | What happens |
|---|---|
| Index timeout, 5xx or 429 (live) | The partition holds its offset and retries with backoff from 1 s to a 60 s cap. Nothing is skipped. Search serves slightly stale data. |
| Index refuses a document as invalid | The event goes to `catalog.products.dlq` with the error text, an alert is raised, and processing continues. The offset moves only after the DLQ write is acknowledged. |
| Version conflict | Counted as stale and acknowledged. Not an error. |
| Indexer crash or rebalance | Replay from the last committed offset. Versioned writes make replay harmless. |
| Connector stopped | WAL accumulates on the primary. Alert at 20 GB. At 50 GB ops drop the slot, the live stream ends, and only a rebuild restores sync. |
| Rebuild backfill crash | Resume from the cursor in the state table, using the same S. Writes are idempotent. |
| Index down during rebuild | Alias still points at `products_v3`, so search is unaffected. Backfill backs off. |
| Rebuild gate fails | Alias unchanged. Keep catching up and investigate. |
| Rollback within 48 h | Point the alias back to `products_v3` in one request. It has already consumed every change because its group kept running. |

**Known limit:** the 48 h rollback restores changes made after the switch. Drift that the old cron left in `products_v3` (for example, missed hard deletes) is not repaired by the switch-back.