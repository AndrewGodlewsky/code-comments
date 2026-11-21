# Feature flags and background jobs

## Flags (`app.flags`)
- `flags.get(name)` returns a boolean, a string, or a percentage (0-100).
  For a percentage flag, `flags.enabled_for(name, key)` buckets by key, so
  the same key always gets the same answer.
- Each app instance caches all flags and refreshes them every 30 seconds.
  After a change, instances can disagree for up to 30 seconds.
- Each instance exports the flag values it is currently using as the metric
  `app_flag_value{flag=...}`, so you can see when every instance has a change.

## Jobs (`app.jobs`)
- `jobs.enqueue(name, payload)` pushes onto a Redis-backed queue. Workers run
  separately from the web instances.
- Delivery is at least once. A failed job is retried up to 5 times with
  exponential backoff (about 15 minutes in total), then moved to the
  dead-letter list `jobs:dead`, which nothing processes automatically.
- If Redis is unreachable, `enqueue` raises after a 1 second timeout.
