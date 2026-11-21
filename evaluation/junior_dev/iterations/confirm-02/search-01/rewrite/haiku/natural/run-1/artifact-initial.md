# Search sync: CDC indexer and zero-downtime rebuild

## Notes

1. **Version.** Convert `commit_lsn` from `X/Y` (hex) to one 64-bit integer: `X * 2^32 + Y`. Changes in one transaction share a value. Equal versions are accepted under the "at least stored" rule, so within a transaction, partition order decides the final state.
2. **Deletes.** A hard delete (`op d`) and a row whose status is not `active` both become a delete with `version = commit_lsn`. This assumes the store keeps a version marker after a delete, so an older write arriving later is refused. If the store drops it, a stale create can bring a deleted product back. Verify this before building.
3. **Snapshot events.** Debezium's initial snapshot emits `op r`, which is not in the event contract. Treat `r` as `c`.
4. **Latency.** The 5 s measure needs the source commit timestamp (`ts_ms` in the Debezium envelope), which the current event shape does not carry. Add it. Set the index refresh interval to 1 s. Starting point for bulk batching: flush every 200 ms or 500 docs, whichever comes first.
5. **Cron first.** `indexer_cron.py` writes without a version and can overwrite newer CDC data. Stop it before the live consumer writes anything. Create alias `products_write` pointing at `products_v3` before starting. The first migration is the rebuild path, because the contents of `products_v3` are unknown (hard deletes were missed).
6. **Snapshot consistency.** Read `S = pg_current_wal_lsn()` as the first statement in the repeatable-read transaction and write snapshot docs with `version = S`. Changes committed at or before `S` are already in the snapshot. Later changes have `commit_lsn > S` and are applied. Older events are refused as stale, which is the correct result.
7. **Replay is safe, late start is not.** Replaying old events is harmless because of the version rule. The replay start is therefore set early (snapshot start minus 10 minutes). Starting late can lose changes. The replay start is fixed once recorded and never moves forward on resume.
8. **Progress stores.** Live and rebuild consumer offsets live in Kafka, one group each. Rebuild state (S, replay start, `last_id`) lives in the indexer's own Postgres, not on the catalog primary. Failed invalid documents go to `catalog.products.dlq`. The alias state lives in the search store. WAL retention is read only from `pg_replication_slots` on the primary.
9. **Isolation.** The rebuild uses its own consumer group and its own throttle, so it cannot starve the live path's 5 s target.

## Diagram

