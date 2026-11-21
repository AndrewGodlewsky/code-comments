# Search sync: change data capture plan

**Today:** a cron job (`existing/indexer_cron.py`) polls `products` every 15 minutes and writes straight to the index `products_v3`. It misses hard deletes, overlapping runs can write older data last, and changes take up to 15 minutes to appear.

**This plan:** Debezium reads every committed change from Postgres and publishes it to the Kafka topic `catalog.products`. A new indexer service reads the topic and writes each change to the search index, using the change's `commit_lsn` as the document version, so older data can never overwrite newer data. The cron job is retired. A separate rebuild controller builds a new index beside the live one, replays the topic into it, and moves the alias `products` to it in one atomic step. Target: 95% of committed changes searchable within 5 seconds.

## Terms

- **WAL**: Postgres's log of committed changes. A replication slot (`search_slot`) makes Postgres keep the WAL until the slot's reader has confirmed it.
- **Debezium (the CDC connector)**: reads the slot and writes one event per row change to `catalog.products`: 12 partitions, keyed by product id, so all changes to one product are in one partition in commit order, retention 7 days. Event: `{op: c|u|d, id, after: full row or null for d, commit_lsn}`.
- **`commit_lsn`**: the WAL position of the committing transaction. Larger means committed later. It is used as the document version (converted to a 64-bit integer).
- **Version rule**: the search store applies a write only if its version is at least the stored version. Otherwise it returns a version-conflict error for that document. Here a conflict means the change is stale.
- **Alias**: the name `products`, which the search API queries. It points at one concrete index (`products_v3`, later `products_vN`). Moving it is atomic: a query goes to the old index or the new one, never neither.
- **Consumer group**: Kafka's record of how far one reader has read the topic (its committed offsets). The indexer runs one group per target index, e.g. `indexer-products_v3`. Groups are independent and all run all the time. Debezium and the topic know nothing about groups.
- **DLQ**: the topic `catalog.products.dlq`, where events the index refuses as invalid are parked with their error.
- **Rebuild controller**: a small program, separate from the indexer, that the operator starts. It runs the rebuild. The indexer only consumes events.
- **`sync_control`**: a small control index in the search cluster. It holds the rebuild's progress.
- **Gate**: the conditions that must hold before the alias moves (see Rebuild).
- **Canary**: one dedicated `active` product row used to measure delay end to end.

## Flowchart

