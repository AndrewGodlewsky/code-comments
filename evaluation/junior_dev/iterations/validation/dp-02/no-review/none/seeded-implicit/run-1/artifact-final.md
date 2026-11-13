# Clickstream ingestion plan

1. **SDKs** (web, iOS, Android) batch events (up to 100) with `event_id`, `device_id` and a client timestamp, and send them to the collector. They retry with backoff.
2. **Collector** validates events, adds `received_at`, and writes them to the raw log. Malformed events go to a reject bucket.
3. **Archiver** writes raw events to object storage in hourly files, with a 90-day lifecycle.
4. **Live processor** dedups on `event_id` using the KV store, enriches (geo-IP, user agent), and loads `events_clean` (partitioned by day).
5. **Replay job** rebuilds a day from the archive into a staging table and swaps it into `events_clean`.
6. Monitoring and alerts on consumer lag.

Bot filtering: TBD.
