## Notes sync

Phones keep notes in SQLite with an outbox. The server keeps notes with versions, a change log, and processed change IDs. Sync is push plus pull, on the usual triggers.

```mermaid
sequenceDiagram
    participant A as Phone A
    participant B as Phone B
    participant S as Server
    A->>A: Edit note offline
    B->>B: Edit same note offline
    A->>S: Push
    S-->>A: Result
    A->>S: Pull
    S-->>A: Changes
    B->>S: Push
    S-->>B: Conflict
    B->>S: Pull
    S-->>B: Changes
```

- Conflicts are handled by version check and a conflict copy.
- Retries use change IDs. Sent changes aren't edited.
- A cursor tracks pull progress, paged.
- Batching limits apply.
