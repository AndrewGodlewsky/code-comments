```mermaid
erDiagram
    TENANT ||--o{ JOB_SCHEDULE : defines
    JOB_SCHEDULE ||--o{ JOB_RUN : creates
    JOB_RUN ||--o{ RUN_ATTEMPT : has

    TENANT {
        uuid id PK
        text status
    }
    JOB_SCHEDULE {
        uuid id PK
        uuid tenant_id FK
        text job_type
        jsonb payload
        text cron_expr
        text timezone
        boolean enabled
        timestamptz next_fire_at
    }
    JOB_RUN {
        uuid id PK
        uuid schedule_id FK
        timestamptz scheduled_for
        text status
        int attempt_count
        text lease_owner
        timestamptz lease_expires_at
    }
    RUN_ATTEMPT {
        uuid id PK
        uuid run_id FK
        text worker_id
        text outcome
        text error_message
    }
```

Notes:
- Workers poll for due schedules and create runs. Uses SKIP LOCKED.
- Workers claim runs and execute them, with a lease.
- Heartbeats keep the lease alive.
- Failures retry with backoff, up to the limit.
- A reaper handles dead workers.
- Overlapping and missed runs are handled per the spec.
- Pausing a tenant or disabling a schedule cancels its pending work.
- History is purged after 90 days.
