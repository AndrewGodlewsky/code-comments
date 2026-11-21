# Search setup (current)

- Search store: one cluster. Live index `products_v3`.
- The search API only ever queries the alias `products`, which points at
  `products_v3`. Moving an alias is atomic: a query goes to the old index or
  the new one, never to neither.
- Writes may carry a per-document version. The store applies a write only if
  its version is at least the stored version; otherwise it returns a
  version-conflict error for that document.
- Kafka: 3 brokers, shared with other teams. Topic retention 7 days.
- CDC connector (Debezium) is installed but only feeds a test topic. When it is
  pointed at the catalog, it reads replication slot `search_slot` and writes one
  event per row change to topic `catalog.products`: 12 partitions, keyed by
  product id, so all changes to one product are in one partition in commit order.
- Event shape:
  {"op": "c" | "u" | "d", "id": 123, "after": {...full row...} or null for d,
   "commit_lsn": "0/16B3748"}
  commit_lsn is the WAL position of the committing transaction: larger means
  committed later.
- While the connector is stopped, Postgres keeps the WAL for the slot.
