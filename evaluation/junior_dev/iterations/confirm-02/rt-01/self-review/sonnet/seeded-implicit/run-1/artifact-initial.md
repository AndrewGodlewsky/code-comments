## Presence and cursors plan

Uses Redis for presence and pub/sub. Clients keep a presence store. Heartbeats keep things fresh, and a sweeper cleans up.

```mermaid
sequenceDiagram
    participant A as Alice
    participant N1 as Node 1
    participant R as Redis
    participant N2 as Node 2
    participant B as Bob

    A->>N1: open
    N1->>R: register presence
    N1-->>A: snapshot
    N1->>R: publish join
    R-->>N2: join
    N2-->>B: join

    A->>N1: cursor
    N1->>R: publish cursor
    R-->>N2: cursor
    N2-->>B: cursor

    N1->>A: ping
    A-->>N1: pong
    N1->>R: refresh

    A-xN1: close
    N1->>R: remove + publish leave
    N2-->>B: leave

    Note over N2: crash
    N1->>R: sweep
    N1-->>A: leave
```

Notes:
- Cursors are throttled.
- Handle revisions with transformPosition.
- Dedupe tabs on the client.
- Seq numbers on cursors.
- Entries have a TTL.
- Edits are unchanged.
