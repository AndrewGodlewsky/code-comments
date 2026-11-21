# Live cursors and presence: sequence design

Presence and cursors go through Redis pub/sub and a few Redis keys that the gateway nodes own. The edit path, the document service, Postgres and the load balancer are not touched. Each connection holds a lease that its node refreshes every 10 s. The lease lasts 30 s, so a crashed node's users are removed by a surviving node's sweep within 40 s.

```mermaid
sequenceDiagram
    autonumber
    participant A as Ann (browser)
    participant N1 as Node 1
    participant R as Redis
    participant N2 as Node 2
    participant B as Ben (browser)
    participant N3 as Node 3
    participant C as Carl (browser)

    Note over B,C: Before the scene: Ben (connId cB) is on Node 2 and Carl (connId cC) is on Node 3. Both are in presence, leases and cursors.

    Note over A,N1: Scene 1: Ann opens the doc on Node 1 while Ben is already in it on Node 2
    A->>N1: open docId (connId cA, userId ann)
    N1->>R: SUBSCRIBE presence:doc and cursor:doc
    Note over N1: Subscribe before reading the snapshot, so no event is missed
    N1->>R: Lua join cA: HSET presence cA, ZADD leases cA (Redis TIME + 30 s), INCR presence_ver
    Note over R: If ann has no other presence entry, the script PUBLISHes join ann with the new version. A second tab publishes nothing.
    R-->>N2: presence:doc join ann v
    N2-->>B: presence join ann v
    N1->>R: HGETALL presence, HGETALL cursors
    R-->>N1: presence (cB ben, cC carl), cursors (cB at old rev r0, cC at old rev r1)
    N1-->>A: snapshot v with users ann, ben, carl and stored cursors
    Note over A: A stored cursor whose rev is older than the first kept revision cannot be transformed (HistoryGone), so it is dropped for now
    N1->>R: PUBLISH presence:doc hello cA
    R-->>N2: hello cA
    N2-->>B: hello cA
    B->>N2: cursor seq (fresh, current rev, current pos), even if idle
    N2->>R: HSET cursors cB, PUBLISH cursor:doc
    R-->>N1: cursor cB (fresh rev)
    N1-->>A: cursor cB (fresh rev, drawable)

    Note over B,A: Scene 2: Ben moves his caret
    B->>N2: cursor seq 42, rev 812, pos 230 (at most one per 50 ms)
    Note over N2: Silently drop if the last accepted update from cB was under 50 ms ago
    N2->>R: HSET cursors cB (seq 42, rev 812, pos 230), PUBLISH cursor:doc
    R-->>N1: cursor cB seq 42 rev 812 pos 230
    N1-->>A: cursor cB seq 42 rev 812 pos 230
    Note over A: Drop if seq is not above the last seq shown for cB (no backward jumps)
    Note over A: If rev 812 is above appliedRev, hold it as pending and draw it when rev 812 is applied
    Note over A: Otherwise transformPosition(pos, 812, appliedRev). On HistoryGone, drop it until the next update.

    Note over N1,R: Scene 3: heartbeat (no caret or presence event is sent)
    loop Every 10 s, for each local connection
        N1->>R: Lua heartbeat cA: ZADD leases XX (Redis TIME + 30 s), EXPIRE presence, cursors, presence_ver 120 s
    end
    loop Every 10 s, each node that has a local socket on the doc
        N2->>R: Lua sweep: ZRANGEBYSCORE leases -inf (Redis TIME)
        Note over R: For each expired connId, ZREM. Only the call that removes it continues: HDEL presence and cursors, PUBLISH leave if it was the last connection for that user.
    end

    Note over A,N1: Scene 4: Ann closes her tab cleanly
    A->>N1: socket close
    N1->>R: Lua leave cA: ZREM leases, HDEL presence, HDEL cursors, INCR presence_ver
    Note over R: If no presence entry for ann remains, PUBLISH leave ann with the new version
    R-->>N2: presence:doc leave ann
    N2-->>B: presence leave ann
    Note over B: Ann disappears well within 2 s. If Ann has another tab, she stays listed.
    N1->>R: UNSUBSCRIBE presence:doc and cursor:doc if no local sockets are left on the doc

    Note over N3: Scene 5: Node 3 crashes. It runs no cleanup. Carl's lease was last refreshed up to 10 s before the crash.
    Note over R: cC stays in leases, presence and cursors until its score (last refresh + 30 s) passes
    loop Node 2 sweep tick, every 10 s
        N2->>R: Lua sweep finds cC expired
        R-->>N2: ZREM cC (this call wins), HDEL presence and cursors, PUBLISH leave carl if it was carl's last connection
    end
    R-->>N2: presence:doc leave carl
    N2-->>A: presence leave carl
    N2-->>B: presence leave carl
    Note over C: Carl's browser reconnects to a live node with a new connId and is listed again as a new connection
