# Search sync: change data capture and rebuild plan

This is a plan only. Nothing was run against the cluster, the connector, or the primary, so the failure behaviour and the gates below are design targets to verify.

## Key decisions before the diagram

- **Version as LSN.** Parse `commit_lsn` (`X/Y`, hex) as `(X << 32) + Y` into an unsigned 64-bit integer, and compare numerically, never as text. The store's "at least stored" rule accepts equal versions. That matters because two events for one product in the same transaction share an LSN, and they stay in order because one product always lands in one partition.
- **Deletes are versioned too.** An old delete cannot remove a newer write. Deleting an absent document counts as success.
- **Snapshot version S.** Every document from the snapshot is written with version S, the WAL LSN read as the first statement of the repeatable-read transaction. Events below S are stale and are counted. Events at or above S apply on top.
- **Lag measurement is an assumption.** The event shape in search-setup.md has no commit time. This plan assumes the Kafka record timestamp (Debezium's source commit time). Confirm that in the connector config before relying on the 5 s SLO.
- **Writes go to index names, not the alias.** The alias moves only at the switch, so the search API never sees a half-built index.
- **Rebuild needs a live stream.** The connector must be streaming from a slot created at or before S, so no commit after S is missed. This applies after an ops slot drop too.

```mermaid
flowchart TD
  subgraph LIVE["Live sync: always on"]
    direction TB
    WR["Seller or app commits a change to products<br/>trigger: any commit"] --> SLOT[("Replication slot search_slot<br/>WAL kept until the connector reads it")]
    SLOT --> DBZ["Debezium connector reads the slot<br/>one event per row change<br/>data: op, id, after, commit_lsn"]
    DBZ --> TOPIC[("Kafka catalog.products<br/>12 partitions keyed by id<br/>retention 7 days")]
    TOPIC --> POLL["Consumer group products-live polls a partition<br/>batch up to 200 events or 200 ms<br/>offset not committed yet"]
    POLL --> VER["Version = commit_lsn as 64-bit integer<br/>write applies only if version is at least stored"]
    VER --> ACT{"op is d, or status is not active?"}
    ACT -->|yes| DEL["Delete doc id with version<br/>absent doc counts as success"]
    ACT -->|no| IDX["Index doc id with version<br/>sku, title, description, price = cents / 100"]
    DEL --> BULK["Bulk write to index products_v3 by name, not alias"]
    IDX --> BULK
    BULK --> RES{"Result per item"}
    RES -->|ok| ACKD["Acked"]
    RES -->|version conflict| STALE["Stale change: count it, ack it, not an error"]
    RES -->|invalid document| DLQ[("Write to catalog.products.dlq<br/>event, error, partition, offset")]
    DLQ -->|DLQ write succeeds| ALERT["Alert: invalid document<br/>acked, carry on"]
    DLQ -->|DLQ write fails, treated as transient| BO
    RES -->|timeout, 5xx, throttled| BO["Backoff 1 s, 2 s, 4 s ... capped at 60 s<br/>pause this partition, retry failed items<br/>never skip ahead"]
    BO --> BULK
    ACKD --> COMMIT["Commit Kafka offset per partition<br/>only up to the last contiguous acked offset"]
    STALE --> COMMIT
    ALERT --> COMMIT
    COMMIT --> POLL
  end

  CUT["One-time cutover from cron<br/>stop cron after its last run<br/>start products-live from offsets 20 min before that stop<br/>versions keep older replays from winning"]
  CUT -.-> POLL

  subgraph WATCH["Monitoring: always on"]
    direction TB
    MET["Metrics: event-to-ack time, consumer lag,<br/>stale count, DLQ count"] --> SLO{"Share of changes searchable within 5 s<br/>at or above 95%?"}
    SLO -->|no| SLOA["Alert: search lag over SLO"]
    WALM["Every minute: retained WAL on search_slot<br/>pg_wal_lsn_diff of current LSN and restart_lsn"] --> W20{"Retained WAL at least 20 GB?"}
    W20 -->|yes| WA["Alert: WAL retention at 20 GB"]
    WA --> W50{"At least 50 GB?"}
    W50 -->|yes| DROP["Ops drop search_slot to protect primary<br/>connector stops, live sync stops"]
    DROP --> NEEDRB["Full rebuild is the only way back<br/>rebuild creates a new slot"]
  end

  subgraph REBUILD["Rebuild: manual trigger for new mapping or data loss"]
    direction TB
    START["Operator starts rebuild<br/>control record: state starting, candidate products_v4"] --> STREAM["Connector streaming from search_slot<br/>create the slot first if it was dropped<br/>events must flow before the snapshot"]
    STREAM --> CANDIDATE["Create index products_v4 with new mapping<br/>not on alias products"]
    CANDIDATE --> REPLAY["Record replay start offset per partition<br/>control record"]
    REPLAY --> SNAP["Open one repeatable-read transaction on catalog-primary<br/>first statement reads current WAL LSN = S<br/>control record: snapshot_lsn S"]
    REPLAY -.->|offsets older than 7 day retention| EXPIRED["Replay offsets expired<br/>drop products_v4 and restart from a new snapshot"]
    SNAP --> READ["Read active rows by id<br/>keyset pages of 1000, about 5000 rows/s<br/>about 2.5 h as briefed"]
    READ --> SNAPW["Bulk write to products_v4 with version S<br/>retry transient errors, DLQ invalid docs"]
    SNAPW --> CKPT["Checkpoint last id in control record<br/>for monitoring only, not for resume"]
    CKPT --> READ
    READ -->|no rows left| SNAPDONE["Close snapshot transaction<br/>control record: snapshot_done, row count"]
    SNAP -.->|reader crashes, snapshot lost| LOST["Drop products_v4 contents<br/>reset control record<br/>restart needs a new DBA-approved snapshot"]
    REPLAY --> CATCH["Consumer group products-rebuild-v4 from replay offsets<br/>same version rule, retry and DLQ rules"]
    CATCH --> LAGC["Catch-up applies every event from the replay start<br/>events below S are stale and counted"]
    SNAPDONE --> GATE{"Gate: snapshot done, lag under 5 s,<br/>products_v4 count within 0.5% of active rows?"}
    LAGC --> GATE
    GATE -->|no, lag or count| WAITG["Keep consuming and re-check<br/>alert if it does not converge<br/>do not switch"]
    WAITG --> GATE
    GATE -->|yes| SWAP["Atomic alias swap on products<br/>remove products_v3 and add products_v4 in one request"]
    SWAP --> SERVE["products_v4 serves<br/>group products-rebuild-v4 is now the live group"]
    SWAP --> KEEP["products-live keeps writing products_v3 for 48 h<br/>rollback = swap alias back, no changes lost"]
    KEEP --> RETIRE["After 48 h: stop products-live and delete products_v3"]
  end
```

## Notes on failures and open items

- **Connector down:** the slot keeps WAL and no data is lost until ops drop the slot at 50 GB. The 20 GB alert is the warning.
- **Index down or throttled:** the partition pauses, its offset does not move, and lag grows until the index recovers. The 5 s SLO alert fires first.
- **Invalid documents:** they go to the DLQ and processing continues. Replaying the DLQ after a fix is manual and is not covered by the brief.
- **Snapshot reader crash:** the snapshot cannot be resumed, so the candidate is discarded and a new snapshot is needed. The checkpoint only reports progress.
- **Count gate is weak:** 0.5% of 40 million is about 200,000 documents of slack, and a count does not detect wrong content. A sampled field comparison would add confidence, but the brief does not ask for one.
- **Rollback caveat:** the 48-hour window protects changes made after the switch. `products_v3` still carries cron-era state, so documents for rows hard-deleted before the switch may still be present. Either reconcile `products_v3` against active ids before relying on rollback, or accept that risk explicitly.
- **Snapshot load:** the one repeatable-read transaction holds back vacuum on the primary for the whole run. The DBA has already approved this.