```mermaid
flowchart TD
  subgraph PG["Postgres primary: catalog-primary"]
    W["Committed change on products<br/>insert, update or hard delete"] --> WAL["WAL kept for slot search_slot"]
    SNAP["Rebuild only: one repeatable-read snapshot<br/>status = active rows only, capped at 5,000 rows/s"]
  end

  subgraph WALGUARD["WAL guard: a monitoring check on pg_replication_slots, every minute, alerts ops on-call"]
    WMON{"Retained WAL<br/>of search_slot"}
    WMON -->|"under 20 GB"| WOK["No action"]
    WMON -->|"20 GB or more"| WALERT["Alert: check connector and Kafka, restart connector"]
    WMON -->|"50 GB: ops drop the slot"| SLOTLOST["Connector fails: slot missing<br/>Alert: full rebuild required"]
  end
  WAL -.->|"pg_replication_slots"| WMON
  SLOTLOST -->|"only way back"| TRIG

  WAL -->|"streamed on commit"| CDC["Debezium connector<br/>snapshot.mode never, tombstones off"]
  CDC -->|"one event per change<br/>op, id, after, commit_lsn"| TOPIC[("Topic catalog.products<br/>12 partitions keyed by id<br/>retention 7 days")]
  CDC -.->|"after Kafka ack, confirms LSN"| SLOTPOS[("Progress: slot confirmed_flush_lsn")]
  CDC -->|"connector error or Kafka down"| CDCFAIL["Connector stops, WAL grows<br/>feeds the WAL guard"]
  CDCFAIL -.-> WMON

  subgraph LIVE["Indexer service: one consumer group per target index, e.g. indexer-products_v3"]
    POLL["Poll batch from the group's partitions<br/>up to 500 events or 200 ms"]
    MAP["Map each event, version = commit_lsn<br/>c or u with status active: index full doc<br/>c or u with other status, or d: delete<br/>null tombstone: ignore"]
    BULK["Bulk write to the concrete index<br/>never through the alias"]
    RES{"Result for each document"}
    COMMIT["Commit Kafka offsets up to the last<br/>resolved event of each partition"]
    STALE["Version conflict: event is stale<br/>count stale_total, not an error"]
    BACK["Timeout, 5xx or throttle: retry only<br/>the failed docs, same order, same version<br/>wait 1 s, 2 s, 4 s ... capped at 60 s<br/>partition paused, never skip ahead"]
    BACKALERT["Alert if stuck at the 60 s cap<br/>for more than 5 minutes"]
    DLQ["Invalid document: produce event + error<br/>to catalog.products.dlq, wait for ack<br/>if the produce fails: same backoff as a transient failure<br/>raise alert, carry on"]
    OFFS[("Progress: consumer group offsets")]
    CRASH["Indexer crash or rebalance:<br/>resume from committed offsets<br/>replayed events are harmless<br/>equal version is accepted"]
    POLL --> MAP --> BULK --> RES
    RES -->|"ok"| COMMIT
    RES -->|"409 conflict"| STALE --> COMMIT
    RES -->|"transient failure"| BACK --> BULK
    BACK -.-> BACKALERT
    RES -->|"rejected as invalid"| DLQ --> COMMIT
    COMMIT -->|"next batch"| POLL
    COMMIT -.-> OFFS
    CRASH --> POLL
  end
  TOPIC --> POLL
  BULK --> V3[("Live index products_v3<br/>alias products points here")]
  ALIAS["Search API queries alias products"] --> V3

  subgraph REB["Rebuild, run by the rebuild controller: new mapping, data loss, slot dropped, or group past 7-day retention"]
    TRIG["Trigger: operator starts the rebuild controller"]
    FIX["If slot was dropped: recreate search_slot<br/>and restart connector first<br/>the slot must exist before the snapshot"]
    R1["Create products_vN: refresh off, 0 replicas<br/>write rebuild record to sync_control"]
    R2["Record end offsets of all 12 partitions<br/>= start offsets, saved to sync_control"]
    R3["Open snapshot, load active rows in id order<br/>bulk to products_vN at version 0<br/>save id cursor and row count"]
    LOADFAIL["Loader crash or snapshot lost:<br/>controller alerts search on-call<br/>snapshot cannot be resumed<br/>operator restarts: delete products_vN,<br/>start again under a new name and new start offsets"]
    R4["Load finished: restore refresh 1 s and replicas<br/>start group indexer-products_vN<br/>at the saved start offsets"]
    GATE{"Gate checked every minute<br/>lag under 5 s, doc count within 0.5%<br/>of active row count, no unreviewed DLQ events<br/>3 checks in a row"}
    WAITG["Keep catching up<br/>alert if gate not met after 6 h"]
    SWAP["One atomic alias request:<br/>remove products_v3, add products_vN<br/>record switch time in sync_control"]
    HOLD["Old index keeps its own group<br/>and stays in sync for 48 h"]
    RB{"Problem within 48 h?"}
    ROLL["Roll back: confirm old group lag under 5 s,<br/>then atomic alias swap back<br/>no change is lost<br/>new index and its group are kept until a person deletes them"]
    RETIRE["After 48 h: delete old index<br/>stop and delete its consumer group"]
    SC[("Progress: sync_control record<br/>rebuild id, start offsets, id cursor,<br/>counts, gate state, switch time")]
    TRIG --> FIX --> R1 --> R2 --> R3
    TRIG -->|"slot intact"| R1
    R3 -->|"snapshot read"| SNAP
    R3 --> R4
    R3 -->|"failure"| LOADFAIL --> R1
    R4 --> GATE
    GATE -->|"not met"| WAITG --> GATE
    GATE -->|"met"| SWAP --> HOLD --> RB
    RB -->|"yes"| ROLL
    RB -->|"no"| RETIRE
    R1 -.-> SC
    R2 -.-> SC
    R3 -.-> SC
    SWAP -.-> SC
  end

  R1 -->|"create"| VN[("New index products_vN<br/>invisible to search")]
  R3 -->|"bulk"| VN
  TOPIC -->|"read from saved start offsets"| R4
  R4 -->|"same loop as LIVE"| POLL
  SWAP -->|"alias moves"| ALIAS
  SWAP -.-> VN
  ROLL -.-> ALIAS
```

## Notes: how the system runs

### Live path