```mermaid
flowchart TD
  subgraph SRC["Source and CDC (continuous)"]
    P1["Committed change on catalog-primary"] --> P2["Replication slot search_slot<br/>holds WAL until the connector confirms it"]
    P2 --> P3["Debezium connector<br/>one event per row change"]
    P3 --> T1[("Topic catalog.products<br/>12 partitions keyed by product id<br/>7 day retention")]
    P2 --> M1{"Retained WAL for slot<br/>checked every minute"}
    M1 -->|"under 20 GB"| M1
    M1 -->|"20 GB or more"| M2["Alert ops"]
    M2 --> M3{"50 GB or more?"}
    M3 -->|"no"| M1
    M3 -->|"yes"| M4["Ops drop slot<br/>changes since then are lost<br/>index marked stale, rebuild required"]
  end

  subgraph LIVE["Live sync path (steady state)"]
    T1 -->|"one worker per partition"| L1["Live consumer group indexer-live<br/>offsets committed in Kafka"]
    L1 --> L2{"op d, or status not active?"}
    L2 -->|"no, active row"| L3["Index doc id<br/>version = commit_lsn as 64-bit integer"]
    L2 -->|"yes"| L4["Delete doc id<br/>version = commit_lsn"]
    L3 --> L5["Bulk write via alias products_write"]
    L4 --> L5
    L5 --> L6{"Result per document"}
    L6 -->|"applied"| L7["Count applied"]
    L6 -->|"409 version conflict"| L8["Count stale<br/>not an error"]
    L6 -->|"timeout, 5xx or throttled"| L9["Retry this document<br/>wait 1 s, 2 s, 4 s ... capped at 60 s<br/>partition waits, never skips ahead"]
    L9 --> L5
    L6 -->|"400 invalid document"| L10["Produce to catalog.products.dlq<br/>with error text and source offset"]
    L10 --> L11["Raise alert, carry on"]
    L7 --> L12{"Whole batch resolved?"}
    L8 --> L12
    L11 --> L12
    L12 -->|"yes, DLQ produce acked"| L13["Commit Kafka offsets for the batch"]
    L13 --> L1
  end

  subgraph REB["Rebuild path (new mapping or data loss)"]
    R0["Operator starts rebuild<br/>job id and target name recorded"] --> R1["Create products_v4 with new mapping<br/>refresh 1 s, no alias yet"]
    R1 --> R2["Record replay start<br/>topic offsets at snapshot start minus 10 min, per partition"]
    R2 --> R3["Open one REPEATABLE READ transaction on catalog-primary<br/>read S = pg_current_wal_lsn()"]
    R3 --> R4["Keyset read: active rows with id above last_id<br/>ORDER BY id, batches of 1000, at most 5000 rows/s"]
    R4 --> R5["Bulk index into products_v4<br/>version = S"]
    R5 --> R6[("Progress store<br/>job state, S, replay start, last_id")]
    R5 --> R4
    R4 -->|"no rows left"| R7["Close snapshot transaction<br/>snapshot phase done"]
    R3 -.->|"crash or connection lost"| R8["Resume: open new snapshot S2<br/>from saved last_id, replay start stays fixed"]
    R8 --> R3
    R2 --> R9["Rebuild consumer group indexer-rebuild<br/>reads topic from replay start"]
    R9 --> R10["Write rules as live path<br/>version = commit_lsn into products_v4"]
    R10 -->|"409: older than snapshot"| R11["Count stale"]
    R10 -->|"timeout, 5xx or throttled"| R12["Same backoff, never skips ahead"]
    R12 --> R10
    R10 -->|"400 invalid"| R13["DLQ and alert<br/>count gate catches the gap"]
    R10 --> R14["Commit rebuild group offsets"]
    R14 --> R9
  end

  subgraph GATE["Cutover gate"]
    R7 --> G1{"Gate: rebuild lag under 5 s on every partition<br/>and products_v4 count within 0.5% of active rows"}
    R14 --> G1
    G1 -->|"no, still catching up"| R9
    G1 -->|"no, after timeout"| G2["Reconcile sweep<br/>compare id sets, add missing, delete extra"]
    G2 --> G1
  end

  subgraph CUT["Cutover (no search downtime)"]
    G1 -->|"yes"| C1["Pause live consumer group"]
    C1 --> C2{"Rebuild offsets at or past live offsets on every partition?"}
    C2 -->|"no"| C3["Wait for rebuild group"]
    C3 --> C2
    C2 -->|"yes"| C4["One atomic alias request<br/>products and products_write both point to products_v4<br/>products_v3 stays open"]
    C4 --> C5["Set live group offsets to rebuild group offsets<br/>resume live consumer"]
  end

  subgraph STBY["Standby window, 48 hours"]
    C5 --> S1["Live consumer writes products_v4 and also products_v3<br/>commit only when both ack"]
    S1 --> S2{"Rollback needed within 48 h?"}
    S2 -->|"yes"| S3["One atomic alias request<br/>products and products_write back to products_v3<br/>v3 already current, nothing lost"]
    S2 -->|"no, 48 h passed"| S4["Stop writes to products_v3<br/>delete it"]
  end

  M4 --> R0
```

## Failure behaviour

- **Index timeout, 5xx or throttling:** retry with backoff (1 s, doubling, capped at 60 s). The partition waits and its offsets are not committed. Nothing is skipped.
- **Invalid document (400):** sent to `catalog.products.dlq` with the error, alert raised, processing continues. The DLQ produce must be acked before the offset commit.
- **Version conflict (409):** counted as stale. Not an error, and the offset is committed.
- **Indexer crash:** restart from committed offsets. Replays are safe because of versions.
- **Connector stopped:** WAL accumulates on the slot. The live index lags but loses nothing while retained WAL is under 50 GB. Alert at 20 GB.
- **Slot dropped at 50 GB:** changes since the drop are lost. The live path cannot recover alone. Mark the index stale and run the rebuild path.
- **Rebuild job crash:** resume from `last_id` with a new snapshot S2. Rows at or below `last_id` stay correct through replay, because the replay start is fixed earlier than S1.
- **Gate not met:** no switch. Run the reconcile sweep, then re-check the gate.
- **Standby write to v3 fails:** the commit of the batch waits, which keeps rollback lossless. Alert. An invalid document on v3 goes to the DLQ and the gap is repaired before any rollback.
- **Rollback:** an alias flip. After a rollback, v4 is the standby, so a new 48 h reverse standby window starts.

## Open questions

- Confirm the store keeps a tombstone version after a delete (note 2).
- Add `ts_ms` to the event contract for the latency measure (note 4).
- Confirm how the connector's snapshot events are emitted (`op r`).
- Confirm the shared Kafka brokers can absorb the replay load of the rebuild group, or set a throttle.
- Confirm the 2.5 h snapshot length against the actual active row count.
