## Plan notes

So the main thing is the alias `products`. The Search API always reads it, and we flip it (atomic) from products_v3 to the new one once that is caught up, meaning lag < 5 s AND count within 0.5 percent of active rows. Before that, the reindexer has to fill the new index (v4, or "shadow index", or "the rebuild target") from a repeatable-read snapshot on catalog-primary, max 5,000 rows/s, ~2.5 h. Each copied doc gets version S, the WAL position read as the first statement of the snapshot. The sync worker for v4 (its own consumer group, indexer-products_v4) starts only after the copy is done, consuming from offsets O. O has to be grabbed (end offsets of catalog.products) BEFORE the snapshot opens, otherwise changes slip through. Anything replayed that the snapshot already had is no later than S, so it either bounces as a version conflict (stale, just counted) or rewrites the same thing, and because replay only starts after the copy, a delete can't get overwritten by the copied doc. If any of that fails, the alias was never touched, so just drop v4 and the group and redo it. Indexer = consumer = sync worker, same thing. It's stateless: its position is the committed offsets in Kafka for its group, committed after the bulk ack, so after a crash it restarts from there and redoes a batch, which is harmless because the versions are the same. v3 stays fed by indexer-products_v3 for 48 h after the flip, so flipping back loses nothing; then stop that group and delete v3.

```mermaid
flowchart LR
  subgraph S1["pipeline stuff"]
    pg[("catalog-primary")] --- slot["search_slot"]
    slot --> dbz["Debezium"]
    dbz --> topic["catalog.products"]
    topic --> w3["sync worker v3"]
    topic --> w4["indexer-products_v4"]
    w3 --> bulk["bulk"]
    w4 --> bulk
    bulk --> v3[("products_v3")]
    bulk --> shadow[("shadow index")]
    bulk --> dlq["catalog.products.dlq"]
    bulk --> bulk
  end
  api["Search API"] --> alias{"products"}
  alias --> v3
  alias -.-> shadow
  copy["reindexer copy job"] --> shadow
  pg --> copy
  n1["NOTE: status draft or archived, or op d, means delete doc; upsert only for active; all with version commit_lsn; index keeps a write only if version is at least the stored one"]
  n2["NOTE errors: timeout/5xx/throttle - pause, retry same batch 1s 2s 4s up to 60s cap, no offset commit, events sit in Kafka 7 days. invalid doc - to dlq + alert, then commit and go on"]
  n3["NOTE: batch flush 500 events or 1 s"]
  n4["NOTE WAL: 20 GB alert, 50 GB slot dropped by ops, then new slot + connector and full rebuild"]
  n1 -.- bulk
  n2 -.- dlq
  n3 -.- w4
  n4 -.- dbz
  topic -.- n5["12 partitions keyed by product id, one event per row change with commit_lsn"]
```

Also, the copy reads active rows in id order.