1. **Change captured.** A commit on `products` goes to the WAL, then Debezium, then `catalog.products`. Debezium confirms its position to the slot only after Kafka acknowledges. If the connector or Kafka fails, the connector stops and WAL grows. Restarting it resumes from the slot's confirmed position, so nothing is lost.
2. **Batch read.** The indexer polls up to 500 events or 200 ms. Progress is kept in the group's committed offsets.
3. **Mapping.** The document id is the event's `id`, which every event carries, so a delete (where `after` is null) still knows what to remove.
   - Create or update with status `active`: index the full document.
   - Create or update with any other status, or a hard delete (`op = d`): delete the document. This keeps the search rule that only `active` rows appear.
   - A null-value tombstone record is ignored.
   - Each write carries `commit_lsn` as its version, deletes included. Events for one product arrive in commit order, so the last event wins. For example, active, inactive, active gives index, delete, index with rising versions, and the product ends in the index.
4. **Bulk write** to the concrete index, never the alias.
5. **Result handling.** Per document:
   - Written: done.
   - Version conflict: the change is stale. Count it in `stale_total` and move on. This is not an error.
   - Transient failure (timeout, 5xx, throttling): retry only the failed documents, same order, same versions, waiting 1 s, 2 s, 4 s and so on, capped at 60 s. The partition stays paused and the indexer never skips ahead. Alert if stuck at the cap for more than 5 minutes.
   - Refused as invalid: produce the original event and the error to the DLQ, wait for the ack, alert the search on-call and carry on. A later valid change to the same product is still applied. If producing to the DLQ fails (for example Kafka is down), treat it as a transient failure: same backoff, partition paused, offsets not committed.
6. **Offset commit.** Offsets are committed only after every document up to them is acknowledged: written, stale, or confirmed in the DLQ.
7. **Crash or rebalance.** The indexer resumes from the committed offsets. Replays are harmless because an equal version is accepted and older versions conflict. A replay may briefly bring a document back and then delete it again. The end state is correct.

The DLQ keeps the original event and its `commit_lsn`. After the cause is fixed, a person can replay it by hand. If a newer change was already applied, the replay is just stale.

### The 5-second target

Budget for 95% of changes: capture and Kafka about 1 s; indexer batch wait 0.2 s; bulk write under 1 s; index refresh 1 s (set `refresh_interval` to 1 s on every live index). That leaves about 1.5 s of slack.

Measure it end to end with the canary: a probe updates a counter in the canary row's description in Postgres every 30 s, then polls the alias `products` until it sees the counter and records the delay. It alerts the search on-call if the 95th percentile goes above 5 s, or if one update is not visible after 30 s. The canary needs an owner and has to be excluded from real results.

### Rebuild

The operator starts the rebuild controller. It runs steps 1 to 4, then checks the gate and moves the alias. Triggers: a new mapping, data loss, a dropped slot, or a group that was down longer than the 7-day retention.

1. **Create** `products_vN` with refresh off and no replicas, and write a rebuild record to `sync_control`. If the slot was dropped, first recreate `search_slot` and restart the connector: the slot must exist before the snapshot so everything after it is retained.
2. **Record** the end offsets of all 12 partitions. These are the start offsets. Save them in `sync_control`.
3. **Load.** Open one repeatable-read snapshot on the primary and load the `active` rows in id order into `products_vN` at version 0. The DBA's read cap is 5,000 rows/s, about 2.5 hours for the active rows. Save the id cursor and row count. The long snapshot opens no second replication slot, so it adds no WAL risk, but it delays vacuum on the primary. Watch for bloat during the load.
4. **Catch up.** When the load finishes, restore refresh to 1 s and the replicas. Start the group `indexer-products_vN` at the saved start offsets. It uses the live loop above.
5. **Gate**, checked every minute. All must hold on 3 checks in a row:
   - Lag under 5 s. Lag is the time between the commit of the newest event the new group has applied and the commit of the newest event now in the topic. The controller reads both from Kafka. A group at the end of every partition has zero lag.
   - Doc count of `products_vN`, read from the search store, within 0.5% of the active row count. The active row count is the snapshot count plus created minus deleted from the bulk results. This avoids a second heavy read on the primary. If the DBA allows a short `count(*)`, add it as a cross-check.
   - No events in `catalog.products.dlq` from this group since its start offsets, unless a person marked them reviewed in `sync_control`.
   
   Alert if the gate is not met after 6 h. A person approves the first switch. After that the controller can switch on its own.
