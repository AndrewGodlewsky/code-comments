## Product search sync: CDC live path and zero-downtime rebuild

**Read first**
1. Source of truth is `products` on catalog-primary. The index is a derived copy that holds only rows with `status = active`. A delete, or a change to `draft` or `archived`, removes the document.
2. Every write to the index carries a version. For a change it is the change's `commit_lsn`. For a document copied during a rebuild it is the snapshot position S. The index applies a write only if its version is at least the stored one. An older change that arrives late is therefore rejected as stale (counted, not an error), and applying any event twice is harmless.
3. Progress lives only in Kafka. Each physical index has its own consumer group (`indexer-products_v3`, `indexer-products_v4`), and that group's committed offsets record how far the index has been brought up to date. The indexer keeps no other state.

```mermaid
flowchart TD
  API["Search API"] -->|"every query"| AL["Alias products<br/>points at products_v3 until the switch"]

  subgraph LIVE["1. Live sync - always running, one consumer group per index"]
    A["App commits a change to products"] --> B["Postgres WAL, held by slot search_slot"]
    B -->|"connector reads WAL"| C["CDC connector emits one event per row change<br/>op, id, after row, commit_lsn"]
    C --> D["Kafka catalog.products<br/>12 partitions keyed by product id, kept 7 days"]
    D -->|"consumer group of this index"| E{"What does the event say?"}
    E -->|"c or u with status active"| F["Upsert doc, version = commit_lsn"]
    E -->|"d, or status draft or archived"| G["Delete doc, version = commit_lsn"]
    F --> H["Add to batch<br/>flush at 500 events or 1 s"]
    G --> H
    H --> I["Bulk write to this group's index"]
    I --> J{"Index reply"}
    J -->|"all ok, or version conflict = stale, counted"| K["Commit the batch's offsets to Kafka"]
    J -->|"a doc refused as invalid"| L["Send event + error to catalog.products.dlq<br/>raise alert"]
    L --> K
    J -->|"timeout, 5xx or throttled"| M["Pause partitions, wait 1, 2, 4 ... max 60 s<br/>retry the same batch, nothing committed"]
    M --> I
    K -->|"next batch"| D
  end

  B -.->|"connector stopped: WAL piles up"| W["Retained WAL: alert at 20 GB<br/>at 50 GB ops drop the slot, pending changes lost<br/>recover: new slot and connector, then section 2"]

  subgraph REBUILD["2. Full rebuild - search stays up"]
    R1["Create products_v4 with the new mapping<br/>alias untouched"] --> R2["Record end offsets O of catalog.products"]
    R2 --> R3["Open one repeatable-read snapshot on catalog-primary<br/>first statement reads WAL position S"]
    R3 --> R4["Copy active rows in id order into products_v4<br/>max 5,000 rows/s, about 2.5 h, version = S"]
    R4 --> R5["Start group indexer-products_v4 at offsets O<br/>runs the section 1 loop against products_v4"]
    R5 --> R6{"Lag under 5 s and doc count within<br/>0.5 percent of active rows?"}
    R6 -->|"not yet, keep consuming"| R5
    R6 -->|"yes"| R7["Atomically move alias products to products_v4"]
    R7 --> R8["48 h rollback window<br/>indexer-products_v3 keeps applying changes to products_v3<br/>rollback = move alias back"]
    R8 --> R9["After 48 h: stop indexer-products_v3<br/>delete products_v3"]
    R1 & R2 & R3 & R4 & R5 -.->|"any step fails"| RF["Alias never moved, search keeps using v3<br/>delete products_v4 and its group, start again"]
  end

  R7 -.-> AL
```

**Notes**
- **Why the rebuild loses nothing:** O is recorded *before* the snapshot opens. Any change the snapshot does not contain was committed after it, so its event is in Kafka after O and gets replayed. Some replayed changes are already in the snapshot. Their commit_lsn is no later than S, so they are either rejected as stale or rewrite the same data. Replay starts only after the copy has finished, so a later delete always lands after the copied document and cannot be overwritten by it. The copy takes about 2.5 h, well inside Kafka's 7-day retention.
- **Indexer crash:** the indexer restarts from its group's last committed offsets and writes the uncommitted batch again with the same versions. This leaves the index unchanged or brings it to the same state.
- **Connector lag or outage:** search goes stale but never wrong. When the connector returns, it catches up from the slot, unless the slot was dropped at 50 GB. In that case a new slot and connector are set up first, and then the section 2 rebuild runs.
