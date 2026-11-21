## Live cursors and presence across gateway nodes

**Where state lives**

| State | Where | Written by | Removed by |
|---|---|---|---|
| Presence entry per connection: `userId, nodeId, lastSeen, cursor {pos, rev, seq}` | Redis hash `presence:{docId}`, field = `connId` | Only the node that owns the connection | The owning node on close, or any node's sweep once stale. The whole key has a 120 s EXPIRE, refreshed on every write. |
| `join` / `leave` / `cursor` events | Redis pub/sub channel `presence:{docId}` (stores nothing, separate from `ops:{docId}`) | The node that owns the connection, or the sweeping node for a `leave` | n/a |
| Latest cursor, last accepted time, last seq and pending hash write per local connection | Gateway node memory | That node | When the socket closes |
| `userId -> {connIds, cursor, seq}` and held cursors | Client memory | The client | When the client leaves |

Cursors never reach the document service or Postgres. The edit path (`op` -> node -> document service -> Postgres -> `ops:{docId}`) is unchanged. Any node can serve any document because all fan-out goes through Redis, so there's no sticky routing.

```mermaid
sequenceDiagram
    autonumber
    participant A as Alice browser
    participant N1 as Gateway node 1
    participant R as Redis
    participant N2 as Gateway node 2
    participant B as Bob browser

    Note over A,B: 1. JOIN - Bob is already in doc D through node 2. Alice opens D through node 1.
    A->>N1: open D (connA, userA from the session)
    opt first local socket on D at node 1
        N1->>R: SUBSCRIBE presence:D
    end
    Note over N1: from now on, presence:D events for connA are buffered
    N1->>R: HSET presence:D connA = userA, node1, lastSeen now, no cursor, then EXPIRE presence:D 120 s
    N1->>R: HGETALL presence:D
    R-->>N1: every connection entry, incl. connB with Bob's last cursor, rev, seq
    Note over N1: entries with lastSeen older than 30 s are left out and HDELed
    N1-->>A: presence_snapshot
    N1-->>A: buffered events, then live events
    Note over A: groups entries by userId (one avatar per user), applies events by connId, ignores a snapshot cursor whose seq is older than a buffered one
    N1->>R: PUBLISH presence:D join connA userA
    R-->>N2: join connA userA
    N2-->>B: join connA userA
    Note over B: adds Alice, or only adds connA to her if she is already shown from another tab

    Note over A,B: 2. CURSOR MOVE - client sends at most one every 50 ms
    A->>N1: cursor pos, rev, seq (seq rises by 1 per update on this connection)
    alt under 50 ms since connA's last accepted cursor
        Note over N1: dropped silently, nothing published
    else accepted
        N1->>R: PUBLISH presence:D cursor connA userA pos rev seq
        par every node subscribed to presence:D
            R-->>N2: cursor connA
            N2-->>B: cursor connA
        and the sender's own node, the same way
            R-->>N1: cursor connA
            Note over N1: forwards to its other local sockets on D, never back to connA
        end
        N1->>R: HSET presence:D connA cursor pos rev seq (at most once per second per connection)
        Note over N1: if a write was already made in this 1 s window, the latest cursor is written when the window ends, so the hash always ends up with the final position after the last move
    end
    Note over B: 1. seq not higher than the last seen for connA: drop<br/>2. rev newer than Bob's appliedRev: do not draw, hold the latest only, draw when Bob has applied rev<br/>3. rev older: transformPosition(pos, rev, appliedRev), drop if it throws HistoryGone<br/>4. draw the caret for userA

    Note over A,B: 3. HEARTBEAT - the existing ping every 10 s
    loop every 10 s per connection
        N1->>A: ping
        A-->>N1: pong
        N1->>R: HSET presence:D connA lastSeen now, EXPIRE presence:D 120 s
    end

    Note over A,B: 4. CLEAN LEAVE - Alice closes her second tab, connA2, which joined like step 1
    A-xN1: socket connA2 closed (the node also closes a socket after 20 s with no pong)
    N1->>R: HDEL presence:D connA2
    N1->>R: PUBLISH presence:D leave connA2 userA
    R-->>N2: leave connA2 userA
    N2-->>B: leave connA2 userA
    Note over B: removes connA2. Alice stays listed because connA remains. Her avatar goes only when none of her connIds are left.
    opt no local socket on D left at node 1
        N1->>R: UNSUBSCRIBE presence:D
    end

    Note over A,B: 5. NODE 2 CRASHES - connB stops being refreshed
    Note over N2: dead, does no cleanup
    loop every 5 s, on every node with local sockets on D
        N1->>R: HGETALL presence:D
        Note over N1: connB lastSeen is older than 30 s
        N1->>R: HDEL presence:D connB
        R-->>N1: 1 = this node removed it (0 = another node did, so stop here)
        N1->>R: PUBLISH presence:D leave connB userB
        R-->>N1: leave connB userB
        N1-->>A: leave connB userB
    end
    Note over B: Bob's browser reconnects through the load balancer to any node and repeats step 1 with a new connId
```

**Timings and failure rules**

- **Clean close.** The node sends HDEL and PUBLISH `leave` straight away, so others see it well within 2 s. If the node has to close a socket after 20 s without a pong, it follows the same path.
- **Node crash.** A dead node stops refreshing, so connB's `lastSeen` is no later than the moment of the crash. The entry counts as stale at most 30 s after the crash (three missed 10 s refreshes), and the next sweep runs within 5 s, so the worst case is about 30 + 5 = 35 s, inside the 45 s limit with 10 s to spare. Only the node whose HDEL returns 1 publishes `leave`, so the leave is announced exactly once. If no node has local sockets on the document, nobody sweeps. The next joiner's snapshot skips and deletes stale entries, and the 120 s EXPIRE removes the key once no one is refreshing it.
- **Reconnect to another node.** The browser gets a new connId. If the old entry is still there, it lingers until it is swept, but the client groups entries by userId, so the user is still shown once.
- **Ordering.** Every cursor carries a per-connection `seq`. Receivers keep the highest seq they have seen per connId and drop anything at or below it, whether it comes from pub/sub, from the buffer or from the snapshot.