6. **Switch.** One atomic alias request removes `products_v3` and adds `products_vN`. Record the switch time in `sync_control`.
7. **Hold 48 h.** The old index keeps its own group and stays in sync. Rollback is an atomic alias swap back, after checking that the old group is under 5 s behind. Users see the old index or the new one, never neither. After a rollback the new index and its group stay running for inspection until a person deletes them. After 48 h without a rollback, delete the old index and its group.

The live index is not touched during the build. It keeps serving search and, after the first go-live, is kept current by its own group. Before the first go-live it is still fed by cron, as today.

**Why this order is safe**
- Offsets are read before the snapshot opens, so any change committed after the snapshot is at or after the saved offsets.
- Events committed before the snapshot that get replayed carry the same or older state, and ordering within a key means the last event wins. This includes changes between recording the offsets and opening the snapshot: the snapshot already has them and the replay applies them again in order.
- A replayed delete for a document never loaded (deleted before the snapshot) does nothing. A replayed delete for a loaded row removes it.
- Version 0 for snapshot rows means any replayed event can overwrite them.
- Replay starts only after the load finishes, so a delete is never applied before a snapshot row that would then wrongly be kept.
- Catch-up is cheap: 2.5 h at 300 writes/s peak is about 2.7M events.

## Failure handling

| What fails | What happens |
|---|---|
| Connector crash or Kafka outage | Connector stops, WAL grows. WAL guard alerts at 20 GB. Fix Kafka first if it is still down, then restart the connector. It resumes from the slot position with no loss. |
| Retained WAL reaches 50 GB | Ops drop the slot. The connector fails. A full rebuild is the only way back. Updates between the drop and the new slot are lost, so the old index is not a clean rollback target for that gap. |
| Index transient failure | Backoff retry, partition paused, never skip ahead (see Live path, step 5). |
| Invalid document | DLQ, alert, carry on. |
| Indexer crash or rebalance | Resume from committed offsets. |
| Group down longer than 7-day retention | Full rebuild. |
| Snapshot loader crash or snapshot lost | The snapshot cannot be resumed, because a partial index could hold rows deleted since. The controller alerts the search on-call. The operator restarts the rebuild: delete `products_vN`, start again under a new name with new start offsets. A person decides when, because a restart costs another 2.5 h of reads on the primary. The cursor in `sync_control` is for visibility, not resuming. |
| Gate not met | Keep catching up. Alert after 6 h. |
| Problem within 48 h of the switch | Roll back as in Rebuild step 7. |

## Notes: how it is built and rolled out

**First go-live (retiring cron)**
1. Deploy the connector and the indexer.
2. Run a rebuild to create `products_v4`.
3. At the switch, stop the cron job and start the group `indexer-products_v3` for `products_v3` at the same saved start offsets. This keeps `products_v3` in sync only so that a rollback within 48 h loses no change.
4. The fallback still has its old gaps, such as ghost hard-deleted rows.

**Settings to confirm**
- Debezium `snapshot.mode` must not snapshot the 40M rows into the topic. Turn tombstones off. If they stay on, the indexer ignores null-value records.
- Update events must carry the full `description`. By default Postgres omits unchanged large (TOAST) columns and Debezium emits a placeholder. If so, set `REPLICA IDENTITY FULL` on `products`. This increases WAL volume, so re-check the 20 GB alert level.
- The brief says the load takes about 2.5 h. 40M rows at 5,000/s is about 2.2 h. Treat 2.5 h as a conservative budget.
- The Kafka cluster (3 brokers) is shared with other teams. Agree quotas and the topic and DLQ settings with them.

## Open questions

- A rebuild for a new mapping needs one indexer build that can write both the old and new document shapes during the 48 h hold, because the document mapping is per target index.
- How long does the search store remember the version of a deleted document? The plan relies on in-order replay and does not need it, but a longer memory gives extra protection.
- Documents written by cron into `products_v3` carry no version. Confirm the store treats an unversioned document as older than any `commit_lsn`.
- Not decided: who is on the search on-call rota, and which alerting system the WAL guard, DLQ and canary alerts use.
- Not decided: who watches `stale_total` and what level means something is wrong. A high count is normal while a new group replays, so any alert level must allow for that.
- Not decided: how the canary product is excluded from real search results (for example a filter in the search API).
