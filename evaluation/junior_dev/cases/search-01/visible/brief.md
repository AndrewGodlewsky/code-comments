## Search sync: replace the 15-minute cron with change data capture

Product search is currently fed by a cron job (`existing/indexer_cron.py`) that polls `products` every 15 minutes. It misses hard deletes, overlapping runs can write older data last, and changes take up to 15 minutes to show up. Read `existing/schema.sql` and `existing/search-setup.md` for the table, the search store and the CDC/Kafka pieces we already have.

I want a plan for two things. First, streaming every committed change to `products` into the index. Second, rebuilding the index from scratch (for new mappings, or after data loss) without search ever going down.

**Fixed requirements**
- Use the CDC connector and the `catalog.products` topic described in search-setup.md. A new indexer service consumes the topic, and the cron job is retired.
- Target: 95% of committed changes searchable within 5 seconds.
- Use each change's `commit_lsn` as the document version, with the store's "new must be at least stored" rule. A version conflict means the change is stale. Count it, but don't treat it as an error.
- The search rules in the schema file still apply.
- Kafka offsets are committed only after the index has acknowledged the writes they cover.
- Transient index failures (timeouts, 5xx, throttling): retry with backoff that starts at 1 s, doubles each time and is capped at 60 s. Never skip ahead. If the index refuses a document as invalid, send it to `catalog.products.dlq` with the error, raise an alert and carry on processing.
- Retained WAL on the primary: alert at 20 GB. At 50 GB, ops will drop the slot to protect the primary. After that, a full rebuild is the only way back.

**Rebuild constraints**
- The search API keeps querying the alias `products` and must never see a half-built index.
- The DBA allows one long repeatable-read snapshot on the primary, read at up to 5,000 rows/s. That is about 2.5 hours for the active rows.
- Switch only when the new index is less than 5 s behind and its document count is within 0.5% of the active row count.
- Keep the old index for 48 hours after the switch, so that we can switch back without losing any change made in the meantime.

**Format:** a Mermaid flowchart that covers both the live sync path and the rebuild, with short notes before or after it. Show what triggers each step, what data moves, where progress is stored and what happens on each kind of failure.
